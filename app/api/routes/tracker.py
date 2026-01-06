from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime, timedelta
from typing import List, Optional, Union
import logging

# Import from the database module
from app.database import get_db, Meal, Template, TemplateMeal, TrackedDay, TrackedMeal, calculate_meal_nutrition, MealFood, TrackedMealFood, Food, calculate_day_nutrition_tracked, Plan
from main import templates

router = APIRouter()

# Tracker tab - Main page
@router.get("/tracker", response_class=HTMLResponse)
async def tracker_page(request: Request, person: str = "Sarah", date: str = None, db: Session = Depends(get_db)):
    try:
        from datetime import datetime, timedelta
        
        # If no date provided, use today
        if not date:
            current_date = datetime.now().date()
        else:
            current_date = datetime.fromisoformat(date).date()
        
        # Calculate previous and next dates
        prev_date = (current_date - timedelta(days=1)).isoformat()
        next_date = (current_date + timedelta(days=1)).isoformat()
        
        # Get or create tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == current_date
        ).first()
        
        if not tracked_day:
            # Create new tracked day
            tracked_day = TrackedDay(person=person, date=current_date, is_modified=False)
            db.add(tracked_day)
            db.commit()
            db.refresh(tracked_day)
            
        # Check if we need to sync from Plan (if no tracked meals exist)
        existing_meals_count = db.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day.id
        ).count()
        
        if existing_meals_count == 0:
            # Look for planned meals
            planned_meals = db.query(Plan).filter(
                Plan.person == person,
                Plan.date == current_date
            ).all()
            
            if planned_meals:
                logging.info(f"Syncing {len(planned_meals)} planned meals to tracker for {person} on {current_date}")
                for plan in planned_meals:
                    tracked_meal = TrackedMeal(
                        tracked_day_id=tracked_day.id,
                        meal_id=plan.meal_id,
                        meal_time=plan.meal_time
                    )
                    db.add(tracked_meal)
                db.commit()
        
        # Get tracked meals for this day with eager loading of meal foods
        tracked_meals = db.query(TrackedMeal).options(
            joinedload(TrackedMeal.meal)
            .joinedload(Meal.meal_foods)
            .joinedload(MealFood.food),
            joinedload(TrackedMeal.tracked_foods)
            .joinedload(TrackedMealFood.food)
        ).filter(
            TrackedMeal.tracked_day_id == tracked_day.id
        ).all()
        
        # Template will handle filtering of deleted foods
        # Get all meals for dropdown
        meals = db.query(Meal).all()
        
        # Get all templates for template dropdown
        templates_list = db.query(Template).all()

        # Get all foods for dropdown
        foods = db.query(Food).all()
        
        # Calculate day totals
        day_totals = calculate_day_nutrition_tracked(tracked_meals, db)
        
        return templates.TemplateResponse("tracker.html", {
            "request": request,
            "person": person,
            "current_date": current_date,
            "prev_date": prev_date,
            "next_date": next_date,
            "tracked_meals": tracked_meals,
            "is_modified": tracked_day.is_modified,
            "day_totals": day_totals,
            "meals": meals,
            "templates": templates_list,
            "foods": foods
        })
    
    except Exception as e:
        # Return a detailed error page instead of generic Internal Server Error
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_title": "Error Loading Tracker",
            "error_message": f"An error occurred while loading the tracker page: {str(e)}",
            "error_details": f"Person: {person}, Date: {date}"
        }, status_code=500)

# Tracker API Routes
@router.post("/tracker/add_meal")
async def tracker_add_meal(request: Request, db: Session = Depends(get_db)):
    """Add a meal to the tracker"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        meal_id = form_data.get("meal_id")
        meal_time = form_data.get("meal_time")
        
        
        # Parse date
        from datetime import datetime
        date = datetime.fromisoformat(date_str).date()
        
        # Get or create tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == date
        ).first()
        
        if not tracked_day:
            tracked_day = TrackedDay(person=person, date=date, is_modified=True)
            db.add(tracked_day)
            db.commit()
            db.refresh(tracked_day)
        
        # Create tracked meal
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=int(meal_id),
            meal_time=meal_time
        )
        db.add(tracked_meal)
        
        # Mark day as modified
        tracked_day.is_modified = True
        
        db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.delete("/tracker/remove_meal/{tracked_meal_id}")
async def tracker_remove_meal(tracked_meal_id: int, db: Session = Depends(get_db)):
    """Remove a meal from the tracker"""
    try:
        
        tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.id == tracked_meal_id).first()
        if not tracked_meal:
            return {"status": "error", "message": "Tracked meal not found"}
        
        # Get the tracked day to mark as modified
        tracked_day = tracked_meal.tracked_day
        tracked_day.is_modified = True
        
        db.delete(tracked_meal)
        db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/save_template")
async def tracker_save_template(request: Request, db: Session = Depends(get_db)):
    """save current day's meals as a new template"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        template_name = form_data.get("template_name")

        if not all([person, date_str, template_name]):
            raise HTTPException(status_code=400, detail="Missing required form data.")


        # 1. Check if template name already exists
        existing_template = db.query(Template).filter(Template.name == template_name).first()
        if existing_template:
            return {"status": "error", "message": f"Template name '{template_name}' already exists."}

        # 2. Find the tracked day and its meals
        from datetime import datetime
        target_date = datetime.fromisoformat(date_str).date()
        
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person, TrackedDay.date == target_date
        ).first()

        if not tracked_day:
            return {"status": "error", "message": "Tracked day not found for the given person and date."}

        tracked_meals = db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).all()

        if not tracked_meals:
            return {"status": "error", "message": "No meals found on this day to save as a template."}

        # 3. Create the new template
        new_template = Template(name=template_name)
        db.add(new_template)
        db.flush()  # Use flush to get the new_template.id before commit

        # 4. Create template_meal entries for each tracked meal
        for meal in tracked_meals:
            template_meal_entry = TemplateMeal(
                template_id=new_template.id,
                meal_id=meal.meal_id,
                meal_time=meal.meal_time
            )
            db.add(template_meal_entry)

        db.commit()
        return {"status": "success", "message": "Template saved successfully."}

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/apply_template")
async def tracker_apply_template(request: Request, db: Session = Depends(get_db)):
    """Apply a template to the current day"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        template_id = form_data.get("template_id")
        
        
        # Parse date
        from datetime import datetime
        date = datetime.fromisoformat(date_str).date()
        
        # Get template
        template = db.query(Template).filter(Template.id == int(template_id)).first()
        if not template:
            return {"status": "error", "message": "Template not found"}
        
        # Get template meals
        template_meals = db.query(TemplateMeal).filter(
            TemplateMeal.template_id == template.id
        ).all()
        
        if not template_meals:
            return {"status": "error", "message": "Template has no meals"}
        
        # Get or create tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == date
        ).first()
        
        if not tracked_day:
            tracked_day = TrackedDay(person=person, date=date, is_modified=True)
            db.add(tracked_day)
            db.commit()
            db.refresh(tracked_day)
        else:
            # Clear existing tracked meals
            db.query(TrackedMeal).filter(
                TrackedMeal.tracked_day_id == tracked_day.id
            ).delete()
            tracked_day.is_modified = True
        
        # Add template meals to tracked day
        for template_meal in template_meals:
            tracked_meal = TrackedMeal(
                tracked_day_id=tracked_day.id,
                meal_id=template_meal.meal_id,
                meal_time=template_meal.meal_time
            )
            db.add(tracked_meal)
        
        db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/update_tracked_food")
async def update_tracked_food(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update quantity of a custom food in a tracked meal"""
    try:
        tracked_food_id = data.get("tracked_food_id")
        grams = float(data.get("grams", 1.0))
        is_custom = data.get("is_custom", False)


        if is_custom:
            tracked_food = db.query(TrackedMealFood).filter(TrackedMealFood.id == tracked_food_id).first()
        else:
            # It's a MealFood, we need to create a TrackedMealFood for it
            meal_food = db.query(MealFood).filter(MealFood.id == tracked_food_id).first()
            if not meal_food:
                return {"status": "error", "message": "Meal food not found"}
            
            tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.meal_id == meal_food.meal_id).first()
            if not tracked_meal:
                return {"status": "error", "message": "Tracked meal not found"}

            tracked_food = TrackedMealFood(
                tracked_meal_id=tracked_meal.id,
                food_id=meal_food.food_id,
                quantity=grams
            )
            db.add(tracked_food)
            
            # We can now remove the original MealFood to avoid duplication
            db.delete(meal_food)

        if not tracked_food:
            return {"status": "error", "message": "Tracked food not found"}
        
        # Update quantity
        tracked_food.quantity = grams
        
        # Mark the tracked day as modified
        tracked_day = tracked_food.tracked_meal.tracked_day
        tracked_day.is_modified = True
        
        db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/clear_page")
async def tracker_clear_page(request: Request, db: Session = Depends(get_db)):
    """Clear all meals and foods from the tracker page for a given day"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        
        # Parse date
        from datetime import datetime
        date = datetime.fromisoformat(date_str).date()
        
        # Get tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == date
        ).first()
        
        if not tracked_day:
            return {"status": "success", "message": "No tracked day found to clear."} # Already clear
        
        # Delete all tracked meals associated with the tracked day
        db.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day.id
        ).delete()

        # Delete all tracked foods associated with the tracked day through meals
        # This handles directly added foods that might not be part of a meal
        db.query(TrackedMealFood).filter(
            TrackedMealFood.tracked_meal_id.in_(
                db.query(TrackedMeal.id).filter(TrackedMeal.tracked_day_id == tracked_day.id)
            )
        ).delete(synchronize_session=False) # Use synchronize_session=False for bulk delete

        # Mark the tracked day as not modified and commit
        tracked_day.is_modified = False
        db.commit()
        
        return {"status": "success", "message": "Tracker page cleared successfully."}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/reset_to_plan")
async def tracker_reset_to_plan(request: Request, db: Session = Depends(get_db)):
    """Reset tracked day back to original plan"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        
        
        # Parse date
        from datetime import datetime
        date = datetime.fromisoformat(date_str).date()
        
        # Get tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == date
        ).first()
        
        if not tracked_day:
            return {"status": "error", "message": "No tracked day found"}
        
        # Clear tracked meals
        db.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day.id
        ).delete()
        
        # Reset modified flag
        tracked_day.is_modified = False
        
        db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/tracker/get_tracked_meal_foods/{tracked_meal_id}")
async def get_tracked_meal_foods(tracked_meal_id: int, db: Session = Depends(get_db)):
    """Get foods associated with a tracked meal"""
    try:
        tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.id == tracked_meal_id).first()

        if not tracked_meal:
            raise HTTPException(status_code=404, detail="Tracked meal not found")

        # Load the associated Meal and its foods
        meal = db.query(Meal).options(joinedload(Meal.meal_foods).joinedload(MealFood.food)).filter(Meal.id == tracked_meal.meal_id).first()
        if not meal:
            raise HTTPException(status_code=404, detail="Associated meal not found")

        # Load custom tracked foods for this tracked meal
        tracked_foods = db.query(TrackedMealFood).options(joinedload(TrackedMealFood.food)).filter(TrackedMealFood.tracked_meal_id == tracked_meal_id).all()

        # New override-based logic
        meal_foods_data = []
        base_foods = {mf.food_id: mf for mf in meal.meal_foods}
        overrides = {tf.food_id: tf for tf in tracked_foods}

        # 1. Handle base meal foods, applying overrides where they exist
        for food_id, base_meal_food in base_foods.items():
            if food_id in overrides:
                override_food = overrides[food_id]
                if not override_food.is_deleted:
                    # This food is overridden, use the override's data
                    meal_foods_data.append({
                        "id": override_food.id,
                        "food_id": override_food.food.id,
                        "food_name": override_food.food.name,
                        "quantity": override_food.quantity,
                        "serving_unit": override_food.food.serving_unit,
                        "serving_size": override_food.food.serving_size,
                        "is_custom": True  # It's an override, so treat as custom
                    })
            else:
                # No override exists, use the base meal food data
                meal_foods_data.append({
                    "id": base_meal_food.id,
                    "food_id": base_meal_food.food.id,
                    "food_name": base_meal_food.food.name,
                    "quantity": base_meal_food.quantity,
                    "serving_unit": base_meal_food.food.serving_unit,
                    "serving_size": base_meal_food.food.serving_size,
                    "is_custom": False
                })

        # 2. Add new foods that are not in the base meal
        for food_id, tracked_food in overrides.items():
            if food_id not in base_foods and not tracked_food.is_deleted:
                meal_foods_data.append({
                    "id": tracked_food.id,
                    "food_id": tracked_food.food.id,
                    "food_name": tracked_food.food.name,
                    "quantity": tracked_food.quantity,
                    "serving_unit": tracked_food.food.serving_unit,
                    "serving_size": tracked_food.food.serving_size,
                    "is_custom": True
                })

        return {"status": "success", "meal_foods": meal_foods_data}

    except HTTPException as he:
        return {"status": "error", "message": he.detail}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tracker/add_food_to_tracked_meal")
async def add_food_to_tracked_meal(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a food to an existing tracked meal by creating a TrackedMealFood entry."""
    try:
        tracked_meal_id = data.get("tracked_meal_id")
        food_id = data.get("food_id")
        grams = float(data.get("grams", 1.0))

        tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.id == tracked_meal_id).first()
        if not tracked_meal:
            raise HTTPException(status_code=404, detail="Tracked meal not found")

        food = db.query(Food).filter(Food.id == food_id).first()
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")

        # Create a new TrackedMealFood entry to associate the food with the tracked meal
        tracked_meal_food = TrackedMealFood(
            tracked_meal_id=tracked_meal.id,
            food_id=food_id,
            quantity=grams,
            is_override=False # This is a new addition, not an override
        )
        db.add(tracked_meal_food)

        # Mark the tracked day as modified
        tracked_meal.tracked_day.is_modified = True

        db.commit()
        return {"status": "success"}

    except HTTPException as he:
        db.rollback()
        return {"status": "error", "message": he.detail}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/update_tracked_meal_foods")
async def update_tracked_meal_foods(data: dict = Body(...), db: Session = Depends(get_db)):
    """Update, add, or remove foods from a tracked meal using an override system."""
    try:
        tracked_meal_id = data.get("tracked_meal_id")
        foods_data = data.get("foods", [])
        removed_food_ids = data.get("removed_food_ids", [])

        tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.id == tracked_meal_id).first()
        if not tracked_meal:
            raise HTTPException(status_code=404, detail="Tracked meal not found")

        # Process removals: mark existing foods as deleted
        for food_id_to_remove in removed_food_ids:
            # Check if an override already exists
            override = db.query(TrackedMealFood).filter(
                TrackedMealFood.tracked_meal_id == tracked_meal_id,
                TrackedMealFood.food_id == food_id_to_remove
            ).first()
            if override:
                override.is_deleted = True
            else:
                # If no override exists, create one to mark the food as deleted
                new_override = TrackedMealFood(
                    tracked_meal_id=tracked_meal_id,
                    food_id=food_id_to_remove,
                    quantity=0, # Quantity is irrelevant for a deleted item
                    is_override=True,
                    is_deleted=True
                )
                db.add(new_override)

        # Process updates and additions
        for food_data in foods_data:
            food_id = food_data.get("food_id")
            grams = float(food_data.get("grams", 1.0))
            item_id = food_data.get("id") # This is the id from the frontend (TrackedMealFood.id or MealFood.id)
            is_custom = food_data.get("is_custom")

            print(f"  Processing food_id {food_id} (item_id: {item_id}, is_custom: {is_custom}) with grams {grams}")

            if is_custom and item_id and item_id != 0: # Existing TrackedMealFood (custom or override)
                tracked_food_entry = db.query(TrackedMealFood).filter(TrackedMealFood.id == item_id).first()
                if tracked_food_entry:
                    tracked_food_entry.quantity = grams
                    tracked_food_entry.is_deleted = False # Ensure it's not marked as deleted if being updated
                    print(f"    Updated existing TrackedMealFood (id: {item_id}) quantity to {grams}.")
                else:
                    print(f"    Error: TrackedMealFood with id {item_id} not found for update.")
                    # This case should ideally not happen if frontend sends correct IDs
            else: # New addition (from modal) or modification of a base MealFood
                # Check if an override (TrackedMealFood) already exists for this food_id
                existing_override = db.query(TrackedMealFood).filter(
                    TrackedMealFood.tracked_meal_id == tracked_meal_id,
                    TrackedMealFood.food_id == food_id
                ).first()

                if existing_override:
                    # Update existing override
                    existing_override.quantity = grams
                    existing_override.is_deleted = False
                    existing_override.is_override = True # Ensure it's marked as an override
                    print(f"    Updated existing override for food_id {food_id}. Quantity: {grams}.")
                else:
                    # Create new TrackedMealFood entry
                    # Determine if it's an override of a base meal food or a completely new food
                    base_meal_food_exists = db.query(MealFood).filter(
                        MealFood.meal_id == tracked_meal.meal_id,
                        MealFood.food_id == food_id
                    ).first()
                    
                    is_override_flag = base_meal_food_exists is not None
                    
                    new_entry = TrackedMealFood(
                        tracked_meal_id=tracked_meal_id,
                        food_id=food_id,
                        quantity=grams,
                        is_override=is_override_flag,
                        is_deleted=False
                    )
                    db.add(new_entry)
                    print(f"    Created new TrackedMealFood for food_id {food_id}. Quantity: {grams}, is_override: {is_override_flag}.")

        # Mark the tracked day as modified
        tracked_meal.tracked_day.is_modified = True

        db.commit()
        return {"status": "success"}

    except HTTPException as he:
        db.rollback()
        return {"status": "error", "message": he.detail}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}



@router.post("/tracker/save_as_new_meal")
async def save_as_new_meal(data: dict = Body(...), db: Session = Depends(get_db)):
    """Save an edited tracked meal as a new meal/variant"""
    try:
        tracked_meal_id = data.get("tracked_meal_id")
        new_meal_name = data.get("new_meal_name")
        foods_data = data.get("foods", [])

        if not new_meal_name:
            raise HTTPException(status_code=400, detail="New meal name is required")

        tracked_meal = db.query(TrackedMeal).options(
            joinedload(TrackedMeal.meal).joinedload(Meal.meal_foods).joinedload(MealFood.food),
            joinedload(TrackedMeal.tracked_foods).joinedload(TrackedMealFood.food)
        ).filter(TrackedMeal.id == tracked_meal_id).first()

        if not tracked_meal:
            raise HTTPException(status_code=404, detail="Tracked meal not found")

        # Create a new meal
        new_meal = Meal(name=new_meal_name, meal_type="custom", meal_time=tracked_meal.meal_time)
        db.add(new_meal)
        db.flush()  # Flush to get the new meal ID

        # Add foods to the new meal
        for food_data in foods_data:
            meal_food = MealFood(
                meal_id=new_meal.id,
                food_id=food_data["food_id"],
                quantity=food_data["grams"]
            )
            db.add(meal_food)

        # Update the original tracked meal to point to the new meal
        tracked_meal.meal_id = new_meal.id
        
        # Clear custom tracked foods from the original tracked meal
        for tf in tracked_meal.tracked_foods:
            db.delete(tf)
        
        # Mark the tracked day as modified
        tracked_meal.tracked_day.is_modified = True

        db.commit()
        db.refresh(new_meal)
        db.refresh(tracked_meal)

        return {"status": "success", "new_meal_id": new_meal.id}

    except HTTPException as he:
        db.rollback()
        return {"status": "error", "message": he.detail}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/tracker/add_food")
async def tracker_add_food(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a single food item to the tracker"""
    try:
        person = data.get("person")
        date_str = data.get("date")
        food_id = data.get("food_id")
        grams = float(data.get("quantity", 1.0))
        meal_time = data.get("meal_time")

        
        # Parse date
        from datetime import datetime
        date = datetime.fromisoformat(date_str).date()
        
        # Get or create tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == date
        ).first()
        
        if not tracked_day:
            tracked_day = TrackedDay(person=person, date=date, is_modified=True)
            db.add(tracked_day)
            db.commit()
            db.refresh(tracked_day)
        
        food_item = db.query(Food).filter(Food.id == food_id).first()
        if not food_item:
            return {"status": "error", "message": "Food not found"}

        # Store grams directly
        quantity = grams

        # Create a new Meal for this single food entry
        # This allows it to be treated like any other meal in the tracker view
        new_meal = Meal(name=food_item.name, meal_type="single_food", meal_time=meal_time)
        db.add(new_meal)
        db.flush() # Flush to get the new meal ID

        # Link the food to the new meal
        meal_food = MealFood(meal_id=new_meal.id, food_id=food_id, quantity=grams)
        db.add(meal_food)
        
        # Create tracked meal entry
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=new_meal.id,
            meal_time=meal_time
        )
        db.add(tracked_meal)
        
        # Mark day as modified
        tracked_day.is_modified = True
        
        db.commit()
        
        return {"status": "success"}
        
    except ValueError as ve:
        db.rollback()
        return {"status": "error", "message": str(ve)}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
