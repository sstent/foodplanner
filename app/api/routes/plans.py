from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
import logging
from typing import List, Optional

# Import from the database module
from app.database import get_db, Food, Meal, MealFood, Plan, Template, TemplateMeal, WeeklyMenu, WeeklyMenuDay, TrackedDay, TrackedMeal, calculate_meal_nutrition, calculate_day_nutrition, calculate_tracked_meal_nutrition
from sqlalchemy.orm import joinedload
from main import templates

router = APIRouter()

# Plan tab
@router.get("/plan", response_class=HTMLResponse)
async def plan_page(request: Request, person: str = "Sarah", week_start_date: str = None, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    # If no week_start_date provided, use current week starting from Monday
    if not week_start_date:
        today = datetime.now().date()
        # Find Monday of current week
        week_start_date_obj = (today - timedelta(days=today.weekday()))
    else:
        week_start_date_obj = datetime.fromisoformat(week_start_date).date()

    # Generate 7 days starting from Monday
    days = []
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for i in range(7):
        day_date = week_start_date_obj + timedelta(days=i)
        days.append({
            'date': day_date,
            'name': day_names[i],
            'display': day_date.strftime('%b %d')
        })

    # Get plans for the person for this week
    plans = {}
    for day in days:
        try:
            day_plans = db.query(Plan).filter(Plan.person == person, Plan.date == day['date']).all()
            plans[day['date'].isoformat()] = day_plans
        except Exception as e:
            print(f"Error loading plans for {day['date']}: {e}")
            plans[day['date'].isoformat()] = []

    # Calculate daily totals
    daily_totals = {}
    for day in days:
        day_key = day['date'].isoformat()
        daily_totals[day_key] = calculate_day_nutrition(plans[day_key], db)

    meals = db.query(Meal).all()

    # Calculate previous and next week dates
    prev_week = (week_start_date_obj - timedelta(days=7)).isoformat()
    next_week = (week_start_date_obj + timedelta(days=7)).isoformat()

    # Debug logging
    print(f"DEBUG: days structure: {days}")
    print(f"DEBUG: first day: {days[0] if days else 'No days'}")

    return templates.TemplateResponse("plan.html", {
        "request": request, "person": person, "days": days,
        "plans": plans, "daily_totals": daily_totals, "meals": meals,
        "week_start_date": week_start_date_obj.isoformat(),
        "prev_week": prev_week, "next_week": next_week,
        "week_range": f"{days[0]['display']} - {days[-1]['display']}, {week_start_date_obj.year}"
    })

@router.post("/plan/add")
async def add_to_plan(request: Request, person: str = Form(None),
                      plan_date: str = Form(None), meal_id: str = Form(None),
                      meal_time: str = Form(None), db: Session = Depends(get_db)):

    print(f"DEBUG: add_to_plan called with person={person}, plan_date={plan_date}, meal_id={meal_id}, meal_time={meal_time}")

    # Validate required fields
    if not person or not plan_date or not meal_id or not meal_time:
        missing = []
        if not person: missing.append("person")
        if not plan_date: missing.append("plan_date")
        if not meal_id: missing.append("meal_id")
        if not meal_time: missing.append("meal_time")
        print(f"DEBUG: Missing required fields: {missing}")
        return {"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}

    try:
        from datetime import datetime
        plan_date_obj = datetime.fromisoformat(plan_date).date()
        print(f"DEBUG: parsed plan_date_obj={plan_date_obj}")

        meal_id_int = int(meal_id)

        # Check if meal exists
        meal = db.query(Meal).filter(Meal.id == meal_id_int).first()
        if not meal:
            print(f"DEBUG: Meal with id {meal_id_int} not found")
            return {"status": "error", "message": f"Meal with id {meal_id_int} not found"}

        plan = Plan(person=person, date=plan_date_obj, meal_id=meal_id_int, meal_time=meal_time)
        db.add(plan)
        db.commit()
        print(f"DEBUG: Successfully added plan")
        return {"status": "success"}
    except ValueError as e:
        print(f"DEBUG: ValueError: {str(e)}")
        return {"status": "error", "message": f"Invalid data: {str(e)}"}
    except Exception as e:
        print(f"DEBUG: Exception in add_to_plan: {str(e)}")
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/plan/{person}/{date}")
async def get_day_plan(person: str, date: str, db: Session = Depends(get_db)):
    """Get all meals for a specific date"""
    try:
        from datetime import datetime
        plan_date = datetime.fromisoformat(date).date()
        plans = db.query(Plan).filter(Plan.person == person, Plan.date == plan_date).all()
        
        meal_details = []
        for plan in plans:
            meal_details.append({
                "id": plan.id,
                "meal_id": plan.meal_id,
                "meal_name": plan.meal.name,
                "meal_type": plan.meal.meal_type,
                "meal_time": plan.meal_time
            })
        
        # Calculate daily totals using the same logic as plan_page
        day_totals = calculate_day_nutrition(plans, db)

        return {"meals": meal_details, "day_totals": day_totals}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/plan/update_day")
async def update_day_plan(request: Request, person: str = Form(...),
                          date: str = Form(...), meal_ids: str = Form(...),
                          db: Session = Depends(get_db)):
    """Replace all meals for a specific date"""
    try:
        from datetime import datetime
        plan_date = datetime.fromisoformat(date).date()

        # Parse meal_ids (comma-separated string)
        meal_id_list = [int(x.strip()) for x in meal_ids.split(',') if x.strip()]

        # Delete existing plans for this date
        db.query(Plan).filter(Plan.person == person, Plan.date == plan_date).delete()

        # Add new plans
        for meal_id in meal_id_list:
            # For now, assign a default meal_time. This will be refined later.
            plan = Plan(person=person, date=plan_date, meal_id=meal_id, meal_time="Breakfast")
            db.add(plan)

        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.delete("/plan/{plan_id}")
async def remove_from_plan(plan_id: int, db: Session = Depends(get_db)):
    """Remove a specific meal from a plan"""
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            return {"status": "error", "message": "Plan not found"}
        
        db.delete(plan)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/detailed", response_class=HTMLResponse, name="detailed")
async def detailed(request: Request, person: str = "Sarah", plan_date: str = None, template_id: int = None, db: Session = Depends(get_db)):
    from datetime import datetime, date
    logging.info(f"DEBUG: Detailed page requested with url: {request.url.path}, query_params: {request.query_params}")
    logging.info(f"DEBUG: Detailed page requested with person={person}, plan_date={plan_date}, template_id={template_id}")

    # Get all templates for the dropdown
    templates_list = db.query(Template).order_by(Template.name).all()

    if template_id:
        # Show template details
        logging.info(f"DEBUG: Loading template with id: {template_id}")
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            logging.error(f"DEBUG: Template with id {template_id} not found")
            return templates.TemplateResponse(request, "detailed.html", {
                "request": request, "title": "Template Not Found",
                "error": "Template not found",
                "day_totals": {},
                "templates": templates_list,
                "person": person
            })

        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).all()
        logging.info(f"DEBUG: Found {len(template_meals)} meals for template id {template_id}")

        # Calculate template nutrition
        template_nutrition = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0}

        meal_details = []
        for tm in template_meals:
            meal_nutrition = calculate_meal_nutrition(tm.meal, db)
            foods = []
            
            # Show individual foods in template meals
            for mf in tm.meal.meal_foods:
                foods.append({
                    'name': mf.food.name,
                    'quantity': mf.quantity,
                    'serving_size': mf.food.serving_size,
                    'serving_unit': mf.food.serving_unit,
                    'calories': mf.food.calories * mf.quantity,
                    'protein': mf.food.protein * mf.quantity,
                    'carbs': mf.food.carbs * mf.quantity,
                    'fat': mf.food.fat * mf.quantity,
                    'fiber': (mf.food.fiber or 0) * mf.quantity,
                    'sodium': (mf.food.sodium or 0) * mf.quantity,
                })
            
            meal_details.append({
                'plan': {'meal': tm.meal, 'meal_time': tm.meal_time},
                'nutrition': meal_nutrition,
                'foods': foods  # Now includes food breakdown
            })

            for key in template_nutrition:
                if key in meal_nutrition:
                    template_nutrition[key] += meal_nutrition[key]

        # Calculate percentages
        total_cals = template_nutrition['calories']
        if total_cals > 0:
            template_nutrition['protein_pct'] = round((template_nutrition['protein'] * 4 / total_cals) * 100, 1)
            template_nutrition['carbs_pct'] = round((template_nutrition['carbs'] * 4 / total_cals) * 100, 1)
            template_nutrition['fat_pct'] = round((template_nutrition['fat'] * 9 / total_cals) * 100, 1)
            template_nutrition['net_carbs'] = template_nutrition['carbs'] - template_nutrition.get('fiber', 0)
        
        context = {
            "request": request,
            "title": f"{template.name} Template",
            "meal_details": meal_details,
            "day_totals": template_nutrition,
            "person": person,
            "templates": templates_list,
            "selected_template_id": template_id
        }
        logging.info(f"DEBUG: Rendering template details with context: {context}")
        return templates.TemplateResponse(request, "detailed.html", context)

    # When viewing a specific date, show TRACKED meals, not planned meals
    if plan_date:
        try:
            plan_date_obj = datetime.fromisoformat(plan_date).date()
        except ValueError:
            logging.error(f"debug: invalid date format plan_date: {plan_date}")
            return templates.TemplateResponse("detailed.html", {
                "request": request,
                "title": "Invalid date",
                "error": "Invalid date format. Please use YYYY-MM-DD.",
                "day_totals": {},
                "templates": templates_list,
                "person": person
            })

        logging.info(f"debug: loading TRACKED meals for {person} on {plan_date_obj}")
        
        # Get tracked day and meals instead of planned meals
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == plan_date_obj
        ).first()
        
        meal_details = []
        day_totals = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0}
        
        if tracked_day:
            tracked_meals = db.query(TrackedMeal).filter(
                TrackedMeal.tracked_day_id == tracked_day.id
            ).options(joinedload(TrackedMeal.meal).joinedload(Meal.meal_foods).joinedload(MealFood.food)).all()
            
            logging.info(f"debug: found {len(tracked_meals)} tracked meals for {person} on {plan_date_obj}")
            
            for tracked_meal in tracked_meals:
                meal_nutrition = calculate_tracked_meal_nutrition(tracked_meal, db)
                foods = []
                
                # Show base meal foods
                for mf in tracked_meal.meal.meal_foods:
                    foods.append({
                        'name': mf.food.name,
                        'quantity': mf.quantity,
                        'serving_size': mf.food.serving_size,
                        'serving_unit': mf.food.serving_unit,
                        'calories': mf.food.calories * mf.quantity,
                        'protein': mf.food.protein * mf.quantity,
                        'carbs': mf.food.carbs * mf.quantity,
                        'fat': mf.food.fat * mf.quantity,
                        'fiber': (mf.food.fiber or 0) * mf.quantity,
                        'sodium': (mf.food.sodium or 0) * mf.quantity,
                    })
                
                # Show custom tracked foods (overrides/additions)
                for tracked_food in tracked_meal.tracked_foods:
                    foods.append({
                        'name': f"{tracked_food.food.name} {'(override)' if tracked_food.is_override else '(addition)'}",
                        'quantity': tracked_food.quantity,
                        'serving_size': tracked_food.food.serving_size,
                        'serving_unit': tracked_food.food.serving_unit,
                        'calories': tracked_food.food.calories * tracked_food.quantity,
                        'protein': tracked_food.food.protein * tracked_food.quantity,
                        'carbs': tracked_food.food.carbs * tracked_food.quantity,
                        'fat': tracked_food.food.fat * tracked_food.quantity,
                        'fiber': (tracked_food.food.fiber or 0) * tracked_food.quantity,
                        'sodium': (tracked_food.food.sodium or 0) * tracked_food.quantity,
                    })
                
                meal_details.append({
                    'plan': tracked_meal,  # Use tracked_meal instead of plan
                    'nutrition': meal_nutrition,
                    'foods': foods
                })
                
                # Accumulate day totals
                for key in day_totals:
                    if key in meal_nutrition:
                        day_totals[key] += meal_nutrition[key]
        
        context = {
            "request": request,
            "title": f"Detailed Tracker - {person} - {plan_date_obj.strftime('%b %d, %Y')}",
            "meal_details": meal_details,
            "day_totals": day_totals,
            "person": person,
            "plan_date": plan_date_obj,
            "templates": templates_list,
            "is_tracked_view": True  # Add flag to indicate this is tracked view
        }
        
        # Add message if no meals tracked
        if not meal_details:
            context["message"] = "No meals tracked for this day."
        
        logging.info(f"debug: rendering tracked meal details context: {context}")
        return templates.TemplateResponse("detailed.html", context)
    else:
        # If no plan_date is provided, default to today's date
        plan_date_obj = date.today()
        
        logging.info(f"DEBUG: Loading plan for {person} on {plan_date_obj}")
        plans = db.query(Plan).filter(Plan.person == person, Plan.date == plan_date_obj).all()
        logging.info(f"DEBUG: Found {len(plans)} plans for {person} on {plan_date_obj}")

        day_totals = calculate_day_nutrition(plans, db)
        
        meal_details = []
        for plan in plans:
            meal_nutrition = calculate_meal_nutrition(plan.meal, db)
            
            foods = []
            for mf in plan.meal.meal_foods:
                foods.append({
                    'name': mf.food.name,
                    'quantity': mf.quantity,
                    'serving_size': mf.food.serving_size,
                    'serving_unit': mf.food.serving_unit,
                    'calories': mf.food.calories * mf.quantity,
                    'protein': mf.food.protein * mf.quantity,
                    'carbs': mf.food.carbs * mf.quantity,
                    'fat': mf.food.fat * mf.quantity,
                    'fiber': (mf.food.fiber or 0) * mf.quantity,
                    'sodium': (mf.food.sodium or 0) * mf.quantity,
                })
            
            meal_details.append({
                'plan': plan,
                'nutrition': meal_nutrition,
                'foods': foods
            })
        
        context = {
            "request": request,
            "title": f"Detailed Plan for {person} on {plan_date_obj.strftime('%B %d, %Y')}" if person else "Detailed View",
            "meal_details": meal_details,
            "day_totals": day_totals,
            "person": person,
            "plan_date": plan_date_obj,
            "templates": templates_list
        }
        
        # If no meals are planned, add a message
        if not meal_details:
            context["message"] = "No meals planned for this day."

        logging.info(f"DEBUG: Rendering plan details with context: {context}")
        return templates.TemplateResponse("detailed.html", context)