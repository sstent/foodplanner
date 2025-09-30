from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
import csv
import logging
from typing import List, Optional

# Import from the database module
from app.database import get_db, Meal, Template, TemplateMeal, TemplateDetail, TemplateMealDetail, TrackedDay, TrackedMeal
from main import templates

router = APIRouter()

@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request, db: Session = Depends(get_db)):
    meals = db.query(Meal).all()
    return templates.TemplateResponse(request, "templates.html", {"meals": meals})

@router.get("/api/templates", response_model=List[TemplateDetail])
async def get_templates_api(db: Session = Depends(get_db)):
    """API endpoint to get all templates with meal details."""
    templates = db.query(Template).options(joinedload(Template.template_meals).joinedload(TemplateMeal.meal)).all()
    
    results = []
    for t in templates:
        meal_details = [
            TemplateMealDetail(
                meal_id=tm.meal_id,
                meal_time=tm.meal_time,
                meal_name=tm.meal.name
            ) for tm in t.template_meals
        ]
        results.append(TemplateDetail(
            id=t.id,
            name=t.name,
            template_meals=meal_details
        ))
    return results

@router.post("/templates/upload")
async def bulk_upload_templates(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Handle bulk template upload from CSV"""
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)

        stats = {'created': 0, 'updated': 0, 'errors': []}

        for row_num, row in enumerate(reader, 2):  # Row numbers start at 2 (1-based + header)
            try:
                user = row.get('User', '').strip()
                template_id = row.get('ID', '').strip()

                if not user or not template_id:
                    stats['errors'].append(f"Row {row_num}: Missing User or ID")
                    continue

                # Create template name in format <User>-<ID>
                template_name = f"{user}-{template_id}"

                # Check if template already exists
                existing_template = db.query(Template).filter(Template.name == template_name).first()
                if existing_template:
                    # Update existing template - remove existing meals
                    db.query(TemplateMeal).filter(TemplateMeal.template_id == existing_template.id).delete()
                    template = existing_template
                    stats['updated'] += 1
                else:
                    # Create new template
                    template = Template(name=template_name)
                    db.add(template)
                    stats['created'] += 1

                db.flush()  # Get template ID

                # Meal time mappings from CSV columns
                meal_columns = {
                    'Beverage 1': 'Beverage 1',
                    'Breakfast': 'Breakfast',
                    'Lunch': 'Lunch',
                    'Dinner': 'Dinner',
                    'Snack 1': 'Snack 1',
                    'Snack 2': 'Snack 2'
                }

                # Process each meal column
                for csv_column, meal_time in meal_columns.items():
                    meal_name = row.get(csv_column, '').strip()
                    if meal_name:
                        # Find meal by name
                        meal = db.query(Meal).filter(Meal.name.ilike(meal_name)).first()
                        if meal:
                            # Create template meal
                            template_meal = TemplateMeal(
                                template_id=template.id,
                                meal_id=meal.id,
                                meal_time=meal_time
                            )
                            db.add(template_meal)
                        else:
                            stats['errors'].append(f"Row {row_num}: Meal '{meal_name}' not found for {meal_time}")

            except (KeyError, ValueError) as e:
                stats['errors'].append(f"Row {row_num}: {str(e)}")

        db.commit()
        return stats

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.post("/templates/create")
async def create_template(request: Request, db: Session = Depends(get_db)):
    """Create a new template with meal assignments."""
    try:
        form_data = await request.form()
        template_name = form_data.get("name")
        meal_assignments_str = form_data.get("meal_assignments")

        if not template_name:
            return {"status": "error", "message": "Template name is required"}

        # Check if template already exists
        existing_template = db.query(Template).filter(Template.name == template_name).first()
        if existing_template:
            return {"status": "error", "message": f"Template with name '{template_name}' already exists"}

        # Create new template
        template = Template(name=template_name)
        db.add(template)
        db.flush()

        # Process meal assignments
        if meal_assignments_str:
            logging.info(f"Processing meal assignments: {meal_assignments_str}")
            assignments = meal_assignments_str.split(',')
            for assignment in assignments:
                meal_time, meal_id_str = assignment.split(':', 1)
                logging.info(f"Processing assignment: meal_time='{meal_time}', meal_id_str='{meal_id_str}'")
                
                if not meal_id_str:
                    logging.warning(f"Skipping empty meal ID for meal_time '{meal_time}'")
                    continue
                
                meal_id = int(meal_id_str)
                meal = db.query(Meal).filter(Meal.id == meal_id).first()
                if meal:
                    template_meal = TemplateMeal(
                        template_id=template.id,
                        meal_id=meal.id,
                        meal_time=meal_time
                    )
                    db.add(template_meal)
                else:
                    logging.warning(f"Meal with ID {meal_id} not found for template '{template_name}'")

        db.commit()
        return {"status": "success", "message": "Template created successfully"}

    except Exception as e:
        db.rollback()
        logging.error(f"Error creating template: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/templates/{template_id}")
async def get_template_details(template_id: int, db: Session = Depends(get_db)):
    """Get details for a single template"""
    try:
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {"status": "error", "message": "Template not found"}
        
        template_meals_details = []
        for tm in template.template_meals:
            template_meals_details.append({
                "meal_id": tm.meal_id,
                "meal_time": tm.meal_time,
                "meal_name": tm.meal.name  # Include meal name for display
            })

        return {
            "status": "success",
            "template": {
                "id": template.id,
                "name": template.name,
                "template_meals": template_meals_details
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.put("/templates/{template_id}")
async def update_template(template_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing template with new meal assignments."""
    try:
        form_data = await request.form()
        template_name = form_data.get("name")
        meal_assignments_str = form_data.get("meal_assignments")

        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {"status": "error", "message": "Template not found"}

        if not template_name:
            return {"status": "error", "message": "Template name is required"}

        # Check for duplicate name if changed
        if template_name != template.name:
            existing_template = db.query(Template).filter(Template.name == template_name).first()
            if existing_template:
                return {"status": "error", "message": f"Template with name '{template_name}' already exists"}
        
        template.name = template_name
        
        # Clear existing template meals
        db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).delete()
        db.flush()

        # Process new meal assignments
        if meal_assignments_str:
            assignments = meal_assignments_str.split(',')
            for assignment in assignments:
                meal_time, meal_id_str = assignment.split(':')
                meal_id = int(meal_id_str)
                
                meal = db.query(Meal).filter(Meal.id == meal_id).first()
                if meal:
                    template_meal = TemplateMeal(
                        template_id=template.id,
                        meal_id=meal.id,
                        meal_time=meal_time
                    )
                    db.add(template_meal)
                else:
                    logging.warning(f"Meal with ID {meal_id} not found for template '{template_name}'")

        db.commit()
        return {"status": "success", "message": "Template updated successfully"}

    except Exception as e:
        db.rollback()
        logging.error(f"Error updating template: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/templates/{template_id}/use")
async def use_template(template_id: int, request: Request, db: Session = Depends(get_db)):
    """Apply a template to a specific date for a person."""
    try:
        form_data = await request.form()
        person = form_data.get("person")
        date_str = form_data.get("start_date") # Renamed from start_day to start_date
        
        if not person or not date_str:
            return {"status": "error", "message": "Person and date are required"}
        
        from datetime import datetime
        target_date = datetime.fromisoformat(date_str).date()

        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {"status": "error", "message": "Template not found"}
        
        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).all()
        if not template_meals:
            return {"status": "error", "message": "Template has no meals"}

        # Check for existing tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == target_date
        ).first()

        if not tracked_day:
            tracked_day = TrackedDay(person=person, date=target_date, is_modified=True)
            db.add(tracked_day)
            db.flush()
        else:
            # Clear existing meals for the tracked day
            db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).delete()
            tracked_day.is_modified = True
        
        for template_meal in template_meals:
            tracked_meal = TrackedMeal(
                tracked_day_id=tracked_day.id,
                meal_id=template_meal.meal_id,
                meal_time=template_meal.meal_time,
                quantity=1.0 # Default quantity when applying template
            )
            db.add(tracked_meal)
        
        db.commit()
        return {"status": "success", "message": "Template applied successfully"}

    except Exception as e:
        db.rollback()
        logging.error(f"Error applying template: {e}")
        return {"status": "error", "message": str(e)}

@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template and its meal assignments."""
    try:
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {"status": "error", "message": "Template not found"}

        # Delete associated template meals
        db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).delete()
        
        db.delete(template)
        db.commit()
        
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting template: {e}")
        return {"status": "error", "message": str(e)}