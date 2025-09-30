from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import csv
import logging
import os
import re
from typing import List, Optional

# Import from the database module
from app.database import get_db, Food, FoodCreate, FoodResponse
from main import templates

try:
    from openfoodfacts import API, APIVersion, Country, Environment, Flavor
except ImportError:
    API = APIVersion = Country = Environment = Flavor = None
    logging.warning("OpenFoodFacts module not installed. Some food functionalities will be limited.")

router = APIRouter()

# Foods tab
@router.get("/foods", response_class=HTMLResponse)
async def foods_page(request: Request, db: Session = Depends(get_db)):
    foods = db.query(Food).all()
    return templates.TemplateResponse(request, "foods.html", {"foods": foods})

@router.post("/foods/upload")
async def bulk_upload_foods(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Handle bulk food upload from CSV"""
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        
        stats = {'created': 0, 'updated': 0, 'errors': []}
        
        for row_num, row in enumerate(reader, 2):  # Row numbers start at 2 (1-based + header)
            try:
                # Map CSV columns to model fields
                food_data = {
                    'name': f"{row['ID']} ({row['Brand']})",
                    'serving_size': str(round(float(row['Serving (g)']), 3)),
                    'serving_unit': 'g',
                    'calories': round(float(row['Calories']), 2),
                    'protein': round(float(row['Protein (g)']), 2),
                    'carbs': round(float(row['Carbohydrate (g)']), 2),
                    'fat': round(float(row['Fat (g)']), 2),
                    'fiber': round(float(row.get('Fiber (g)', 0)), 2),
                    'sugar': round(float(row.get('Sugar (g)', 0)), 2),
                    'sodium': round(float(row.get('Sodium (mg)', 0)), 2),
                    'calcium': round(float(row.get('Calcium (mg)', 0)), 2),
                    'brand': row.get('Brand', '') # Add brand from CSV
                }

                # Check for existing food
                existing = db.query(Food).filter(Food.name == food_data['name']).first()
                
                if existing:
                    # Update existing food
                    for key, value in food_data.items():
                        setattr(existing, key, value)
                    # Ensure source is set for existing foods
                    if not existing.source:
                        existing.source = "csv"
                    stats['updated'] += 1
                else:
                    # Create new food
                    food_data['source'] = "csv"
                    food = Food(**food_data)
                    db.add(food)
                    stats['created'] += 1
                    
            except (KeyError, ValueError) as e:
                stats['errors'].append(f"Row {row_num}: {str(e)}")
        
        db.commit()
        return stats
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/foods/add")
async def add_food(request: Request, db: Session = Depends(get_db),
                  name: str = Form(...), serving_size: str = Form(...),
                  serving_unit: str = Form(...), calories: float = Form(...),
                  protein: float = Form(...), carbs: float = Form(...),
                  fat: float = Form(...), fiber: float = Form(0),
                  sugar: float = Form(0), sodium: float = Form(0),
                  calcium: float = Form(0), source: str = Form("manual"),
                  brand: str = Form("")):

    try:
        food = Food(
            name=name, serving_size=serving_size, serving_unit=serving_unit,
            calories=calories, protein=protein, carbs=carbs, fat=fat,
            fiber=fiber, sugar=sugar, sodium=sodium, calcium=calcium,
            source=source, brand=brand
        )
        db.add(food)
        db.commit()
        return {"status": "success", "message": "Food added successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/foods/edit")
async def edit_food(request: Request, db: Session = Depends(get_db),
                   food_id: int = Form(...), name: str = Form(...),
                   serving_size: str = Form(...), serving_unit: str = Form(...),
                   calories: float = Form(...), protein: float = Form(...),
                   carbs: float = Form(...), fat: float = Form(...),
                   fiber: float = Form(0), sugar: float = Form(0),
                   sodium: float = Form(0), calcium: float = Form(0),
                   source: str = Form("manual"), brand: str = Form("")):

    try:
        food = db.query(Food).filter(Food.id == food_id).first()
        if not food:
            return {"status": "error", "message": "Food not found"}

        food.name = name
        food.serving_size = serving_size
        food.serving_unit = serving_unit
        food.calories = calories
        food.protein = protein
        food.carbs = carbs
        food.fat = fat
        food.fiber = fiber
        food.sugar = sugar
        food.sodium = sodium
        food.calcium = calcium
        food.source = source
        food.brand = brand

        db.commit()
        return {"status": "success", "message": "Food updated successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/foods/delete")
async def delete_foods(food_ids: dict = Body(...), db: Session = Depends(get_db)):
    try:
        # Delete foods
        db.query(Food).filter(Food.id.in_(food_ids["food_ids"])).delete(synchronize_session=False)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/foods/search_openfoodfacts")
async def search_openfoodfacts(query: str, limit: int = 10):
    """Search OpenFoodFacts database for foods using the official SDK"""
    try:
        if API is None:
            return {"status": "error", "message": "OpenFoodFacts module not installed. Please install with: pip install openfoodfacts"}

        # Initialize the API client
        api = API(
            user_agent="MealPlanner/1.0",
            country=Country.world,
            flavor=Flavor.off,
            version=APIVersion.v2,
            environment=Environment.org
        )

        # Perform text search
        search_result = api.product.text_search(query)

        results = []

        if search_result and 'products' in search_result:
            for product in search_result['products'][:limit]:  # Limit results
                # Skip products without basic information
                if not product.get('product_name') and not product.get('product_name_en'):
                    continue

                # Extract nutritional information (OpenFoodFacts provides per 100g values)
                nutriments = product.get('nutriments', {})

                # Get serving size information
                serving_size = product.get('serving_size', '100g')
                if not serving_size or serving_size == '':
                    serving_size = '100g'

                # Parse serving size to extract quantity and unit
                serving_quantity = 100  # default to 100g
                serving_unit = 'g'

                try:
                    # Try to parse serving size (e.g., "30g", "1 cup", "250ml")
                    match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', str(serving_size))
                    if match:
                        serving_quantity = float(match.group(1))
                        serving_unit = match.group(2)
                    else:
                        # If no clear match, use 100g as default
                        serving_quantity = 100
                        serving_unit = 'g'
                except:
                    serving_quantity = 100
                    serving_unit = 'g'

                # Helper function to safely extract and convert nutrient values
                def get_nutrient_per_serving(nutrient_key, default=0):
                    """Extract nutrient value and convert from per 100g to per serving"""
                    value = nutriments.get(nutrient_key, nutriments.get(nutrient_key.replace('_100g', ''), default))
                    if value is None or value == '':
                        return default
                    
                    try:
                        # Convert to float
                        numeric_value = float(str(value).replace(',', '.'))  # Handle European decimal format
                        
                        # If the nutrient key contains '_100g', it's already per 100g
                        # Convert to per serving size
                        if '_100g' in nutrient_key and serving_quantity != 100:
                            numeric_value = (numeric_value * serving_quantity) / 100
                        
                        return round(numeric_value, 2)
                    except (ValueError, TypeError):
                        return default

                # Extract product name (try multiple fields)
                product_name = (product.get('product_name') or 
                              product.get('product_name_en') or 
                              product.get('abbreviated_product_name') or 
                              'Unknown Product')

                # Add brand information if available
                brands = product.get('brands', '')
                if brands and brands not in product_name:
                    product_name = f"{product_name} ({brands})"

                # Build the food data structure
                food_data = {
                    'name': product_name[:100],  # Limit name length
                    'serving_size': str(serving_quantity),
                    'serving_unit': serving_unit,
                    'calories': get_nutrient_per_serving('energy-kcal_100g', 0),
                    'protein': get_nutrient_per_serving('proteins_100g', 0),
                    'carbs': get_nutrient_per_serving('carbohydrates_100g', 0),
                    'fat': get_nutrient_per_serving('fat_100g', 0),
                    'fiber': get_nutrient_per_serving('fiber_100g', 0),
                    'sugar': get_nutrient_per_serving('sugars_100g', 0),
                    'sodium': get_nutrient_per_serving('sodium_100g', 0),  # in mg
                    'calcium': get_nutrient_per_serving('calcium_100g', 0),  # in mg
                    'source': 'openfoodfacts',
                    'openfoodfacts_id': product.get('code', ''),
                    'brand': brands, # Brand is already extracted
                    'image_url': product.get('image_url', ''),
                    'categories': product.get('categories', ''),
                    'ingredients_text': product.get('ingredients_text_en', product.get('ingredients_text', ''))
                }

                # Only add products that have at least calorie information
                if food_data['calories'] > 0:
                    results.append(food_data)

        return {"status": "success", "results": results}

    except Exception as e:
        return {"status": "error", "message": f"OpenFoodFacts search failed: {str(e)}"}

@router.get("/foods/get_openfoodfacts_product/{barcode}")
async def get_openfoodfacts_product(barcode: str):
    """Get a specific product by barcode from OpenFoodFacts"""
    try:
        if API is None:
            return {"status": "error", "message": "OpenFoodFacts module not installed"}

        # Initialize the API client
        api = API(
            user_agent="MealPlanner/1.0",
            country=Country.world,
            flavor=Flavor.off,
            version=APIVersion.v2,
            environment=Environment.org
        )

        # Get product by barcode
        product_data = api.product.get(barcode)

        if not product_data or not product_data.get('product'):
            return {"status": "error", "message": "Product not found"}

        product = product_data['product']
        nutriments = product.get('nutriments', {})

        # Extract serving information
        serving_size = product.get('serving_size', '100g')
        serving_quantity = 100
        serving_unit = 'g'

        try:
            match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', str(serving_size))
            if match:
                serving_quantity = float(match.group(1))
                serving_unit = match.group(2)
        except:
            pass

        # Helper function for nutrient extraction
        def get_nutrient_per_serving(nutrient_key, default=0):
            value = nutriments.get(nutrient_key, nutriments.get(nutrient_key.replace('_100g', ''), default))
            if value is None or value == '':
                return default
            
            try:
                numeric_value = float(str(value).replace(',', '.'))
                if '_100g' in nutrient_key and serving_quantity != 100:
                    numeric_value = (numeric_value * serving_quantity) / 100
                return round(numeric_value, 2)
            except (ValueError, TypeError):
                return default

        # Build product name
        product_name = (product.get('product_name') or 
                       product.get('product_name_en') or 
                       'Unknown Product')
        
        brands = product.get('brands', '')
        if brands and brands not in product_name:
            product_name = f"{product_name} ({brands})"

        food_data = {
            'name': product_name[:100],
            'serving_size': str(serving_quantity),
            'serving_unit': serving_unit,
            'calories': get_nutrient_per_serving('energy-kcal_100g', 0),
            'protein': get_nutrient_per_serving('proteins_100g', 0),
            'carbs': get_nutrient_per_serving('carbohydrates_100g', 0),
            'fat': get_nutrient_per_serving('fat_100g', 0),
            'fiber': get_nutrient_per_serving('fiber_100g', 0),
            'sugar': get_nutrient_per_serving('sugars_100g', 0),
            'sodium': get_nutrient_per_serving('sodium_100g', 0),
            'calcium': get_nutrient_per_serving('calcium_100g', 0),
            'source': 'openfoodfacts',
            'openfoodfacts_id': barcode,
            'brand': brands, # Brand is already extracted
            'image_url': product.get('image_url', ''),
            'categories': product.get('categories', ''),
            'ingredients_text': product.get('ingredients_text_en', product.get('ingredients_text', ''))
        }

        return {"status": "success", "product": food_data}

    except Exception as e:
        return {"status": "error", "message": f"Failed to get product: {str(e)}"}

@router.get("/foods/openfoodfacts_by_category")
async def get_openfoodfacts_by_category(category: str, limit: int = 20):
    """Get products from OpenFoodFacts filtered by category"""
    try:
        if API is None:
            return {"status": "error", "message": "OpenFoodFacts module not installed"}

        # Initialize the API client
        api = API(
            user_agent="MealPlanner/1.0",
            country=Country.world,
            flavor=Flavor.off,
            version=APIVersion.v2,
            environment=Environment.org
        )

        # Search by category (you can also combine with text search)
        search_result = api.product.text_search("", 
                                               categories_tags=category,
                                               page_size=limit,
                                               sort_by="popularity")

        results = []
        if search_result and 'products' in search_result:
            for product in search_result['products'][:limit]:
                if not product.get('product_name') and not product.get('product_name_en'):
                    continue

                nutriments = product.get('nutriments', {})
                
                # Only include products with nutritional data
                if not nutriments.get('energy-kcal_100g'):
                    continue

                product_name = (product.get('product_name') or 
                               product.get('product_name_en') or 
                               'Unknown Product')
                
                brands = product.get('brands', '')
                if brands and brands not in product_name:
                    product_name = f"{product_name} ({brands})"

                # Simplified data for category browsing
                suggestion = {
                    'name': product_name[:100],
                    'barcode': product.get('code', ''),
                    'brands': brands,
                    'categories': product.get('categories', ''),
                    'image_url': product.get('image_url', ''),
                    'calories_per_100g': nutriments.get('energy-kcal_100g', 0)
                }

                results.append(suggestion)

        return {"status": "success", "products": results}

    except Exception as e:
        return {"status": "error", "message": f"Failed to get category products: {str(e)}"}

@router.post("/foods/add_openfoodfacts")
async def add_openfoodfacts_food(request: Request, db: Session = Depends(get_db),
                                name: str = Form(...), serving_size: str = Form(...),
                                serving_unit: str = Form(...), calories: float = Form(...),
                                protein: float = Form(...), carbs: float = Form(...),
                                fat: float = Form(...), fiber: float = Form(0),
                                sugar: float = Form(0), sodium: float = Form(0),
                                calcium: float = Form(0), openfoodfacts_id: str = Form(""),
                                brand: str = Form(""), categories: str = Form("")):

    try:
        # Create a more descriptive name if brand is provided
        display_name = name
        if brand and brand not in name:
            display_name = f"{name} ({brand})"
            
        food = Food(
            name=display_name, 
            serving_size=serving_size, 
            serving_unit=serving_unit,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
            sugar=sugar,
            sodium=sodium,
            calcium=calcium,
            source="openfoodfacts",
            brand=brand # Add brand here
        )
        db.add(food)
        db.commit()
        return {"status": "success", "message": "Food added from OpenFoodFacts successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
