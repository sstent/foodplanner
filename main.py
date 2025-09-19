# Meal Planner FastAPI Application
# Run with: uvicorn main:app --reload

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Date
from sqlalchemy import or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import os
import csv
from fastapi import File, UploadFile

# Database setup - Use SQLite for easier setup
DATABASE_URL = "sqlite:///./meal_planner.db"
# For production, use PostgreSQL: DATABASE_URL = "postgresql://username:password@localhost/meal_planner"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize FastAPI app
app = FastAPI(title="Meal Planner")
templates = Jinja2Templates(directory="templates")

# Database Models
class Food(Base):
    __tablename__ = "foods"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    serving_size = Column(String)
    serving_unit = Column(String)
    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)
    fiber = Column(Float, default=0)
    sugar = Column(Float, default=0)
    sodium = Column(Float, default=0)
    calcium = Column(Float, default=0)

class Meal(Base):
    __tablename__ = "meals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    meal_type = Column(String)  # breakfast, lunch, dinner, snack, custom
    
    # Relationship to meal foods
    meal_foods = relationship("MealFood", back_populates="meal")

class MealFood(Base):
    __tablename__ = "meal_foods"
    
    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey("meals.id"))
    food_id = Column(Integer, ForeignKey("foods.id"))
    quantity = Column(Float)
    
    meal = relationship("Meal", back_populates="meal_foods")
    food = relationship("Food")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    person = Column(String, index=True)  # Person A or Person B
    date = Column(Date, index=True)  # Store actual calendar dates
    meal_id = Column(Integer, ForeignKey("meals.id"))

    meal = relationship("Meal")

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # Relationship to template meals
    template_meals = relationship("TemplateMeal", back_populates="template")

class TemplateMeal(Base):
    __tablename__ = "template_meals"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    meal_id = Column(Integer, ForeignKey("meals.id"))
    meal_time = Column(String)  # Breakfast, Lunch, Dinner, Snack 1, Snack 2, Beverage 1, Beverage 2

    template = relationship("Template", back_populates="template_meals")
    meal = relationship("Meal")

# Pydantic models
class FoodCreate(BaseModel):
    name: str
    serving_size: str
    serving_unit: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float = 0
    sugar: float = 0
    sodium: float = 0
    calcium: float = 0

class FoodResponse(BaseModel):
    id: int
    name: str
    serving_size: str
    serving_unit: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    sodium: float
    calcium: float

    class Config:
        from_attributes = True

class MealCreate(BaseModel):
    name: str
    meal_type: str
    foods: List[dict]  # [{"food_id": 1, "quantity": 1.5}]

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)

# Utility functions
def calculate_meal_nutrition(meal, db: Session):
    """Calculate total nutrition for a meal"""
    totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }
    
    for meal_food in meal.meal_foods:
        food = meal_food.food
        quantity = meal_food.quantity
        
        totals['calories'] += food.calories * quantity
        totals['protein'] += food.protein * quantity
        totals['carbs'] += food.carbs * quantity
        totals['fat'] += food.fat * quantity
        totals['fiber'] += (food.fiber or 0) * quantity
        totals['sugar'] += (food.sugar or 0) * quantity
        totals['sodium'] += (food.sodium or 0) * quantity
        totals['calcium'] += (food.calcium or 0) * quantity
    
    # Calculate percentages
    total_cals = totals['calories']
    if total_cals > 0:
        totals['protein_pct'] = round((totals['protein'] * 4 / total_cals) * 100, 1)
        totals['carbs_pct'] = round((totals['carbs'] * 4 / total_cals) * 100, 1)
        totals['fat_pct'] = round((totals['fat'] * 9 / total_cals) * 100, 1)
        totals['net_carbs'] = totals['carbs'] - totals['fiber']
    else:
        totals['protein_pct'] = 0
        totals['carbs_pct'] = 0
        totals['fat_pct'] = 0
        totals['net_carbs'] = 0
    
    return totals

def calculate_day_nutrition(plans, db: Session):
    """Calculate total nutrition for a day's worth of meals"""
    day_totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }
    
    for plan in plans:
        meal_nutrition = calculate_meal_nutrition(plan.meal, db)
        for key in day_totals:
            if key in meal_nutrition:
                day_totals[key] += meal_nutrition[key]
    
    # Calculate percentages
    total_cals = day_totals['calories']
    if total_cals > 0:
        day_totals['protein_pct'] = round((day_totals['protein'] * 4 / total_cals) * 100, 1)
        day_totals['carbs_pct'] = round((day_totals['carbs'] * 4 / total_cals) * 100, 1)
        day_totals['fat_pct'] = round((day_totals['fat'] * 9 / total_cals) * 100, 1)
        day_totals['net_carbs'] = day_totals['carbs'] - day_totals['fiber']
    else:
        day_totals['protein_pct'] = 0
        day_totals['carbs_pct'] = 0
        day_totals['fat_pct'] = 0
        day_totals['net_carbs'] = 0
    
    return day_totals

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Imports tab
@app.get("/imports", response_class=HTMLResponse)
async def imports_page(request: Request):
    return templates.TemplateResponse("imports.html", {"request": request})

# Foods tab
@app.get("/foods", response_class=HTMLResponse)
async def foods_page(request: Request, db: Session = Depends(get_db)):
    foods = db.query(Food).all()
    return templates.TemplateResponse("foods.html", {"request": request, "foods": foods})

@app.post("/foods/upload")
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
                    'calcium': round(float(row.get('Calcium (mg)', 0)), 2)
                }

                # Check for existing food
                existing = db.query(Food).filter(Food.name == food_data['name']).first()
                
                if existing:
                    # Update existing food
                    for key, value in food_data.items():
                        setattr(existing, key, value)
                    stats['updated'] += 1
                else:
                    # Create new food
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

@app.post("/foods/add")
async def add_food(request: Request, db: Session = Depends(get_db),
                  name: str = Form(...), serving_size: str = Form(...),
                  serving_unit: str = Form(...), calories: float = Form(...),
                  protein: float = Form(...), carbs: float = Form(...),
                  fat: float = Form(...), fiber: float = Form(0),
                  sugar: float = Form(0), sodium: float = Form(0),
                  calcium: float = Form(0)):
    
    try:
        food = Food(
            name=name, serving_size=serving_size, serving_unit=serving_unit,
            calories=calories, protein=protein, carbs=carbs, fat=fat,
            fiber=fiber, sugar=sugar, sodium=sodium, calcium=calcium
        )
        db.add(food)
        db.commit()
        return {"status": "success", "message": "Food added successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/foods/edit")
async def edit_food(request: Request, db: Session = Depends(get_db),
                   food_id: int = Form(...), name: str = Form(...), 
                   serving_size: str = Form(...), serving_unit: str = Form(...), 
                   calories: float = Form(...), protein: float = Form(...), 
                   carbs: float = Form(...), fat: float = Form(...), 
                   fiber: float = Form(0), sugar: float = Form(0), 
                   sodium: float = Form(0), calcium: float = Form(0)):
    
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
        
        db.commit()
        return {"status": "success", "message": "Food updated successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/foods/delete")
async def delete_foods(food_ids: dict = Body(...), db: Session = Depends(get_db)):
    try:
        # Delete foods
        db.query(Food).filter(Food.id.in_(food_ids["food_ids"])).delete(synchronize_session=False)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

# Meals tab
@app.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request, db: Session = Depends(get_db)):
    meals = db.query(Meal).all()
    foods = db.query(Food).all()
    return templates.TemplateResponse("meals.html", 
                                    {"request": request, "meals": meals, "foods": foods})

@app.post("/meals/upload")
async def bulk_upload_meals(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Handle bulk meal upload from CSV"""
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8').splitlines()
        reader = csv.reader(decoded)
        
        stats = {'created': 0, 'updated': 0, 'errors': []}
        
        # Skip header rows
        next(reader)  # First header
        next(reader)  # Second header
        
        for row_num, row in enumerate(reader, 3):  # Start at row 3
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
                    quantity = round(float(row[i+1].strip()) / 100, 3)  # Convert grams to 100g units and round to 3 decimal places
                    
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
                        # Get all food names for debugging
                        all_foods = db.query(Food.name).limit(10).all()
                        food_names = [f[0] for f in all_foods]
                        raise ValueError(f"Food '{food_name}' not found. Available foods include: {', '.join(food_names[:5])}...")
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

@app.post("/meals/add")
async def add_meal(request: Request, db: Session = Depends(get_db),
                  name: str = Form(...), meal_type: str = Form(...)):
    
    try:
        meal = Meal(name=name, meal_type=meal_type)
        db.add(meal)
        db.commit()
        db.refresh(meal)
        return {"status": "success", "meal_id": meal.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/meals/edit")
async def edit_meal(request: Request, db: Session = Depends(get_db),
                   meal_id: int = Form(...), name: str = Form(...), 
                   meal_type: str = Form(...)):
    
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            return {"status": "error", "message": "Meal not found"}
        
        meal.name = name
        meal.meal_type = meal_type
        
        db.commit()
        return {"status": "success", "message": "Meal updated successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.get("/meals/{meal_id}/foods")
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

@app.post("/meals/{meal_id}/add_food")
async def add_food_to_meal(meal_id: int, food_id: int = Form(...), 
                          quantity: float = Form(...), db: Session = Depends(get_db)):
    
    try:
        meal_food = MealFood(meal_id=meal_id, food_id=food_id, quantity=quantity)
        db.add(meal_food)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.delete("/meals/remove_food/{meal_food_id}")
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

@app.post("/meals/delete")
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

# Plan tab
@app.get("/plan", response_class=HTMLResponse)
async def plan_page(request: Request, person: str = "Person A", week_start_date: str = None, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    # If no week_start_date provided, use current week starting from Monday
    if not week_start_date:
        today = datetime.now().date()
        # Find Monday of current week
        week_start_date = (today - timedelta(days=today.weekday())).isoformat()
    else:
        week_start_date = datetime.fromisoformat(week_start_date).date()

    # Generate 7 days starting from Monday
    days = []
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for i in range(7):
        day_date = week_start_date + timedelta(days=i)
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
    prev_week = (week_start_date - timedelta(days=7)).isoformat()
    next_week = (week_start_date + timedelta(days=7)).isoformat()

    return templates.TemplateResponse("plan.html", {
        "request": request, "person": person, "days": days,
        "plans": plans, "daily_totals": daily_totals, "meals": meals,
        "week_start_date": week_start_date.isoformat(),
        "prev_week": prev_week, "next_week": next_week,
        "week_range": f"{days[0]['display']} - {days[-1]['display']}, {week_start_date.year}"
    })

@app.post("/plan/add")
async def add_to_plan(request: Request, person: str = Form(...),
                      plan_date: str = Form(...), meal_id: int = Form(...),
                      db: Session = Depends(get_db)):

    try:
        from datetime import datetime
        plan_date_obj = datetime.fromisoformat(plan_date).date()
        plan = Plan(person=person, date=plan_date_obj, meal_id=meal_id)
        db.add(plan)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.get("/plan/{person}/{date}")
async def get_day_plan(person: str, date: str, db: Session = Depends(get_db)):
    """Get all meals for a specific date"""
    try:
        from datetime import datetime
        plan_date = datetime.fromisoformat(date).date()
        plans = db.query(Plan).filter(Plan.person == person, Plan.date == plan_date).all()
        result = []
        for plan in plans:
            result.append({
                "id": plan.id,
                "meal_id": plan.meal_id,
                "meal_name": plan.meal.name,
                "meal_type": plan.meal.meal_type
            })
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/plan/update_day")
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
            plan = Plan(person=person, date=plan_date, meal_id=meal_id)
            db.add(plan)

        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.delete("/plan/{plan_id}")
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

@app.get("/detailed", response_class=HTMLResponse)
async def detailed(request: Request):
    return templates.TemplateResponse("detailed.html", {"request": request, "title": "Detailed"})

@app.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request, db: Session = Depends(get_db)):
    templates_list = db.query(Template).all()
    meals = db.query(Meal).all()

    # Convert templates to dictionaries for JSON serialization
    templates_data = []
    for template in templates_list:
        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template.id).all()
        template_dict = {
            "id": template.id,
            "name": template.name,
            "template_meals": []
        }
        for tm in template_meals:
            template_dict["template_meals"].append({
                "meal_time": tm.meal_time,
                "meal_id": tm.meal_id,
                "meal": {
                    "id": tm.meal.id,
                    "name": tm.meal.name,
                    "meal_type": tm.meal.meal_type
                }
            })
        templates_data.append(template_dict)

    return templates.TemplateResponse("plans.html", {
        "request": request,
        "title": "Templates",
        "templates": templates_data,
        "meals": meals
    })

@app.post("/templates/create")
async def create_template(request: Request, name: str = Form(...),
                         meal_assignments: str = Form(...), db: Session = Depends(get_db)):
    """Create a new template with meal assignments"""
    try:
        # Create template
        template = Template(name=name)
        db.add(template)
        db.flush()  # Get template ID

        # Parse meal assignments (format: "meal_time:meal_id,meal_time:meal_id,...")
        if meal_assignments:
            assignments = meal_assignments.split(',')
            for assignment in assignments:
                if ':' in assignment:
                    meal_time, meal_id = assignment.split(':', 1)
                    if meal_id.strip():  # Only add if meal_id is not empty
                        template_meal = TemplateMeal(
                            template_id=template.id,
                            meal_id=int(meal_id.strip()),
                            meal_time=meal_time.strip()
                        )
                        db.add(template_meal)

        db.commit()
        return {"status": "success", "template_id": template.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.get("/templates/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get template details with meal assignments"""
    try:
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {"status": "error", "message": "Template not found"}

        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).all()
        result = {
            "id": template.id,
            "name": template.name,
            "meals": []
        }

        for tm in template_meals:
            result["meals"].append({
                "meal_time": tm.meal_time,
                "meal_id": tm.meal_id,
                "meal_name": tm.meal.name
            })

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/templates/{template_id}/use")
async def use_template(template_id: int, person: str = Form(...),
                       start_date: str = Form(...), db: Session = Depends(get_db)):
    """Copy template meals to a person's plan starting from a specific date"""
    try:
        from datetime import datetime
        start_date_obj = datetime.fromisoformat(start_date).date()

        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).all()

        print(f"DEBUG: Using template {template_id} for {person} on {start_date}")
        print(f"DEBUG: Found {len(template_meals)} template meals")

        # Check if any meals already exist for this date
        existing_plans = db.query(Plan).filter(Plan.person == person, Plan.date == start_date_obj).count()
        if existing_plans > 0:
            return {"status": "confirm_overwrite", "message": f"There are already {existing_plans} meals planned for this date. Do you want to overwrite them?"}

        # Copy all template meals to the specified date
        for tm in template_meals:
            print(f"DEBUG: Adding meal {tm.meal_id} ({tm.meal.name}) for {tm.meal_time}")
            plan = Plan(person=person, date=start_date_obj, meal_id=tm.meal_id)
            db.add(plan)

        db.commit()
        print(f"DEBUG: Successfully applied template")
        return {"status": "success"}
    except Exception as e:
        print(f"DEBUG: Error applying template: {str(e)}")
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.delete("/templates/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template and its meal assignments"""
    try:
        # Delete template meals first
        db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).delete()
        # Delete template
        template = db.query(Template).filter(Template.id == template_id).first()
        if template:
            db.delete(template)
            db.commit()
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Template not found"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)