from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime, timedelta
import logging
from typing import List, Optional

# Import from the database module
from app.database import get_db, Meal, Template, WeeklyMenu, WeeklyMenuDay, WeeklyMenuDetail, WeeklyMenuDayDetail, Plan
from main import templates

router = APIRouter()

#Weekly Menu tab
@router.get("/weeklymenu", response_class=HTMLResponse)
async def weekly_menu_page(request: Request, db: Session = Depends(get_db)):
    weekly_menus = db.query(WeeklyMenu).all()
    templates_list = db.query(Template).all()
    
    # Convert WeeklyMenu objects to dictionaries for JSON serialization
    weekly_menus_data = []
    for wm in weekly_menus:
        wm_dict = {
            "id": wm.id,
            "name": wm.name,
            "weekly_menu_days": []
        }
        for wmd in wm.weekly_menu_days:
            wm_dict["weekly_menu_days"].append({
                "day_of_week": wmd.day_of_week,
                "template_id": wmd.template_id,
                "template_name": wmd.template.name if wmd.template else "Unknown"
            })
        weekly_menus_data.append(wm_dict)
    
    logging.info(f"DEBUG: Loading weekly menu page with {len(weekly_menus_data)} weekly menus")
    
    return templates.TemplateResponse("weeklymenu.html", {
        "request": request,
        "weekly_menus": weekly_menus_data,
        "templates": templates_list
    })

@router.get("/api/weeklymenus", response_model=List[WeeklyMenuDetail])
async def get_weekly_menus_api(db: Session = Depends(get_db)):
    """API endpoint to get all weekly menus with template details."""
    weekly_menus = db.query(WeeklyMenu).options(joinedload(WeeklyMenu.weekly_menu_days).joinedload(WeeklyMenuDay.template)).all()
    
    results = []
    for wm in weekly_menus:
        day_details = [
            WeeklyMenuDayDetail(
                day_of_week=wmd.day_of_week,
                template_id=wmd.template_id,
                template_name=wmd.template.name if wmd.template else "Unknown"
            ) for wmd in wm.weekly_menu_days
        ]
        results.append(WeeklyMenuDetail(
            id=wm.id,
            name=wm.name,
            weekly_menu_days=day_details
        ))
    return results


@router.get("/weeklymenu/{weekly_menu_id}", response_model=WeeklyMenuDetail)
async def get_weekly_menu_detail(weekly_menu_id: int, db: Session = Depends(get_db)):
    """API endpoint to get a specific weekly menu with template details."""
    weekly_menu = db.query(WeeklyMenu).options(joinedload(WeeklyMenu.weekly_menu_days).joinedload(WeeklyMenuDay.template)).filter(WeeklyMenu.id == weekly_menu_id).first()
    
    if not weekly_menu:
        raise HTTPException(status_code=404, detail="Weekly menu not found")
    
    day_details = [
        WeeklyMenuDayDetail(
            day_of_week=wmd.day_of_week,
            template_id=wmd.template_id,
            template_name=wmd.template.name if wmd.template else "Unknown"
        ) for wmd in weekly_menu.weekly_menu_days
    ]
    return WeeklyMenuDetail(
        id=weekly_menu.id,
        name=weekly_menu.name,
        weekly_menu_days=day_details
    )

@router.post("/weeklymenu/create")
async def create_weekly_menu(request: Request, db: Session = Depends(get_db)):
    """Create a new weekly menu with template assignments."""
    try:
        form_data = await request.form()
        name = form_data.get("name")
        template_assignments_str = form_data.get("template_assignments")

        if not name:
            return {"status": "error", "message": "Weekly menu name is required"}

        # Check if weekly menu already exists
        existing_weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.name == name).first()
        if existing_weekly_menu:
            return {"status": "error", "message": f"Weekly menu with name '{name}' already exists"}

        weekly_menu = WeeklyMenu(name=name)
        db.add(weekly_menu)
        db.flush() # To get the weekly_menu.id

        if template_assignments_str:
            assignments = template_assignments_str.split(',')
            for assignment in assignments:
                day_of_week_str, template_id_str = assignment.split(':', 1)
                day_of_week = int(day_of_week_str)
                template_id = int(template_id_str)

                # Check if template exists
                template = db.query(Template).filter(Template.id == template_id).first()
                if not template:
                    raise HTTPException(status_code=400, detail=f"Template with ID {template_id} not found.")

                weekly_menu_day = WeeklyMenuDay(
                    weekly_menu_id=weekly_menu.id,
                    day_of_week=day_of_week,
                    template_id=template_id
                )
                db.add(weekly_menu_day)
        
        db.commit()
        return {"status": "success", "message": "Weekly menu created successfully"}

    except Exception as e:
        db.rollback()
        logging.error(f"Error creating weekly menu: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/weeklymenu/{weekly_menu_id}/apply")
async def apply_weekly_menu(weekly_menu_id: int, request: Request, db: Session = Depends(get_db)):
    """Apply a weekly menu to a person's plan for a specific week."""
    try:
        from datetime import datetime, timedelta
        form_data = await request.form()
        person = form_data.get("person")
        week_start_date_str = form_data.get("week_start_date")
        confirm_overwrite = form_data.get("confirm_overwrite") == "true"

        if not person or not week_start_date_str:
            return {"status": "error", "message": "Person and week start date are required."}

        week_start_date = datetime.fromisoformat(week_start_date_str).date()

        weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == weekly_menu_id).first()
        if not weekly_menu:
            return {"status": "error", "message": "Weekly menu not found."}

        # Check if there are existing plans for the target week
        existing_plans = db.query(Plan).filter(
            Plan.person == person,
            Plan.date >= week_start_date,
            Plan.date < (week_start_date + timedelta(days=7))
        ).all()

        if existing_plans and not confirm_overwrite:
            return {"status": "confirm_overwrite", "message": "Meals already planned for this week. Do you want to overwrite them?"}

        # If confirmed or no existing plans, delete existing plans for the week
        if existing_plans:
            db.query(Plan).filter(
                Plan.person == person,
                Plan.date >= week_start_date,
                Plan.date < (week_start_date + timedelta(days=7))
            ).delete()
            db.flush()

        # Apply each day of the weekly menu
        for weekly_menu_day in weekly_menu.weekly_menu_days:
            target_date = week_start_date + timedelta(days=weekly_menu_day.day_of_week)
            template = weekly_menu_day.template

            if template:
                for template_meal in template.template_meals:
                    plan = Plan(
                        person=person,
                        date=target_date,
                        meal_id=template_meal.meal_id,
                        meal_time=template_meal.meal_time
                    )
                    db.add(plan)
        
        db.commit()
        return {"status": "success", "message": "Weekly menu applied successfully."}

    except Exception as e:
        db.rollback()
        logging.error(f"Error applying weekly menu: {e}")
        return {"status": "error", "message": str(e)}


@router.put("/weeklymenu/{weekly_menu_id}")
async def update_weekly_menu(weekly_menu_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing weekly menu with new template assignments."""
    try:
        form_data = await request.form()
        name = form_data.get("name")
        template_assignments_str = form_data.get("template_assignments")

        weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == weekly_menu_id).first()
        if not weekly_menu:
            return {"status": "error", "message": "Weekly menu not found"}

        if not name:
            return {"status": "error", "message": "Weekly menu name is required"}

        # Check for duplicate name if changed
        if name != weekly_menu.name:
            existing_weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.name == name).first()
            if existing_weekly_menu:
                return {"status": "error", "message": f"Weekly menu with name '{name}' already exists"}

        weekly_menu.name = name

        # Clear existing weekly menu days
        db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu_id).delete()
        db.flush()

        # Process new template assignments
        if template_assignments_str:
            assignments = template_assignments_str.split(',')
            for assignment in assignments:
                day_of_week_str, template_id_str = assignment.split(':', 1)
                day_of_week = int(day_of_week_str)
                template_id = int(template_id_str)

                # Check if template exists
                template = db.query(Template).filter(Template.id == template_id).first()
                if not template:
                    raise HTTPException(status_code=400, detail=f"Template with ID {template_id} not found.")

                weekly_menu_day = WeeklyMenuDay(
                    weekly_menu_id=weekly_menu.id,
                    day_of_week=day_of_week,
                    template_id=template_id
                )
                db.add(weekly_menu_day)

        db.commit()
        return {"status": "success", "message": "Weekly menu updated successfully"}

    except Exception as e:
        db.rollback()
        logging.error(f"Error updating weekly menu: {e}")
        return {"status": "error", "message": str(e)}


@router.delete("/weeklymenu/{weekly_menu_id}")
async def delete_weekly_menu(weekly_menu_id: int, db: Session = Depends(get_db)):
    """Delete a weekly menu and its day assignments."""
    try:
        weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == weekly_menu_id).first()
        if not weekly_menu:
            return {"status": "error", "message": "Weekly menu not found"}

        # Delete associated weekly menu days
        db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu_id).delete()

        db.delete(weekly_menu)
        db.commit()

        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting weekly menu: {e}")
        return {"status": "error", "message": str(e)}