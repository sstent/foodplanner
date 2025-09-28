# Meal Planner FastAPI Application
# Run with: uvicorn main:app --reload

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Date, Boolean
from sqlalchemy import or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import os
import csv
import requests
from fastapi import File, UploadFile

# Database setup - Use SQLite for easier setup
DATABASE_URL = f"sqlite:///{os.getenv('DATABASE_PATH', './data')}/meal_planner.db"
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
    source = Column(String, default="manual")  # manual, csv, openfoodfacts
    brand = Column(String, default="") # Brand name for the food

class Meal(Base):
    __tablename__ = "meals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    meal_type = Column(String)  # breakfast, lunch, dinner, snack, custom
    meal_time = Column(String, default="Breakfast") # Breakfast, Lunch, Dinner, Snack 1, Snack 2, Beverage 1, Beverage 2
    
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
    person = Column(String, index=True)  # Sarah or Stuart
    date = Column(Date, index=True)  # Store actual calendar dates
    meal_id = Column(Integer, ForeignKey("meals.id"))
    meal_time = Column(String)  # Breakfast, Lunch, Dinner, Snack 1, Snack 2, Beverage 1, Beverage 2

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

class WeeklyMenu(Base):
    __tablename__ = "weekly_menus"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # Relationship to weekly menu days
    weekly_menu_days = relationship("WeeklyMenuDay", back_populates="weekly_menu")

class WeeklyMenuDay(Base):
    __tablename__ = "weekly_menu_days"

    id = Column(Integer, primary_key=True, index=True)
    weekly_menu_id = Column(Integer, ForeignKey("weekly_menus.id"))
    day_of_week = Column(Integer)  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    template_id = Column(Integer, ForeignKey("templates.id"))

    weekly_menu = relationship("WeeklyMenu", back_populates="weekly_menu_days")
    template = relationship("Template")

class TrackedDay(Base):
    """Represents a day being tracked (separate from planned days)"""
    __tablename__ = "tracked_days"

    id = Column(Integer, primary_key=True, index=True)
    person = Column(String, index=True)  # Sarah or Stuart
    date = Column(Date, index=True)  # Date being tracked
    is_modified = Column(Boolean, default=False)  # Whether this day has been modified from original plan

    # Relationship to tracked meals
    tracked_meals = relationship("TrackedMeal", back_populates="tracked_day")

class TrackedMeal(Base):
    """Represents a meal tracked for a specific day"""
    __tablename__ = "tracked_meals"

    id = Column(Integer, primary_key=True, index=True)
    tracked_day_id = Column(Integer, ForeignKey("tracked_days.id"))
    meal_id = Column(Integer, ForeignKey("meals.id"))
    meal_time = Column(String)  # Breakfast, Lunch, Dinner, Snack 1, Snack 2, Beverage 1, Beverage 2
    quantity = Column(Float, default=1.0)  # Quantity multiplier (e.g., 1.5 for 1.5 servings)

    tracked_day = relationship("TrackedDay", back_populates="tracked_meals")
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
    source: str = "manual"
    brand: Optional[str] = ""

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
    source: str
    brand: str

    class Config:
        from_attributes = True

class MealCreate(BaseModel):
    name: str
    meal_type: str
    meal_time: str
    foods: List[dict]  # [{"food_id": 1, "quantity": 1.5}]

class TrackedDayCreate(BaseModel):
    person: str
    date: str  # ISO date string

class TrackedMealCreate(BaseModel):
    meal_id: int
    meal_time: str
    quantity: float = 1.0

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
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/tracker", status_code=302)

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

@app.post("/foods/add")
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

@app.post("/foods/edit")
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

@app.get("/foods/search_openfoodfacts")
async def search_openfoodfacts(query: str, limit: int = 10):
    """Search OpenFoodFacts database for foods using the official SDK"""
    try:
        from openfoodfacts import API, APIVersion, Country, Environment, Flavor

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
                    import re
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

    except ImportError:
        return {"status": "error", "message": "OpenFoodFacts module not installed. Please install with: pip install openfoodfacts"}
    except Exception as e:
        return {"status": "error", "message": f"OpenFoodFacts search failed: {str(e)}"}

@app.get("/foods/get_openfoodfacts_product/{barcode}")
async def get_openfoodfacts_product(barcode: str):
    """Get a specific product by barcode from OpenFoodFacts"""
    try:
        from openfoodfacts import API, APIVersion, Country, Environment, Flavor

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
            import re
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

    except ImportError:
        return {"status": "error", "message": "OpenFoodFacts module not installed"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get product: {str(e)}"}

@app.get("/foods/openfoodfacts_by_category")
async def get_openfoodfacts_by_category(category: str, limit: int = 20):
    """Get products from OpenFoodFacts filtered by category"""
    try:
        from openfoodfacts import API, APIVersion, Country, Environment, Flavor

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

    except ImportError:
        return {"status": "error", "message": "OpenFoodFacts module not installed"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get category products: {str(e)}"}

@app.post("/foods/add_openfoodfacts")
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
                  name: str = Form(...), meal_type: str = Form(...),
                  meal_time: str = Form(...)):
    
    try:
        meal = Meal(name=name, meal_type=meal_type, meal_time=meal_time)
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
                   meal_type: str = Form(...), meal_time: str = Form(...)):
    
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            return {"status": "error", "message": "Meal not found"}
        
        meal.name = name
        meal.meal_type = meal_type
        meal.meal_time = meal_time # Update meal_time
        
        db.commit()
        return {"status": "success", "message": "Meal updated successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.get("/meals/{meal_id}")
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

@app.post("/plan/add")
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

@app.get("/plan/{person}/{date}")
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
            # For now, assign a default meal_time. This will be refined later.
            plan = Plan(person=person, date=plan_date, meal_id=meal_id, meal_time="Breakfast")
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
async def detailed(request: Request, person: str = "Sarah", plan_date: str = None, template_id: int = None, db: Session = Depends(get_db)):
    from datetime import datetime

    if template_id:
        # Show template details
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return templates.TemplateResponse("detailed.html", {
                "request": request, "title": "Template Not Found",
                "error": "Template not found"
            })

        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).all()

        # Calculate template nutrition
        template_nutrition = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0}

        meal_details = []
        for tm in template_meals:
            meal_nutrition = calculate_meal_nutrition(tm.meal, db)
            meal_details.append({
                'plan': {'meal': tm.meal},
                'nutrition': meal_nutrition,
                'foods': []  # Template view doesn't show individual foods
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
            template_nutrition['net_carbs'] = template_nutrition['carbs'] - template_nutrition['fiber']

        return templates.TemplateResponse("detailed.html", {
            "request": request, "title": f"Template: {template.name}",
            "person": person, "meal_details": meal_details, "day_totals": template_nutrition,
            "selected_day": template.name, "view_mode": "template"
        })

    elif plan_date:
        # Show planned day details
        plan_date_obj = datetime.fromisoformat(plan_date).date()
        plans = db.query(Plan).filter(Plan.person == person, Plan.date == plan_date_obj).all()

        meal_details = []
        day_totals = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0}

        for plan in plans:
            meal_nutrition = calculate_meal_nutrition(plan.meal, db)

            # Get meal foods for detailed breakdown
            meal_foods = []
            for meal_food in plan.meal.meal_foods:
                meal_foods.append({
                    'food': meal_food.food,
                    'quantity': meal_food.quantity
                })

            meal_details.append({
                'plan': plan,
                'nutrition': meal_nutrition,
                'foods': meal_foods
            })

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

        selected_day = plan_date_obj.strftime('%A, %B %d, %Y')

        return templates.TemplateResponse("detailed.html", {
            "request": request, "title": f"Detailed View - {selected_day}",
            "person": person, "meal_details": meal_details, "day_totals": day_totals,
            "selected_day": selected_day, "view_mode": "day"
        })

    else:
        # Default view - show current week
        templates_list = db.query(Template).all()
        context = {
            "request": request, "title": "Detailed View",
            "person": person, "view_mode": "select", "templates": templates_list,
            "meal_details": [],  # Empty list for default view
            "day_totals": {  # Default empty nutrition totals
                'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
                'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0,
                'protein_pct': 0, 'carbs_pct': 0, 'fat_pct': 0, 'net_carbs': 0
            },
            "selected_day": "Select a date or template above"
        }
        return templates.TemplateResponse("detailed.html", context)

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
            plan = Plan(person=person, date=start_date_obj, meal_id=tm.meal_id, meal_time=tm.meal_time) # Use meal_time from template
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

@app.post("/templates/edit")
async def edit_template(template_id: int = Form(...), name: str = Form(...),
                       meal_assignments: str = Form(...), db: Session = Depends(get_db)):
    """Edit an existing template with new name and meal assignments"""
    try:
        # Get existing template
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {"status": "error", "message": "Template not found"}

        # Update template name
        template.name = name

        # Delete existing template meals
        db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).delete()

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

@app.post("/templates/create_from_template")
async def create_template_from_existing(source_template_id: int = Form(...),
                                       new_name: str = Form(...), db: Session = Depends(get_db)):
    """Create a new template by copying an existing template's meal assignments"""
    try:
        # Get source template
        source_template = db.query(Template).filter(Template.id == source_template_id).first()
        if not source_template:
            return {"status": "error", "message": "Source template not found"}

        # Create new template
        new_template = Template(name=new_name)
        db.add(new_template)
        db.flush()  # Get new template ID

        # Copy template meals from source
        source_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == source_template_id).all()
        for source_meal in source_meals:
            new_template_meal = TemplateMeal(
                template_id=new_template.id,
                meal_id=source_meal.meal_id,
                meal_time=source_meal.meal_time
            )
            db.add(new_template_meal)

        db.commit()
        return {"status": "success", "template_id": new_template.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/templates/upload")
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

# Weekly Menu tab
@app.get("/weeklymenu", response_class=HTMLResponse)
async def weeklymenu_page(request: Request, db: Session = Depends(get_db)):
    weekly_menus = db.query(WeeklyMenu).all()
    templates_list = db.query(Template).all()

    # Convert weekly menus to dictionaries for JSON serialization
    weekly_menus_data = []
    for weekly_menu in weekly_menus:
        weekly_menu_days = db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu.id).all()
        weekly_menu_dict = {
            "id": weekly_menu.id,
            "name": weekly_menu.name,
            "weekly_menu_days": []
        }
        for wmd in weekly_menu_days:
            weekly_menu_dict["weekly_menu_days"].append({
                "day_of_week": wmd.day_of_week,
                "template_id": wmd.template_id,
                "template": {
                    "id": wmd.template.id,
                    "name": wmd.template.name
                }
            })
        weekly_menus_data.append(weekly_menu_dict)

    return templates.TemplateResponse("weeklymenu.html", {
        "request": request,
        "weekly_menus": weekly_menus_data,
        "templates": templates_list
    })

@app.get("/weeklymenu/{weekly_menu_id}")
async def get_weekly_menu(weekly_menu_id: int, db: Session = Depends(get_db)):
    """Get details for a specific weekly menu for editing"""
    try:
        weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == weekly_menu_id).first()
        if not weekly_menu:
            return {"status": "error", "message": "Weekly menu not found"}

        weekly_menu_days = db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu_id).all()

        # Create a dictionary mapping day_of_week to template_id
        template_assignments = {}
        for wmd in weekly_menu_days:
            template_assignments[wmd.day_of_week] = wmd.template_id

        return {
            "status": "success",
            "id": weekly_menu.id,
            "name": weekly_menu.name,
            "template_assignments": template_assignments
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/weeklymenu/create")
async def create_weekly_menu(request: Request, name: str = Form(...),
                            template_assignments: str = Form(...), db: Session = Depends(get_db)):
    """Create a new weekly menu with template assignments"""
    try:
        # Create weekly menu
        weekly_menu = WeeklyMenu(name=name)
        db.add(weekly_menu)
        db.flush()  # Get weekly menu ID

        # Parse template assignments (format: "day_of_week:template_id,day_of_week:template_id,...")
        if template_assignments:
            assignments = template_assignments.split(',')
            for assignment in assignments:
                if ':' in assignment:
                    day_of_week, template_id = assignment.split(':', 1)
                    if template_id.strip():  # Only add if template_id is not empty
                        weekly_menu_day = WeeklyMenuDay(
                            weekly_menu_id=weekly_menu.id,
                            day_of_week=int(day_of_week.strip()),
                            template_id=int(template_id.strip())
                        )
                        db.add(weekly_menu_day)

        db.commit()
        return {"status": "success", "weekly_menu_id": weekly_menu.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/weeklymenu/edit")
async def edit_weekly_menu(request: Request, weekly_menu_id: int = Form(...),
                          name: str = Form(...), monday: str = Form(""),
                          tuesday: str = Form(""), wednesday: str = Form(""),
                          thursday: str = Form(""), friday: str = Form(""),
                          saturday: str = Form(""), sunday: str = Form(""),
                          db: Session = Depends(get_db)):
    """Edit an existing weekly menu with new name and template assignments"""
    try:
        # Get existing weekly menu
        weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == weekly_menu_id).first()
        if not weekly_menu:
            return {"status": "error", "message": "Weekly menu not found"}

        # Update name
        weekly_menu.name = name

        # Delete existing weekly menu days
        db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu_id).delete()

        # Create new template assignments
        day_assignments = {
            0: monday,    # Monday
            1: tuesday,   # Tuesday
            2: wednesday, # Wednesday
            3: thursday,  # Thursday
            4: friday,    # Friday
            5: saturday,  # Saturday
            6: sunday     # Sunday
        }

        for day_of_week, template_id in day_assignments.items():
            if template_id and template_id.strip():
                weekly_menu_day = WeeklyMenuDay(
                    weekly_menu_id=weekly_menu.id,
                    day_of_week=day_of_week,
                    template_id=int(template_id.strip())
                )
                db.add(weekly_menu_day)

        db.commit()
        return {"status": "success", "weekly_menu_id": weekly_menu.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/weeklymenu/{weekly_menu_id}/apply")
async def apply_weekly_menu(weekly_menu_id: int, person: str = Form(...),
                          week_start_date: str = Form(...), db: Session = Depends(get_db)):
    """Apply a weekly menu to a person's plan for a specific week"""
    try:
        from datetime import datetime, timedelta
        week_start_date_obj = datetime.fromisoformat(week_start_date).date()

        weekly_menu_days = db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu_id).all()

        # Check if any meals already exist for this week
        existing_plans_count = 0
        for i in range(7):
            day_date = week_start_date_obj + timedelta(days=i)
            existing_plans_count += db.query(Plan).filter(Plan.person == person, Plan.date == day_date).count()

        if existing_plans_count > 0:
            return {"status": "confirm_overwrite", "message": f"There are already {existing_plans_count} meals planned for this week. Do you want to overwrite them?"}

        # Apply weekly menu to each day
        for weekly_menu_day in weekly_menu_days:
            day_date = week_start_date_obj + timedelta(days=weekly_menu_day.day_of_week)

            # Get template meals for this day
            template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == weekly_menu_day.template_id).all()

            # Add template meals to plan
            for tm in template_meals:
                plan = Plan(person=person, date=day_date, meal_id=tm.meal_id, meal_time=tm.meal_time)
                db.add(plan)

        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.delete("/weeklymenu/{weekly_menu_id}")
async def delete_weekly_menu(weekly_menu_id: int, db: Session = Depends(get_db)):
    """Delete a weekly menu and its day assignments"""
    try:
        # Delete weekly menu days first
        db.query(WeeklyMenuDay).filter(WeeklyMenuDay.weekly_menu_id == weekly_menu_id).delete()
        # Delete weekly menu
        weekly_menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == weekly_menu_id).first()
        if weekly_menu:
            db.delete(weekly_menu)
            db.commit()
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Weekly menu not found"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

# Tracker tab
@app.get("/tracker", response_class=HTMLResponse)
async def tracker_page(request: Request, person: str = "Sarah", date: str = None, db: Session = Depends(get_db)):
    from datetime import datetime, date as date_type

    # If no date provided, use today
    if not date:
        current_date = date_type.today()
    else:
        current_date = datetime.fromisoformat(date).date()

    # Get or create tracked day for this date
    tracked_day = db.query(TrackedDay).filter(
        TrackedDay.person == person,
        TrackedDay.date == current_date
    ).first()

    if not tracked_day:
        tracked_day = TrackedDay(person=person, date=current_date)
        db.add(tracked_day)
        db.commit()
        db.refresh(tracked_day)

    # Get tracked meals for this day
    tracked_meals = db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).all()

    # If no tracked meals exist, pre-populate with planned meals
    if not tracked_meals:
        copy_plan_to_tracked(db, person, current_date, tracked_day.id)
        # Re-fetch tracked meals after copying
        tracked_meals = db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).all()

    # Calculate nutrition totals
    day_totals = calculate_tracked_day_nutrition(tracked_meals, db)

    # Get all meals for selection
    meals = db.query(Meal).all()

    # Get existing templates for apply template functionality
    templates_list = db.query(Template).all()

    # Calculate previous and next dates
    prev_date = current_date
    next_date = current_date

    return templates.TemplateResponse("tracker.html", {
        "request": request,
        "person": person,
        "current_date": current_date,
        "tracked_meals": tracked_meals,
        "day_totals": day_totals,
        "meals": meals,
        "templates": templates_list,
        "is_modified": tracked_day.is_modified if tracked_day else False,
        "prev_date": prev_date.isoformat(),
        "next_date": next_date.isoformat()
    })

def copy_plan_to_tracked(db: Session, person: str, date, tracked_day_id: int):
    """Copy planned meals to tracked meals for a specific date"""
    plans = db.query(Plan).filter(Plan.person == person, Plan.date == date).all()

    for plan in plans:
        # Check if this meal is already tracked
        existing_tracked = db.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day_id,
            TrackedMeal.meal_id == plan.meal_id,
            TrackedMeal.meal_time == plan.meal_time
        ).first()

        if not existing_tracked:
            tracked_meal = TrackedMeal(
                tracked_day_id=tracked_day_id,
                meal_id=plan.meal_id,
                meal_time=plan.meal_time,
                quantity=1.0
            )
            db.add(tracked_meal)

    # Mark the tracked day as not modified (it's now matching the plan)
    tracked_day = db.query(TrackedDay).filter(TrackedDay.id == tracked_day_id).first()
    if tracked_day:
        tracked_day.is_modified = False

    db.commit()

def calculate_tracked_day_nutrition(tracked_meals, db: Session):
    """Calculate total nutrition for tracked meals"""
    day_totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }

    for tracked_meal in tracked_meals:
        meal_nutrition = calculate_meal_nutrition(tracked_meal.meal, db)
        for key in day_totals:
            if key in meal_nutrition:
                day_totals[key] += meal_nutrition[key] * tracked_meal.quantity

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

@app.post("/tracker/add_meal")
async def add_tracked_meal(request: Request, person: str = Form(...),
                          date: str = Form(...), meal_id: int = Form(...),
                          meal_time: str = Form(...), quantity: float = Form(1.0),
                          db: Session = Depends(get_db)):
    """Add a meal to the tracker"""
    try:
        from datetime import datetime
        track_date = datetime.fromisoformat(date).date()

        # Get or create tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == track_date
        ).first()

        if not tracked_day:
            tracked_day = TrackedDay(person=person, date=track_date)
            db.add(tracked_day)
            db.commit()
            db.refresh(tracked_day)

        # Add the tracked meal
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=meal_id,
            meal_time=meal_time,
            quantity=quantity
        )
        db.add(tracked_meal)

        # Mark as modified since we're adding a meal
        tracked_day.is_modified = True

        db.commit()

        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.delete("/tracker/remove_meal/{tracked_meal_id}")
async def remove_tracked_meal(tracked_meal_id: int, db: Session = Depends(get_db)):
    """Remove a meal from the tracker"""
    try:
        tracked_meal = db.query(TrackedMeal).filter(TrackedMeal.id == tracked_meal_id).first()
        if not tracked_meal:
            return {"status": "error", "message": "Tracked meal not found"}

        # Mark as modified since we're removing a meal
        tracked_day = db.query(TrackedDay).filter(TrackedDay.id == tracked_meal.tracked_day_id).first()
        if tracked_day:
            tracked_day.is_modified = True

        db.delete(tracked_meal)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/tracker/save_template")
async def save_tracked_day_as_template(request: Request, person: str = Form(...),
                                     date: str = Form(...), template_name: str = Form(...),
                                     db: Session = Depends(get_db)):
    """Save the current tracked day as a template"""
    try:
        from datetime import datetime
        track_date = datetime.fromisoformat(date).date()

        # Get tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == track_date
        ).first()

        if not tracked_day:
            return {"status": "error", "message": "No tracked day found"}

        # Create new template
        template = Template(name=template_name)
        db.add(template)
        db.commit()
        db.refresh(template)

        # Add all tracked meals to template
        tracked_meals = db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).all()
        for tracked_meal in tracked_meals:
            template_meal = TemplateMeal(
                template_id=template.id,
                meal_id=tracked_meal.meal_id,
                meal_time=tracked_meal.meal_time
            )
            db.add(template_meal)

        db.commit()
        return {"status": "success", "template_id": template.id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/tracker/apply_template")
async def apply_template_to_tracked_day(request: Request, person: str = Form(...),
                                       date: str = Form(...), template_id: int = Form(...),
                                       db: Session = Depends(get_db)):
    """Apply a template to the current tracked day"""
    try:
        from datetime import datetime
        track_date = datetime.fromisoformat(date).date()

        # Get or create tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == track_date
        ).first()

        if not tracked_day:
            tracked_day = TrackedDay(person=person, date=track_date)
            db.add(tracked_day)
            db.commit()
            db.refresh(tracked_day)

        # Remove existing tracked meals
        db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).delete()

        # Apply template meals
        template_meals = db.query(TemplateMeal).filter(TemplateMeal.template_id == template_id).all()
        for template_meal in template_meals:
            tracked_meal = TrackedMeal(
                tracked_day_id=tracked_day.id,
                meal_id=template_meal.meal_id,
                meal_time=template_meal.meal_time,
                quantity=1.0
            )
            db.add(tracked_meal)

        # Mark as modified since we're applying a template (not the original plan)
        tracked_day.is_modified = True

        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/tracker/reset_to_plan")
async def reset_to_plan(request: Request, person: str = Form(...),
                       date: str = Form(...), db: Session = Depends(get_db)):
    """Reset the tracked day back to the original plan"""
    try:
        from datetime import datetime
        track_date = datetime.fromisoformat(date).date()

        # Get tracked day
        tracked_day = db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date == track_date
        ).first()

        if not tracked_day:
            return {"status": "error", "message": "No tracked day found"}

        # Remove existing tracked meals
        db.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).delete()

        # Copy plan meals back
        copy_plan_to_tracked(db, person, track_date, tracked_day.id)

        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)