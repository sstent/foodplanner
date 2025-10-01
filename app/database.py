"""
Database models and session management for the meal planner app
"""
"""
QUANTITY CONVENTION:
All quantity fields in this application represent GRAMS.

- Food.serving_size: base serving size in grams (e.g., 100.0)
- Food nutrition values: per serving_size grams
- MealFood.quantity: grams of this food in the meal (e.g., 150.0)
- TrackedMealFood.quantity: grams of this food as tracked (e.g., 200.0)

To calculate nutrition: multiplier = quantity / serving_size
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Date, Boolean
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, ConfigDict

from typing import List, Optional
from datetime import date, datetime
import os

# Database setup - Use SQLite for easier setup
# Use environment variables if set, otherwise use defaults
# Use current directory for database
DATABASE_PATH = os.getenv('DATABASE_PATH', '/app/data')
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_PATH}/meal_planner.db')

# For production, use PostgreSQL: DATABASE_URL = "postgresql://username:password@localhost/meal_planner"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    serving_size = Column(Float)
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

    tracked_day = relationship("TrackedDay", back_populates="tracked_meals")
    meal = relationship("Meal")
    tracked_foods = relationship("TrackedMealFood", back_populates="tracked_meal", cascade="all, delete-orphan")


class TrackedMealFood(Base):
    """Custom food entries for a tracked meal (overrides or additions)"""
    __tablename__ = "tracked_meal_foods"

    id = Column(Integer, primary_key=True, index=True)
    tracked_meal_id = Column(Integer, ForeignKey("tracked_meals.id"))
    food_id = Column(Integer, ForeignKey("foods.id"))
    quantity = Column(Float, default=1.0)  # Custom quantity for this tracked instance
    is_override = Column(Boolean, default=False)  # True if overriding original meal food, False if addition

    tracked_meal = relationship("TrackedMeal", back_populates="tracked_foods")
    food = relationship("Food")

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

    model_config = ConfigDict(from_attributes=True)

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

class FoodExport(FoodResponse):
    pass

class MealFoodExport(BaseModel):
    food_id: int
    quantity: float

class MealExport(BaseModel):
    id: int
    name: str
    meal_type: str
    meal_time: str
    meal_foods: List[MealFoodExport]

    model_config = ConfigDict(from_attributes=True)

class PlanExport(BaseModel):
    id: int
    person: str
    date: date
    meal_id: int
    meal_time: str

    model_config = ConfigDict(from_attributes=True)

class TemplateMealExport(BaseModel):
    meal_id: int
    meal_time: str

class TemplateExport(BaseModel):
    id: int
    name: str
    template_meals: List[TemplateMealExport]

    model_config = ConfigDict(from_attributes=True)

class TemplateMealDetail(BaseModel):
   meal_id: int
   meal_time: str
   meal_name: str

class TemplateDetail(BaseModel):
   id: int
   name: str
   template_meals: List[TemplateMealDetail]

   model_config = ConfigDict(from_attributes=True)

class WeeklyMenuDayExport(BaseModel):
   day_of_week: int
   template_id: int

class WeeklyMenuDayDetail(BaseModel):
    day_of_week: int
    template_id: int
    template_name: str

class WeeklyMenuExport(BaseModel):
    id: int
    name: str
    weekly_menu_days: List[WeeklyMenuDayExport]

    model_config = ConfigDict(from_attributes=True)

class WeeklyMenuDetail(BaseModel):
    id: int
    name: str
    weekly_menu_days: List[WeeklyMenuDayDetail]

    model_config = ConfigDict(from_attributes=True)

class TrackedMealFoodExport(BaseModel):
    food_id: int
    quantity: float
    is_override: bool


class TrackedMealExport(BaseModel):
    meal_id: int
    meal_time: str
    tracked_foods: List[TrackedMealFoodExport] = []

class TrackedDayExport(BaseModel):
    id: int
    person: str
    date: date
    is_modified: bool
    tracked_meals: List[TrackedMealExport]

    model_config = ConfigDict(from_attributes=True)

class AllData(BaseModel):
    foods: List[FoodExport]
    meals: List[MealExport]
    plans: List[PlanExport]
    templates: List[TemplateExport]
    weekly_menus: List[WeeklyMenuExport]
    tracked_days: List[TrackedDayExport]

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def calculate_meal_nutrition(meal, db: Session):
    """
    Calculate total nutrition for a meal.
    MealFood.quantity is in GRAMS. Multiplier = quantity / food.serving_size (serving_size in grams).
    """
    totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }
    
    for meal_food in meal.meal_foods:
        food = meal_food.food
        try:
            serving_size = float(food.serving_size)
            multiplier = meal_food.quantity / serving_size if serving_size > 0 else 0
        except (ValueError, TypeError):
            multiplier = 0
        
        totals['calories'] += (food.calories or 0) * multiplier
        totals['protein'] += (food.protein or 0) * multiplier
        totals['carbs'] += (food.carbs or 0) * multiplier
        totals['fat'] += (food.fat or 0) * multiplier
        totals['fiber'] += (food.fiber or 0) * multiplier
        totals['sugar'] += (food.sugar or 0) * multiplier
        totals['sodium'] += (food.sodium or 0) * multiplier
        totals['calcium'] += (food.calcium or 0) * multiplier
    
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

def calculate_tracked_meal_nutrition(tracked_meal, db: Session):
    """
    Calculate nutrition for a tracked meal, including custom foods.
    TrackedMealFood.quantity is in GRAMS. Multiplier = quantity / food.serving_size (serving_size in grams).
    Base meal uses calculate_meal_nutrition which handles grams correctly.
    """
    totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }
    
    # Base meal nutrition
    base_nutrition = calculate_meal_nutrition(tracked_meal.meal, db)
    for key in totals:
        if key in base_nutrition:
            totals[key] += base_nutrition[key]
    
    # Add custom tracked foods
    for tracked_food in tracked_meal.tracked_foods:
        food = tracked_food.food
        multiplier = tracked_food.quantity / food.serving_size if food.serving_size and food.serving_size != 0 else 0
        totals['calories'] += (food.calories or 0) * multiplier
        totals['protein'] += (food.protein or 0) * multiplier
        totals['carbs'] += (food.carbs or 0) * multiplier
        totals['fat'] += (food.fat or 0) * multiplier
        totals['fiber'] += (food.fiber or 0) * multiplier
        totals['sugar'] += (food.sugar or 0) * multiplier
        totals['sodium'] += (food.sodium or 0) * multiplier
        totals['calcium'] += (food.calcium or 0) * multiplier
    
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


def calculate_day_nutrition_tracked(tracked_meals, db: Session):
    """Calculate total nutrition for tracked meals"""
    day_totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }
    
    for tracked_meal in tracked_meals:
        meal_nutrition = calculate_tracked_meal_nutrition(tracked_meal, db)
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


def calculate_multiplier_from_grams(food_id: int, grams: float, db: Session) -> float:
    """
    Calculate the multiplier from grams based on the food's serving size.
    Multiplier = grams / serving_size (both in grams).
    Used for nutrition calculations when quantity is provided in grams.
    """
    food = db.query(Food).filter(Food.id == food_id).first()
    if not food:
        raise ValueError(f"Food with ID {food_id} not found.")

    try:
        serving_size_value = float(food.serving_size)
    except ValueError:
        raise ValueError(f"Invalid serving size '{food.serving_size}' for food ID {food_id}. Must be a number.")

    if serving_size_value == 0:
        raise ValueError(f"Serving size for food ID {food_id} cannot be zero.")

    return grams / serving_size_value