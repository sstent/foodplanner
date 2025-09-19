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
    meal_type = Column(String)  # breakfast, lunch, dinner, snack
    
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
    date = Column(Date, index=True)
    meal_id = Column(Integer, ForeignKey("meals.id"))
    
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
        totals['fiber'] += food.fiber * quantity
        totals['sugar'] += food.sugar * quantity
        totals['sodium'] += food.sodium * quantity
        totals['calcium'] += food.calcium * quantity
    
    # Calculate percentages
    total_cals = totals['calories']
    if total_cals > 0:
        totals['protein_pct'] = round((totals['protein'] * 4 / total_cals) * 100, 1)
        totals['carbs_pct'] = round((totals['carbs'] * 4 / total_cals) * 100, 1)
        totals['fat_pct'] = round((totals['fat'] * 9 / total_cals) * 100, 1)
        totals['net_carbs'] = totals['carbs'] - totals['fiber']
    
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
    
    return day_totals

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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

@app.post("/foods/add")
async def add_food(request: Request, db: Session = Depends(get_db),
                  name: str = Form(...), serving_size: str = Form(...),
                  serving_unit: str = Form(...), calories: float = Form(...),
                  protein: float = Form(...), carbs: float = Form(...),
                  fat: float = Form(...), fiber: float = Form(0),
                  sugar: float = Form(0), sodium: float = Form(0),
                  calcium: float = Form(0)):
    
    food = Food(
        name=name, serving_size=serving_size, serving_unit=serving_unit,
        calories=calories, protein=protein, carbs=carbs, fat=fat,
        fiber=fiber, sugar=sugar, sodium=sodium, calcium=calcium
    )
    db.add(food)
    db.commit()
    return {"status": "success", "message": "Food added successfully"}

# Meals tab
@app.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request, db: Session = Depends(get_db)):
    meals = db.query(Meal).all()
    foods = db.query(Food).all()
    return templates.TemplateResponse("meals.html", 
                                    {"request": request, "meals": meals, "foods": foods})

@app.post("/meals/add")
async def add_meal(request: Request, db: Session = Depends(get_db),
                  name: str = Form(...), meal_type: str = Form(...)):
    
    meal = Meal(name=name, meal_type=meal_type)
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return {"status": "success", "meal_id": meal.id}

@app.post("/meals/{meal_id}/add_food")
async def add_food_to_meal(meal_id: int, food_id: int = Form(...), 
                          quantity: float = Form(...), db: Session = Depends(get_db)):
    
    meal_food = MealFood(meal_id=meal_id, food_id=food_id, quantity=quantity)
    db.add(meal_food)
    db.commit()
    return {"status": "success"}

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
async def plan_page(request: Request, person: str = "Person A", db: Session = Depends(get_db)):
    from datetime import date, timedelta
    
    # Get 2 weeks starting from today
    start_date = date.today()
    dates = [start_date + timedelta(days=i) for i in range(14)]
    
    # Get plans for the person
    plans = {}
    for d in dates:
        day_plans = db.query(Plan).filter(Plan.person == person, Plan.date == d).all()
        plans[d] = day_plans
    
    # Calculate daily totals
    daily_totals = {}
    for d in dates:
        daily_totals[d] = calculate_day_nutrition(plans[d], db)
    
    meals = db.query(Meal).all()
    
    return templates.TemplateResponse("plan.html", {
        "request": request, "person": person, "dates": dates,
        "plans": plans, "daily_totals": daily_totals, "meals": meals
    })

@app.post("/plan/add")
async def add_to_plan(request: Request, person: str = Form(...), 
                     plan_date: str = Form(...), meal_id: int = Form(...),
                     db: Session = Depends(get_db)):
    
    plan = Plan(person=person, date=datetime.strptime(plan_date, "%Y-%m-%d").date(), meal_id=meal_id)
    db.add(plan)
    db.commit()
    return {"status": "success"}

# Detailed planner tab
@app.get("/detailed", response_class=HTMLResponse)
async def detailed_page(request: Request, person: str = "Person A", 
                       plan_date: str = None, db: Session = Depends(get_db)):
    
    if not plan_date:
        plan_date = date.today().strftime("%Y-%m-%d")
    
    selected_date = datetime.strptime(plan_date, "%Y-%m-%d").date()
    
    # Get all plans for the selected day
    plans = db.query(Plan).filter(Plan.person == person, Plan.date == selected_date).all()
    
    # Group by meal type and calculate nutrition
    meal_details = []
    for plan in plans:
        meal_nutrition = calculate_meal_nutrition(plan.meal, db)
        meal_details.append({
            'plan': plan,
            'nutrition': meal_nutrition,
            'foods': plan.meal.meal_foods
        })
    
    # Calculate day totals
    day_totals = calculate_day_nutrition(plans, db)
    
    return templates.TemplateResponse("detailed.html", {
        "request": request, "person": person, "selected_date": selected_date,
        "meal_details": meal_details, "day_totals": day_totals
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)