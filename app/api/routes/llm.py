import base64
import json
import logging
import os
from logging.config import fileConfig
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import templates
from app.database import get_db
from app.models.llm_config import LLMConfig

router = APIRouter()

@router.get("/llm", response_class=HTMLResponse, include_in_schema=False)
async def llm_food_extractor_page(request: Request):
    return templates.TemplateResponse("llm_food_extractor.html", {"request": request})

class FoodItem(BaseModel):
    name: Optional[str] = Field(None, description="Name of the food item")
    brand: Optional[str] = Field(None, description="Brand name of the food item")
    serving_size_g: Optional[float] = Field(None, description="Actual serving size in grams as labeled on the page")
    calories: Optional[int] = Field(None, description="Calories per actual serving")
    protein_g: Optional[float] = Field(None, description="Protein in grams per actual serving")
    carbohydrate_g: Optional[float] = Field(None, description="Carbohydrates in grams per actual serving")
    fat_g: Optional[float] = Field(None, description="Fat in grams per actual serving")
    fiber_g: Optional[float] = Field(None, description="Fiber in grams per actual serving")
    sugar_g: Optional[float] = Field(None, description="Sugar in grams per actual serving")
    sodium_mg: Optional[int] = Field(None, description="Sodium in milligrams per actual serving")
    calcium_mg: Optional[int] = Field(None, description="Calcium in milligrams per actual serving")
    potassium_mg: Optional[int] = Field(None, description="Potassium in milligrams per actual serving")
    cholesterol_mg: Optional[int] = Field(None, description="Cholesterol in milligrams per actual serving")

@router.post("/llm/extract", response_model=FoodItem)
async def extract_food_data_from_llm(
    request: Request,
    url: Optional[str] = Form(None),
    webpage_url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    logging.info("Starting food data extraction from LLM.")
    llm_config = db.query(LLMConfig).first()
    if not llm_config or not llm_config.openrouter_api_key:
        logging.error("OpenRouter API key not configured.")
        raise HTTPException(
            status_code=500,
            detail="OpenRouter API key not configured. Please configure it in the Admin section."
        )
    if not llm_config.browserless_api_key:
        logging.error("Browserless API key not configured.")
        raise HTTPException(
            status_code=500,
            detail="Browserless API key not configured. Please configure it in the Admin section."
        )
    logging.info(f"LLM config loaded: preferred_model={llm_config.preferred_model}")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=llm_config.openrouter_api_key
    )

    # LLM prompt for extracting nutrition data from webpage content or images.
    # Units: serving_size_g in grams; nutrition values per actual serving size (not normalized to 100g).
    # All nutrition fields are in grams except sodium_mg, calcium_mg, potassium_mg, cholesterol_mg in milligrams.
    prompt = """You are a nutrition data extractor. Your task is to analyze the provided information (image or website content) and extract the nutritional information for the food item. The output must be a single JSON object that conforms to the following schema. All nutritional values should be for the actual serving size as labeled on the page (e.g., if the page says "per 1 cup (240g)", use values for 240g serving).

     JSON Schema:
     {
       "name": "string",
       "brand": "string",
       "serving_size_g": "float",
       "calories": "integer",
       "protein_g": "float",
       "carbohydrate_g": "float",
       "fat_g": "float",
       "fiber_g": "float",
       "sugar_g": "float",
       "sodium_mg": "integer",
       "calcium_mg": "integer",
       "potassium_mg": "integer",
       "cholesterol_mg": "integer"
     }

     The food name is usually the most prominent header or title on the page. Brand is the manufacturer or brand name if available. serving_size_g should be the actual grams for the serving size shown (e.g., 240 for 1 cup). If any of the fields are not available, set them to null. Do not include any text or explanations outside of the JSON object in your response.
     """
    messages = [{"role": "system", "content": prompt}]

    content = []
    if url:
        logging.info(f"Processing image from URL: {url}")
        content.append({"type": "image_url", "image_url": {"url": url}})
    elif webpage_url:
        logging.info(f"Processing content from webpage URL: {webpage_url}")
        try:
            async with httpx.AsyncClient() as client:
                browserless_url = f"https://production-sfo.browserless.io/content?token={llm_config.browserless_api_key}"
                headers = {
                    "Cache-Control": "no-cache",
                    "Content-Type": "application/json"
                }
                payload = {"url": webpage_url}
                logging.info(f"Fetching content from Browserless API (POST): {browserless_url} with payload url={webpage_url}")
                response = await client.post(browserless_url, headers=headers, json=payload, timeout=30.0)
                logging.info(f"Browserless response status={response.status_code}, content_length={len(response.text) if response and response.text is not None else 0}")
                response.raise_for_status()
                content.append({"type": "text", "text": f"Extract nutritional data from this webpage content: {response.text}"})
                logging.info("Successfully fetched webpage content.")
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if getattr(e, "response", None) is not None else "unknown"
            body = e.response.text if getattr(e, "response", None) is not None else ""
            logging.error(f"Browserless HTTP error status={status}, body_snippet={body[:500]}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Browserless HTTP {status}: unable to fetch webpage content")
        except httpx.HTTPError as e:
            logging.error(f"HTTP client error while fetching webpage content: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Could not fetch webpage content: {e}")
    elif image:
        logging.info(f"Processing uploaded image: {image.filename}")
        image_data = await image.read()
        base64_image = base64.b64encode(image_data).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
        })
        logging.info("Successfully processed uploaded image.")
    else:
        logging.error("No input provided. Either a URL, a webpage URL, or an image is required.")
        raise HTTPException(status_code=400, detail="Either a URL, a webpage URL, or an image must be provided.")

    messages.append({"role": "user", "content": content})
    logging.info(f"LLM prompt: {messages}")
    try:
        os.makedirs("/app/data", exist_ok=True)
        with open("/app/data/llmprompt.txt", "wt") as file:
            file.write(json.dumps(messages, indent=2))
        logging.info("Wrote LLM prompt to /app/data/llmprompt.txt")
    except Exception as e:
        logging.warning(f"Could not write LLM prompt file: {e}", exc_info=True)

    try:
        openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=llm_config.openrouter_api_key
        )
        logging.info(f"Sending request to LLM with model: {llm_config.preferred_model}")
        response = openai_client.chat.completions.create(
            model=llm_config.preferred_model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        food_data_str = response.choices[0].message.content
        logging.info(f"LLM response: {food_data_str}")
        food_data = json.loads(food_data_str)
        logging.info("Successfully parsed LLM response.")
        # Debug logs for serving size: trace actual serving_size_g from LLM, no rescaling applied
        serving_size_g = food_data.get('serving_size_g')
        logging.info(f"Extracted serving_size_g: {serving_size_g}g (actual serving size, no normalization to 100g)")
        return FoodItem(**food_data)
    except Exception as e:
        logging.error(f"Error during LLM data extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error extracting food data: {e}")