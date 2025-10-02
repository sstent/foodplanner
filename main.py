print("DEBUG: main.py started")

# Meal Planner FastAPI Application
# Run with: uvicorn main:app --reload

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Body
from contextlib import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
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
# Import database components from the database module
from app.database import DATABASE_URL, engine, Base, get_db, SessionLocal, Food, Meal, MealFood, Plan, Template, TemplateMeal, WeeklyMenu, WeeklyMenuDay, TrackedMeal, FoodCreate, FoodResponse, calculate_meal_nutrition, calculate_day_nutrition, calculate_day_nutrition_tracked

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("DEBUG: Startup event triggered")
    run_migrations()
    
    # Re-apply logging configuration after Alembic might have altered it
    logging.getLogger().setLevel(logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.INFO)
    logging.info("DEBUG: Logging re-configured to INFO level.")
    
    logging.info("DEBUG: Startup event completed")

    # Schedule the backup job - temporarily disabled for debugging
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_backup, 'cron', hour=0)
    scheduler.start()
    logging.info("Scheduled backup job started.")
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(title="Meal Planner", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

from app.api.routes import foods, meals, plans, templates as templates_router, weekly_menu, tracker, admin, export, charts

app.include_router(foods.router, tags=["foods"])
app.include_router(meals.router, tags=["meals"])
app.include_router(plans.router, tags=["plans"])
app.include_router(templates_router.router, tags=["templates"])
app.include_router(weekly_menu.router, tags=["weekly_menu"])
app.include_router(tracker.router, tags=["tracker"])
app.include_router(admin.router, tags=["admin"])
app.include_router(export.router, tags=["export"])
app.include_router(charts.router, tags=["charts"])

# Add a logging middleware to see incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response

# Get the port from environment variable or default to 8999
PORT = int(os.getenv("PORT", 8999))

# This will be called if running directly with Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    
# Import Pydantic models from the database module
from app.database import FoodCreate, FoodResponse, MealCreate, TrackedDayCreate, TrackedMealCreate, FoodExport, MealFoodExport, MealExport, PlanExport, TemplateMealExport, TemplateExport, TemplateMealDetail, TemplateDetail, WeeklyMenuDayExport, WeeklyMenuDayDetail, WeeklyMenuExport, WeeklyMenuDetail, TrackedMealExport, TrackedDayExport, AllData, TrackedDay

def backup_database(source_db_path, backup_db_path):
    """Backs up an SQLite database using the online backup API."""
    logging.info(f"DEBUG: Starting backup - source: {source_db_path}, backup: {backup_db_path}")
    import tempfile
    
    try:
        # Check if source database exists
        if not os.path.exists(source_db_path):
            logging.error(f"DEBUG: Source database file does not exist: {source_db_path}")
            return False
        
        # Create backup in temporary directory first (local fast storage)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_backup_path = temp_file.name
        
        logging.info(f"DEBUG: Creating temporary backup at: {temp_backup_path}")
        
        # Backup to local temp file (fast)
        source_conn = sqlite3.connect(source_db_path)
        temp_conn = sqlite3.connect(temp_backup_path)
        
        with temp_conn:
            source_conn.backup(temp_conn)
        
        source_conn.close()
        temp_conn.close()
        
        logging.info(f"DEBUG: Temporary backup created, copying to final destination")
        
        # Ensure backup directory exists
        backup_dir = os.path.dirname(backup_db_path)
        if backup_dir and not os.path.exists(backup_dir):
            logging.info(f"DEBUG: Creating backup directory: {backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)
        
        # Copy to NAS (this may be slow but won't block SQLite)
        shutil.copy2(temp_backup_path, backup_db_path)
        
        # Clean up temp file
        os.unlink(temp_backup_path)
        
        logging.info(f"Backup of '{source_db_path}' created successfully at '{backup_db_path}'")
        return True

    except sqlite3.Error as e:
        logging.error(f"SQLite error during backup: {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error during backup: {e}", exc_info=True)
        return False
    finally:
        # Cleanup temp file if it still exists
        if 'temp_backup_path' in locals() and os.path.exists(temp_backup_path):
            try:
                os.unlink(temp_backup_path)
            except:
                pass
def scheduled_backup():
    """Create a backup of the database."""
    db_path = DATABASE_URL.split("///")[1]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = "./backups"
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_path = os.path.join(backup_dir, f"meal_planner_{timestamp}.db")
    backup_database(db_path, backup_path)


def test_sqlite_connection(db_path):
    """Test if we can create and write to SQLite database file"""
    logging.info(f"DEBUG: Starting SQLite connection test for path: {db_path}")
    try:
        import sqlite3
        import stat
        import os
        
        # Log directory permissions
        db_dir = os.path.dirname(db_path)
        logging.info(f"DEBUG: Checking database directory: {db_dir}")
        if os.path.exists(db_dir):
            dir_stat = os.stat(db_dir)
            dir_perm = stat.filemode(dir_stat.st_mode)
            dir_uid = dir_stat.st_uid
            dir_gid = dir_stat.st_gid
            logging.info(f"DEBUG: Database directory permissions: {dir_perm}, UID:{dir_uid}, GID:{dir_gid}, CWD: {os.getcwd()}")
            
            # Test write access
            test_file = os.path.join(db_dir, "write_test.txt")
            logging.info(f"DEBUG: Testing write access with file: {test_file}")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                logging.info("DEBUG: Write test to directory succeeded")
            except Exception as e:
                logging.error(f"DEBUG: Write test to directory failed: {e}")
                return False
        else:
            logging.warning(f"DEBUG: Database directory does not exist: {db_dir}")
            return False
        
        # Test SQLite operations
        logging.info("DEBUG: Attempting SQLite connection...")
        conn = sqlite3.connect(db_path)
        logging.info("DEBUG: SQLite connection established")
        
        cursor = conn.cursor()
        logging.info("DEBUG: Creating test table...")
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        logging.info("DEBUG: Test table created")
        
        logging.info("DEBUG: Inserting test data...")
        cursor.execute("INSERT INTO test VALUES (1)")
        logging.info("DEBUG: Test data inserted")
        
        logging.info("DEBUG: Committing transaction...")
        conn.commit()
        logging.info("DEBUG: Transaction committed")
        
        logging.info("DEBUG: Dropping test table...")
        cursor.execute("DROP TABLE test")
        logging.info("DEBUG: Test table dropped")
        
        logging.info("DEBUG: Closing connection...")
        conn.close()
        logging.info("DEBUG: Connection closed")
        
        # Log file permissions
        if os.path.exists(db_path):
            file_stat = os.stat(db_path)
            file_perm = stat.filemode(file_stat.st_mode)
            file_uid = file_stat.st_uid
            file_gid = file_stat.st_gid
            logging.info(f"DEBUG: Database file permissions: {file_perm}, UID:{file_uid}, GID:{file_gid}")
        
        logging.info("DEBUG: SQLite connection test completed successfully")
        return True
    except Exception as e:
        logging.error(f"DEBUG: SQLite connection test failed: {e}", exc_info=True)
        return False

def table_exists(engine, table_name):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    return inspector.has_table(table_name)

def table_has_content(engine, table_name):
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        return result > 0

def run_migrations():
    logging.info("DEBUG: Starting database setup...")
    try:
        alembic_cfg = Config("alembic.ini")
        
        # Create a new engine for checking tables
        from sqlalchemy import create_engine
        db_url = DATABASE_URL
        temp_engine = create_engine(db_url)
        
        # Check if the database is old and needs to be stamped
        has_alembic_version = table_exists(temp_engine, 'alembic_version')
        has_foods = table_exists(temp_engine, 'foods')
        alembic_version_has_content = has_alembic_version and table_has_content(temp_engine, 'alembic_version')
        
        logging.info(f"DEBUG: has_alembic_version: {has_alembic_version}, has_foods: {has_foods}, alembic_version_has_content: {alembic_version_has_content}")
        
        if has_foods and (not has_alembic_version or not alembic_version_has_content):
            logging.info("DEBUG: Existing database detected. Stamping with initial migration.")
            # Stamp with the specific initial migration that creates all tables
            command.stamp(alembic_cfg, "cf94fca21104")
            logging.info("DEBUG: Database stamped successfully.")

        # Now, run upgrades to bring the database to the latest version
        logging.info("DEBUG: Running alembic upgrade...")
        command.upgrade(alembic_cfg, "head")
        logging.info("DEBUG: Database migrations run successfully.")
    except Exception as e:
        logging.error(f"DEBUG: Failed to setup database: {e}", exc_info=True)
        raise

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/tracker", status_code=302)

# Add a simple test route to confirm routing is working
@app.get("/test")
async def test_route():
    logging.info("DEBUG: Test route called")
# Add a test route to check template inheritance
@app.get("/test_template", response_class=HTMLResponse)
async def test_template(request: Request):
    return templates.TemplateResponse("test_template.html", {"request": request, "person": "Sarah"})
    return {"status": "success", "message": "Test route is working"}