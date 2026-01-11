from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, File, UploadFile, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
import os
import csv
import shutil
import sqlite3
import logging
from openfoodfacts import API, APIVersion, Country, Environment, Flavor
import re
import json

from app.database import get_db, Food, Meal, Plan, Template, WeeklyMenu, TrackedDay, MealFood, TemplateMeal, WeeklyMenuDay, TrackedMeal
from app.database import FoodCreate, FoodResponse, MealCreate, TrackedDayCreate, TrackedMealCreate, AllData, FoodExport, MealFoodExport, MealExport, PlanExport, TemplateMealExport, TemplateExport, TemplateMealDetail, TemplateDetail, WeeklyMenuDayExport, WeeklyMenuDayDetail, WeeklyMenuExport, WeeklyMenuDetail, TrackedMealExport, TrackedDayExport, TrackedMealFoodExport

router = APIRouter()

def validate_import_data(data: AllData):
    """Validate the integrity of the imported data."""
    food_ids = {f.id for f in data.foods}
    meal_ids = {m.id for m in data.meals}
    template_ids = {t.id for t in data.templates}

    # Validate Meals
    for meal in data.meals:
        for meal_food in meal.meal_foods:
            if meal_food.food_id not in food_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid meal food: food_id {meal_food.food_id} not found.",
                )

    # Validate Plans
    for plan in data.plans:
        if plan.meal_id not in meal_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan: meal_id {plan.meal_id} not found.",
            )

    # Validate Templates
    for template in data.templates:
        for template_meal in template.template_meals:
            if template_meal.meal_id not in meal_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid template meal: meal_id {template_meal.meal_id} not found.",
                )

    # Validate Weekly Menus
    for weekly_menu in data.weekly_menus:
        for day in weekly_menu.weekly_menu_days:
            if day.template_id not in template_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid weekly menu day: template_id {day.template_id} not found.",
                )

    # Validate Tracked Days
    for tracked_day in data.tracked_days:
        for tracked_meal in tracked_day.tracked_meals:
            if tracked_meal.meal_id not in meal_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tracked meal: meal_id {tracked_meal.meal_id} not found.",
                )

@router.get("/export/all")
async def export_all_data(db: Session = Depends(get_db)):
    """Export all data from the database as a single JSON file."""

    try:
        # ... (rest of the code)
        foods = db.query(Food).all()
        meals = db.query(Meal).all()
        plans = db.query(Plan).all()
        templates = db.query(Template).all()
        weekly_menus = db.query(WeeklyMenu).all()
        tracked_days = db.query(TrackedDay).all()

        # Manual serialization to handle nested relationships
        
        # Meals with MealFoods
        meals_export = []
        for meal in meals:
            meal_foods_export = [
                MealFoodExport(food_id=mf.food_id, quantity=mf.quantity)
                for mf in meal.meal_foods
            ]
            meals_export.append(
                MealExport(
                    id=meal.id,
                    name=meal.name,
                    meal_type=meal.meal_type,
                    meal_time=meal.meal_time,
                    meal_foods=meal_foods_export,
                )
            )

        # Templates with TemplateMeals
        templates_export = []
        for template in templates:
            template_meals_export = [
                TemplateMealExport(meal_id=tm.meal_id, meal_time=tm.meal_time)
                for tm in template.template_meals
            ]
            templates_export.append(
                TemplateExport(
                    id=template.id,
                    name=template.name,
                    template_meals=template_meals_export,
                )
            )

        # Weekly Menus with WeeklyMenuDays
        weekly_menus_export = []
        for weekly_menu in weekly_menus:
            weekly_menu_days_export = [
                WeeklyMenuDayExport(
                    day_of_week=wmd.day_of_week, template_id=wmd.template_id
                )
                for wmd in weekly_menu.weekly_menu_days
            ]
            weekly_menus_export.append(
                WeeklyMenuExport(
                    id=weekly_menu.id,
                    name=weekly_menu.name,
                    weekly_menu_days=weekly_menu_days_export,
                )
            )

        # Tracked Days with TrackedMeals
        tracked_days_export = []
        for tracked_day in tracked_days:
            tracked_meals_export = [
                TrackedMealExport(
                    meal_id=tm.meal_id,
                    meal_time=tm.meal_time,
                    tracked_foods=[
                         TrackedMealFoodExport(
                             food_id=tmf.food_id,
                             quantity=tmf.quantity,
                             is_override=tmf.is_override
                         ) for tmf in tm.tracked_foods
                    ]
                )
                for tm in tracked_day.tracked_meals
            ]
            tracked_days_export.append(
                TrackedDayExport(
                    id=tracked_day.id,
                    person=tracked_day.person,
                    date=tracked_day.date,
                    is_modified=tracked_day.is_modified,
                    tracked_meals=tracked_meals_export,
                )
            )

        data = AllData(
            foods=[FoodExport.from_orm(f) for f in foods],
            meals=meals_export,
            plans=[PlanExport.from_orm(p) for p in plans],
            templates=templates_export,
            weekly_menus=weekly_menus_export,
            tracked_days=tracked_days_export,
        )
        
        json_content = data.model_dump_json()
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=meal_planner_backup.json"}
        )
    except Exception as e:
        import traceback
        logging.error(f"Error exporting data: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/all")
async def import_all_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import all data from a JSON file, overwriting existing data."""
    try:
        contents = await file.read()
        data = AllData.parse_raw(contents)

        # Validate data before import
        validate_import_data(data)

        # 1. Delete existing data in the correct order
        db.query(TrackedMeal).delete()
        db.query(TrackedDay).delete()
        db.query(WeeklyMenuDay).delete()
        db.query(WeeklyMenu).delete()
        db.query(Plan).delete()
        db.query(TemplateMeal).delete()
        db.query(Template).delete()
        db.query(MealFood).delete()
        db.query(Meal).delete()
        db.query(Food).delete()
        db.commit()

        # 2. Insert new data in the correct order
        # Foods
        for food_data in data.foods:
            db.add(Food(**food_data.dict()))
        db.commit()

        # Meals
        for meal_data in data.meals:
            meal = Meal(
                id=meal_data.id,
                name=meal_data.name,
                meal_type=meal_data.meal_type,
                meal_time=meal_data.meal_time,
            )
            db.add(meal)
            db.flush()
            for mf_data in meal_data.meal_foods:
                db.add(
                    MealFood(
                        meal_id=meal.id,
                        food_id=mf_data.food_id,
                        quantity=mf_data.quantity,
                    )
                )
        db.commit()

        # Templates
        for template_data in data.templates:
            template = Template(id=template_data.id, name=template_data.name)
            db.add(template)
            db.flush()
            for tm_data in template_data.template_meals:
                db.add(
                    TemplateMeal(
                        template_id=template.id,
                        meal_id=tm_data.meal_id,
                        meal_time=tm_data.meal_time,
                    )
                )
        db.commit()
        
        # Plans
        for plan_data in data.plans:
            db.add(Plan(**plan_data.dict()))
        db.commit()

        # Weekly Menus
        for weekly_menu_data in data.weekly_menus:
            weekly_menu = WeeklyMenu(
                id=weekly_menu_data.id, name=weekly_menu_data.name
            )
            db.add(weekly_menu)
            db.flush()
            for wmd_data in weekly_menu_data.weekly_menu_days:
                db.add(
                    WeeklyMenuDay(
                        weekly_menu_id=weekly_menu.id,
                        day_of_week=wmd_data.day_of_week,
                        template_id=wmd_data.template_id,
                    )
                )
        db.commit()

        # Tracked Days
        for tracked_day_data in data.tracked_days:
            tracked_day = TrackedDay(
                id=tracked_day_data.id,
                person=tracked_day_data.person,
                date=tracked_day_data.date,
                is_modified=tracked_day_data.is_modified,
            )
            db.add(tracked_day)
            db.flush()
            for tm_data in tracked_day_data.tracked_meals:
                db.add(
                    TrackedMeal(
                        tracked_day_id=tracked_day.id,
                        meal_id=tm_data.meal_id,
                        meal_time=tm_data.meal_time,
                    )
                )
        db.commit()

        return {"status": "success", "message": "All data imported successfully."}

    except Exception as e:
        db.rollback()
        logging.error(f"Failed to import data: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to import data: {e}")