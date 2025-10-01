from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import csv
import logging
from typing import List, Optional

# Import from the database module
from app.database import get_db, Food, Meal, MealFood, convert_grams_to_quantity
from main import templates

router = APIRouter()

# Meals tab
@router.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request, db: Session = Depends(get_db)):
    meals = db.query(Meal).all()
    foods = db.query(Food).all()
    return templates.TemplateResponse("meals.html", 
                                    {"request": request, "meals": meals, "foods": foods})

@router.post("/meals/upload")
async def bulk_upload_meals(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Handle bulk meal upload from CSV"""
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8').splitlines()
        reader = csv.reader(decoded)
        
        stats = {'created': 0, 'updated': 0, 'errors': []}
        
        # Skip header
        header = next(reader)
        
        for row_num, row in enumerate(reader, 2):  # Start at row 2
            if not row:
                continue
                
            try:
                meal_name = row[0].strip()
                ingredients = []
                
                # Process ingredient pairs (item, grams)
                for i in range(1, len(row), 2):
                    if i+1 >= len(row) or not row[i].strip():
                        continue
                        
                    food_name = row[i].strip()
                    grams = float(row[i+1].strip())
                    quantity = convert_grams_to_quantity(food.id, grams, db)
                    
                    # Try multiple matching strategies for food names
                    food = None

                    # Strategy 1: Exact match
                    food = db.query(Food).filter(Food.name.ilike(food_name)).first()

                    # Strategy 2: Match food name within stored name (handles "ID (Brand) Name" format)
                    if not food:
                        food = db.query(Food).filter(Food.name.ilike(f"%{food_name}%")).first()

                    # Strategy 3: Try to match food name after closing parenthesis in "ID (Brand) Name" format
                    if not food:
                        # Look for pattern like ") mushrooms" at end of name
                        search_pattern = f") {food_name}"
                        food = db.query(Food).filter(Food.name.ilike(f"%{search_pattern}%")).first()

                    if not food:
                        logging.error(f"Food '{food_name}' not found in database.")
                        # Get all food names for debugging
                        all_foods = db.query(Food.name).limit(10).all()
                        food_names = [f[0] for f in all_foods]
                        raise ValueError(f"Food '{food_name}' not found. Available foods include: {', '.join(food_names[:5])}...")
                    logging.info(f"Found food '{food_name}' with id {food.id}")
                    ingredients.append((food.id, quantity))
                
                # Create/update meal
                existing = db.query(Meal).filter(Meal.name == meal_name).first()
                if existing:
                    # Remove existing ingredients
                    db.query(MealFood).filter(MealFood.meal_id == existing.id).delete()
                    existing.meal_type = "custom"  # Default type
                    stats['updated'] += 1
                else:
                    existing = Meal(name=meal_name, meal_type="custom")
                    db.add(existing)
                    stats['created'] += 1
                
                db.flush()  # Get meal ID
                
                # Add new ingredients
                for food_id, quantity in ingredients:
                    meal_food = MealFood(
                        meal_id=existing.id,
                        food_id=food_id,
                        quantity=quantity
                    )
                    db.add(meal_food)
                
                db.commit()
                
            except (ValueError, IndexError) as e:
                db.rollback()
                stats['errors'].append(f"Row {row_num}: {str(e)}")
            except Exception as e:
                db.rollback()
                stats['errors'].append(f"Row {row_num}: Unexpected error - {str(e)}")
                
        return stats
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/meals/add")
async def add_meal(request: Request, db: Session = Depends(get_db),
                  name: str = Form(...)):
    
    try:
        meal = Meal(name=name, meal_type="custom", meal_time="Custom")
        db.add(meal)
        db.commit()
        db.refresh(meal)
        return {"status": "success", "meal_id": meal.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/meals/edit")
async def edit_meal(request: Request, db: Session = Depends(get_db),
                   meal_id: int = Form(...), name: str = Form(...)):
    
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            return {"status": "error", "message": "Meal not found"}
        
        meal.name = name
        
        db.commit()
        return {"status": "success", "message": "Meal updated successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/meals/{meal_id}")
async def get_meal_details(meal_id: int, db: Session = Depends(get_db)):
    """Get details for a single meal"""
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            return {"status": "error", "message": "Meal not found"}
        
        return {
            "status": "success",
            "id": meal.id,
            "name": meal.name,
            "meal_type": meal.meal_type,
            "meal_time": meal.meal_time
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/meals/{meal_id}/foods")
async def get_meal_foods(meal_id: int, db: Session = Depends(get_db)):
    """Get all foods in a meal"""
    try:
        meal_foods = db.query(MealFood).filter(MealFood.meal_id == meal_id).all()
        result = []
        for mf in meal_foods:
            result.append({
                "id": mf.id,
                "food_id": mf.food_id,
                "food_name": mf.food.name,
                "quantity": mf.quantity
            })
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/meals/{meal_id}/add_food")
async def add_food_to_meal(meal_id: int, food_id: int = Form(...),
                           grams: float = Form(..., alias="quantity"), db: Session = Depends(get_db)):
    
    try:
        quantity = convert_grams_to_quantity(food_id, grams, db)
        meal_food = MealFood(meal_id=meal_id, food_id=food_id, quantity=quantity)
        db.add(meal_food)
        db.commit()
        return {"status": "success"}
    except ValueError as ve:
        db.rollback()
        return {"status": "error", "message": str(ve)}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.delete("/meals/remove_food/{meal_food_id}")
async def remove_food_from_meal(meal_food_id: int, db: Session = Depends(get_db)):
    """Remove a food from a meal"""
    try:
        meal_food = db.query(MealFood).filter(MealFood.id == meal_food_id).first()
        if not meal_food:
            return {"status": "error", "message": "Meal food not found"}
        
        db.delete(meal_food)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/meals/update_food_quantity")
async def update_meal_food_quantity(meal_food_id: int = Form(...), grams: float = Form(..., alias="quantity"), db: Session = Depends(get_db)):
    """Update the quantity of a food in a meal"""
    try:
        meal_food = db.query(MealFood).filter(MealFood.id == meal_food_id).first()
        if not meal_food:
            return {"status": "error", "message": "Meal food not found"}
        
        quantity = convert_grams_to_quantity(meal_food.food_id, grams, db)
        meal_food.quantity = quantity
        db.commit()
        return {"status": "success"}
    except ValueError as ve:
        db.rollback()
        return {"status": "error", "message": str(ve)}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/meals/clone/{meal_id}")
async def clone_meal(meal_id: int, db: Session = Depends(get_db)):
    """Clone an existing meal"""
    try:
        original_meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not original_meal:
            return {"status": "error", "message": "Original meal not found"}

        # Create new meal
        new_meal = Meal(
            name=f"{original_meal.name} - Copy",
            meal_type=original_meal.meal_type,
            meal_time=original_meal.meal_time
        )
        db.add(new_meal)
        db.flush()

        # Copy meal foods
        for meal_food in original_meal.meal_foods:
            new_meal_food = MealFood(
                meal_id=new_meal.id,
                food_id=meal_food.food_id,
                quantity=meal_food.quantity
            )
            db.add(new_meal_food)
        
        db.commit()
        return {"status": "success", "new_meal_id": new_meal.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/meals/delete")
async def delete_meals(meal_ids: dict = Body(...), db: Session = Depends(get_db)):
    try:
        # Delete meal foods first
        db.query(MealFood).filter(MealFood.meal_id.in_(meal_ids["meal_ids"])).delete(synchronize_session=False)
        # Delete meals
        db.query(Meal).filter(Meal.id.in_(meal_ids["meal_ids"])).delete(synchronize_session=False)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}