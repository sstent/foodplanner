
print("DEBUG: main.py started")

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
import logging
from alembic.config import Config
from alembic import command
from apscheduler.schedulers.background import BackgroundScheduler
import shutil
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database setup - Use SQLite for easier setup
# Use environment variables if set, otherwise use defaults
# Use current directory for database
DATABASE_PATH = os.getenv('DATABASE_PATH', '.')
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_PATH}/meal_planner.db')

logging.info(f"Database URL: {DATABASE_URL}")
logging.info(f"Absolute database path: {os.path.abspath(DATABASE_PATH)}")
logging.info(f"Absolute database path: {os.path.abspath(DATABASE_PATH)}")

# Ensure the database directory exists
logging.info(f"Creating database directory at: {DATABASE_PATH}")
try:
    os.makedirs(DATABASE_PATH, exist_ok=True)
    logging.info(f"Database directory created successfully")
except Exception as e:
    logging.error(f"Failed to create database directory: {e}")
    raise

# For production, use PostgreSQL: DATABASE_URL = "postgresql://username:password@localhost/meal_planner"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize FastAPI app
app = FastAPI(title="Meal Planner")
templates = Jinja2Templates(directory="templates")

# Get the port from environment variable or default to 8999
PORT = int(os.getenv("PORT", 8999))

# This will be called if running directly with Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    
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

    class Config:
        from_attributes = True

class PlanExport(BaseModel):
    id: int
    person: str
    date: date
    meal_id: int
    meal_time: str

    class Config:
        from_attributes = True

class TemplateMealExport(BaseModel):
    meal_id: int
    meal_time: str

class TemplateExport(BaseModel):
    id: int
    name: str
    template_meals: List[TemplateMealExport]

    class Config:
        from_attributes = True

class WeeklyMenuDayExport(BaseModel):
    day_of_week: int
    template_id: int

class WeeklyMenuExport(BaseModel):
    id: int
    name: str
    weekly_menu_days: List[WeeklyMenuDayExport]

    class Config:
        from_attributes = True

class TrackedMealExport(BaseModel):
    meal_id: int
    meal_time: str
    quantity: float

class TrackedDayExport(BaseModel):
    id: int
    person: str
    date: date
    is_modified: bool
    tracked_meals: List[TrackedMealExport]

    class Config:
        from_attributes = True

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

def backup_database(source_db_path, backup_db_path):
    """Backs up an SQLite database using the online backup API."""
    try:
        source_conn = sqlite3.connect(source_db_path)
        dest_conn = sqlite3.connect(backup_db_path)

        with dest_conn:
            source_conn.backup(dest_conn)

        logging.info(f"Backup of '{source_db_path}' created successfully at '{backup_db_path}'")

    except sqlite3.Error as e:
        logging.error(f"SQLite error during backup: {e}")
    finally:
        if 'source_conn' in locals() and source_conn:
            source_conn.close()
        if 'dest_conn' in locals() and dest_conn:
            dest_conn.close()

def scheduled_backup():
    """Create a backup of the database."""
    db_path = DATABASE_URL.split("///")[1]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join("./backups", f"meal_planner_{timestamp}.db")
    backup_database(db_path, backup_path)

@app.on_event("startup")
def startup_event():
    run_migrations()

    # Schedule the backup job - temporarily disabled for debugging
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(scheduled_backup, 'cron', hour=0)
    # scheduler.start()
    # logging.info("Scheduled backup job started.")
    logging.info("Startup completed - scheduler temporarily disabled")

def test_sqlite_connection(db_path):
    """Test if we can create and write to SQLite database file"""
    try:
        import sqlite3
        import stat
        import os
        
        # Log directory permissions
        db_dir = os.path.dirname(db_path)
        if os.path.exists(db_dir):
            dir_stat = os.stat(db_dir)
            dir_perm = stat.filemode(dir_stat.st_mode)
            dir_uid = dir_stat.st_uid
            dir_gid = dir_stat.st_gid
            logging.info(f"Database directory permissions: {dir_perm}, UID:{dir_uid}, GID:{dir_gid}")
            
            # Test write access
            test_file = os.path.join(db_dir, "write_test.txt")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                logging.info("Write test to directory succeeded")
            except Exception as e:
                logging.error(f"Write test to directory failed: {e}")
        else:
            logging.warning(f"Database directory does not exist: {db_dir}")
        
        # Test SQLite operations
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        cursor.execute("DROP TABLE test")
        conn.close()
        
        # Log file permissions
        if os.path.exists(db_path):
            file_stat = os.stat(db_path)
            file_perm = stat.filemode(file_stat.st_mode)
            file_uid = file_stat.st_uid
            file_gid = file_stat.st_gid
            logging.info(f"Database file permissions: {file_perm}, UID:{file_uid}, GID:{file_gid}")
        return True
    except Exception as e:
        logging.error(f"SQLite connection test failed: {e}", exc_info=True)
        return False

def run_migrations():
    logging.info("Running database migrations...")
    try:
        # Extract database path from URL
        db_path = DATABASE_URL.split("///")[1]
        logging.info(f"Database path: {db_path}")
        
        # Create directory if needed
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            logging.info(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        # Test SQLite connection
        if not test_sqlite_connection(db_path):
            raise Exception("SQLite connection test failed")
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logging.info("Database migrations completed successfully.")
    except Exception as e:
        logging.error(f"Failed to run database migrations: {e}", exc_info=True)
        raise

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

# Admin Section
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})

@app.get("/admin/imports", response_class=HTMLResponse)
async def admin_imports_page(request: Request):
    return templates.TemplateResponse("admin/imports.html", {"request": request})

@app.get("/admin/backups", response_class=HTMLResponse)
async def admin_backups_page(request: Request):
    BACKUP_DIR = "./backups"
    backups = []
    if os.path.exists(BACKUP_DIR):
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
            reverse=True
        )
    return templates.TemplateResponse("admin/backups.html", {"request": request, "backups": backups})

@app.post("/admin/backups/create", response_class=HTMLResponse)
async def create_backup(request: Request, db: Session = Depends(get_db)):
    db_path = DATABASE_URL.split("///")[1]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join("./backups", f"meal_planner_{timestamp}.db")
    backup_database(db_path, backup_path)

    # Redirect back to the backups page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/backups", status_code=303)

@app.post("/admin/backups/restore", response_class=HTMLResponse)
async def restore_backup(request: Request, backup_file: str = Form(...)):
    import shutil

    BACKUP_DIR = "./backups"
    db_path = DATABASE_URL.split("///")[1]
    backup_path = os.path.join(BACKUP_DIR, backup_file)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup file not found.")

    try:
        # It's a good practice to close the current connection before overwriting the database
        engine.dispose()
        shutil.copyfile(backup_path, db_path)
        logging.info(f"Database restored from {backup_path}")
    except Exception as e:
        logging.error(f"Failed to restore backup: {e}")
        # You might want to add some user-facing error feedback here
        pass

    # Redirect back to the backups page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/backups", status_code=303)

@app.get("/export/all", response_model=AllData)
async def export_all_data(db: Session = Depends(get_db)):
    """Export all data from the database as a single JSON file."""
    foods = db.query(Food).all()
    meals = db.query(Meal).all()
    plans = db.query(Plan).all()
    templates = db.query(Template).all()
    weekly_menus = db.query(WeeklyMenu).all()
    tracked_days = db.query(TrackedDay).all()

    # Manual serialization to handle nested relationships
    
    # Meals with MealFoods
    meals_export = []
    for meal in meals:
        meal_foods_export = [
            MealFoodExport(food_id=mf.food_id, quantity=mf.quantity)
            for mf in meal.meal_foods
        ]
        meals_export.append(
            MealExport(
                id=meal.id,
                name=meal.name,
                meal_type=meal.meal_type,
                meal_time=meal.meal_time,
                meal_foods=meal_foods_export,
            )
        )

    # Templates with TemplateMeals
    templates_export = []
    for template in templates:
        template_meals_export = [
            TemplateMealExport(meal_id=tm.meal_id, meal_time=tm.meal_time)
            for tm in template.template_meals
        ]
        templates_export.append(
            TemplateExport(
                id=template.id,
                name=template.name,
                template_meals=template_meals_export,
            )
        )

    # Weekly Menus with WeeklyMenuDays
    weekly_menus_export = []
    for weekly_menu in weekly_menus:
        weekly_menu_days_export = [
            WeeklyMenuDayExport(
                day_of_week=wmd.day_of_week, template_id=wmd.template_id
            )
            for wmd in weekly_menu.weekly_menu_days
        ]
        weekly_menus_export.append(
            WeeklyMenuExport(
                id=weekly_menu.id,
                name=weekly_menu.name,
                weekly_menu_days=weekly_menu_days_export,
            )
        )

    # Tracked Days with TrackedMeals
    tracked_days_export = []
    for tracked_day in tracked_days:
        tracked_meals_export = [
            TrackedMealExport(
                meal_id=tm.meal_id,
                meal_time=tm.meal_time,
                quantity=tm.quantity,
            )
            for tm in tracked_day.tracked_meals
        ]
        tracked_days_export.append(
            TrackedDayExport(
                id=tracked_day.id,
                person=tracked_day.person,
                date=tracked_day.date,
                is_modified=tracked_day.is_modified,
                tracked_meals=tracked_meals_export,
            )
        )

    return AllData(
        foods=[FoodExport.from_orm(f) for f in foods],
        meals=meals_export,
        plans=[PlanExport.from_orm(p) for p in plans],
        templates=templates_export,
        weekly_menus=weekly_menus_export,
        tracked_days=tracked_days_export,
    )

@app.post("/import/all")
async def import_all_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import all data from a JSON file, overwriting existing data."""
    try:
        contents = await file.read()
        data = AllData.parse_raw(contents)

        # Validate data before import
        validate_import_data(data)

        # 1. Delete existing data in the correct order
        db.query(TrackedMeal).delete()
        db.query(TrackedDay).delete()
        db.query(WeeklyMenuDay).delete()
        db.query(WeeklyMenu).delete()
        db.query(Plan).delete()
        db.query(TemplateMeal).delete()
        db.query(Template).delete()
        db.query(MealFood).delete()
        db.query(Meal).delete()
        db.query(Food).delete()
        db.commit()

        # 2. Insert new data in the correct order
        # Foods
        for food_data in data.foods:
            db.add(Food(**food_data.dict()))
        db.commit()

        # Meals
        for meal_data in data.meals:
            meal = Meal(
                id=meal_data.id,
                name=meal_data.name,
                meal_type=meal_data.meal_type,
                meal_time=meal_data.meal_time,
            )
            db.add(meal)
            db.flush()
            for mf_data in meal_data.meal_foods:
                db.add(
                    MealFood(
                        meal_id=meal.id,
                        food_id=mf_data.food_id,
                        quantity=mf_data.quantity,
                    )
                )
        db.commit()

        # Templates
        for template_data in data.templates:
            template = Template(id=template_data.id, name=template_data.name)
            db.add(template)
            db.flush()
            for tm_data in template_data.template_meals:
                db.add(
                    TemplateMeal(
                        template_id=template.id,
                        meal_id=tm_data.meal_id,
                        meal_time=tm_data.meal_time,
                    )
                )
        db.commit()
        
        # Plans
        for plan_data in data.plans:
            db.add(Plan(**plan_data.dict()))
        db.commit()

        # Weekly Menus
        for weekly_menu_data in data.weekly_menus:
            weekly_menu = WeeklyMenu(
                id=weekly_menu_data.id, name=weekly_menu_data.name
            )
            db.add(weekly_menu)
            db.flush()
            for wmd_data in weekly_menu_data.weekly_menu_days:
                db.add(
                    WeeklyMenuDay(
                        weekly_menu_id=weekly_menu.id,
                        day_of_week=wmd_data.day_of_week,
                        template_id=wmd_data.template_id,
                    )
                )
        db.commit()

        # Tracked Days
        for tracked_day_data in data.tracked_days:
            tracked_day = TrackedDay(
                id=tracked_day_data.id,
                person=tracked_day_data.person,
                date=tracked_day_data.date,
                is_modified=tracked_day_data.is_modified,
            )
            db.add(tracked_day)
            db.flush()
            for tm_data in tracked_day_data.tracked_meals:
                db.add(
                    TrackedMeal(
                        tracked_day_id=tracked_day.id,
                        meal_id=tm_data.meal_id,
                        meal_time=tm_data.meal_time,
                        quantity=tm_data.quantity,
                    )
                )
        db.commit()

        return {"status": "success", "message": "All data imported successfully."}

    except Exception as e:
        db.rollback()
        logging.error(f"Failed to import data: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to import data: {e}")

def validate_import_data(data: AllData):
    """Validate the integrity of the imported data."""
    food_ids = {f.id for f in data.foods}
    meal_ids = {m.id for m in data.meals}
    template_ids = {t.id for t in data.templates}

    # Validate Meals
    for meal in data.meals:
        for meal_food in meal.meal_foods:
            if meal_food.food_id not in food_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid meal food: food_id {meal_food.food_id} not found.",
                )

    # Validate Plans
    for plan in data.plans:
        if plan.meal_id not in meal_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan: meal_id {plan.meal_id} not found.",
            )

    # Validate Templates
    for template in data.templates:
        for template_meal in template.template_meals:
            if template_meal.meal_id not in meal_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid template meal: meal_id {template_meal.meal_id} not found.",
                )

    # Validate Weekly Menus
    for weekly_menu in data.weekly_menus:
        for day in weekly_menu.weekly_menu_days:
            if day.template_id not in template_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid weekly menu day: template_id {day.template_id} not found.",
                )

    # Validate Tracked Days
    for tracked_day in data.tracked_days:
        for tracked_meal in tracked_day.tracked_meals:
            if tracked_meal.meal_id not in meal_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tracked meal: meal_id {tracked_meal.meal_id} not found.",
                )

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

        return templates