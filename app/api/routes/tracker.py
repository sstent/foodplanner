from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime, timedelta
import logging
from typing import List, Optional

# Import from the database module
from app.database import get_db, Meal, Template, TemplateMeal, TrackedDay, TrackedMeal, calculate_meal_nutrition
from main import templates

router = APIRouter()

# Import from the database module
from app.database import get_db, Meal, Template, TemplateMeal, TrackedDay, TrackedMeal, calculate_meal_nutrition, calculate_day_nutrition_tracked
from main import templates

# Tracker tab - Main page
@router.get("/tracker", response_class=HTMLResponse)
async def tracker_page(request: Request, person: str = "Sarah", date: str = None, db: Session = Depends(get_db)):
    logging.info(f"DEBUG: Tracker page requested with person={person}, date={date}")
    
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
        logging.info(f"DEBUG: Created new tracked day for {person} on {current_date}")
    
    # Get tracked meals for this day
    tracked_meals = db.query(TrackedMeal).filter(
        TrackedMeal.tracked_day_id == tracked_day.id
    ).all()
    
    # Get all meals for dropdown
    meals = db.query(Meal).all()
    
    # Get all templates for template dropdown
    templates_list = db.query(Template).all()
    
    # Calculate day totals
    day_totals = calculate_day_nutrition_tracked(tracked_meals, db)
    
    logging.info(f"DEBUG: Rendering tracker page with {len(tracked_meals)} tracked meals")
    
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
        "templates": templates_list
    })

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
        quantity = float(form_data.get("quantity", 1.0))
        
        logging.info(f"DEBUG: Adding meal to tracker - person={person}, date={date_str}, meal_id={meal_id}, meal_time={meal_time}, quantity={quantity}")
        
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
            meal_time=meal_time,
            quantity=quantity
        )
        db.add(tracked_meal)
        
        # Mark day as modified
        tracked_day.is_modified = True
        
        db.commit()
        
        logging.info(f"DEBUG: Successfully added meal to tracker")
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"DEBUG: Error adding meal to tracker: {e}")
        return {"status": "error", "message": str(e)}

@router.delete("/tracker/remove_meal/{tracked_meal_id}")
async def tracker_remove_meal(tracked_meal_id: int, db: Session = Depends(get_db)):
    """Remove a meal from the tracker"""
    try:
        logging.info(f"DEBUG: Removing tracked meal with ID: {tracked_meal_id}")
        
        tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.id == tracked_meal_id).first()
        if not tracked_meal:
            return {"status": "error", "message": "Tracked meal not found"}
        
        # Get the tracked day to mark as modified
        tracked_day = tracked_meal.tracked_day
        tracked_day.is_modified = True
        
        db.delete(tracked_meal)
        db.commit()
        
        logging.info(f"DEBUG: Successfully removed tracked meal")
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"DEBUG: Error removing tracked meal: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/tracker/save_template")
async def tracker_save_template(request: Request, db: Session = Depends(get_db)):
    """Save current day's meals as a template"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        template_name = form_data.get("template_name")
        
        logging.info(f"DEBUG: Saving template - name={template_name}, person={person}, date={date_str}")
        
        # Parse date
        from datetime import datetime
        date = datetime.fromisoformat(date_str).date()
        
        # Get tracked day and meals
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == date
        ).first()
        
        if not tracked_day:
            return {"status": "error", "message": "No tracked day found"}
        
        tracked_meals = db.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day.id
        ).all()
        
        if not tracked_meals:
            return {"status": "error", "message": "No meals to save as template"}
        
        # Create template
        template = Template(name=template_name)
        db.add(template)
        db.flush()
        
        # Add template meals
        for tracked_meal in tracked_meals:
            template_meal = TemplateMeal(
                template_id=template.id,
                meal_id=tracked_meal.meal_id,
                meal_time=tracked_meal.meal_time
            )
            db.add(template_meal)
        db.commit()
        
        logging.info(f"DEBUG: Successfully saved template with {len(tracked_meals)} meals")
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"DEBUG: Error saving template: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/tracker/apply_template")
async def tracker_apply_template(request: Request, db: Session = Depends(get_db)):
    """Apply a template to the current day"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        template_id = form_data.get("template_id")
        
        logging.info(f"DEBUG: Applying template - template_id={template_id}, person={person}, date={date_str}")
        
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
                meal_time=template_meal.meal_time,
                quantity=1.0
            )
            db.add(tracked_meal)
        
        db.commit()
        
        logging.info(f"DEBUG: Successfully applied template with {len(template_meals)} meals")
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"DEBUG: Error applying template: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/tracker/reset_to_plan")
async def tracker_reset_to_plan(request: Request, db: Session = Depends(get_db)):
    """Reset tracked day back to original plan"""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("date")
        
        logging.info(f"DEBUG: Resetting to plan - person={person}, date={date_str}")
        
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
        
        logging.info(f"DEBUG: Successfully reset to plan")
        return {"status": "success"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"DEBUG: Error resetting to plan: {e}")
        return {"status": "error", "message": str(e)}