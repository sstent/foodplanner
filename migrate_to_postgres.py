import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Import models to ensure simple table discovery if needed, 
# though we will mostly work with raw tables or inspection.
from app.database import Base, Food, Meal, MealFood, Plan, Template, TemplateMeal, WeeklyMenu, WeeklyMenuDay, TrackedDay, TrackedMeal, TrackedMealFood, FitbitConfig, WeightLog

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate():
    import argparse

    parser = argparse.ArgumentParser(description='Migrate data from SQLite to PostgreSQL')
    parser.add_argument('--sqlite-path', help='Path to source SQLite database file', default=os.getenv('SQLITE_PATH', '/app/data/meal_planner.db'))
    parser.add_argument('--pg-url', help='PostgreSQL connection URL', default=os.getenv('PG_DATABASE_URL'))
    
    args = parser.parse_args()

    # Configuration
    # Source: SQLite
    sqlite_path = args.sqlite_path
    sqlite_url = f"sqlite:///{sqlite_path}"
    
    # Destination: Postgres
    if args.pg_url:
        pg_url = args.pg_url
    else:
        # update this if running externally
        pg_user = os.getenv('POSTGRES_USER', 'user')
        pg_password = os.getenv('POSTGRES_PASSWORD', 'password')
        pg_host = os.getenv('POSTGRES_HOST', 'postgres')
        pg_db = os.getenv('POSTGRES_DB', 'meal_planner')
        pg_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}/{pg_db}"

    logger.info(f"Source SQLite: {sqlite_url}")
    logger.info(f"Destination Postgres: {pg_url}")

    # Create Engines
    try:
        sqlite_engine = create_engine(sqlite_url)
        pg_engine = create_engine(pg_url)
        
        # Test connections
        with sqlite_engine.connect() as conn:
            pass
        logger.info("Connected to SQLite.")
        
        with pg_engine.connect() as conn:
            pass
        logger.info("Connected to Postgres.")
        
    except Exception as e:
        logger.error(f"Failed to connect to databases: {e}")
        return

    # Create tables in Postgres if they don't exist
    # Using the Base metadata from the app
    logger.info("Creating tables in Postgres...")
    Base.metadata.drop_all(pg_engine) # Clean start to avoid conflicts
    Base.metadata.create_all(pg_engine)
    logger.info("Tables created.")

    # Define table order to respect Foreign Keys
    tables_ordered = [
        'foods',
        'meals',
        'meal_foods',
        'templates',
        'template_meals',
        'weekly_menus',
        'weekly_menu_days',
        'plans',
        'tracked_days',
        'tracked_meals',
        'tracked_meal_foods',
        'fitbit_config',
        'weight_logs'
    ]

    # Migration Loop
    with sqlite_engine.connect() as sqlite_conn, pg_engine.connect() as pg_conn:
        for table_name in tables_ordered:
            logger.info(f"Migrating table: {table_name}")
            
            # Read from SQLite
            try:
                # Use raw SQL to get all data, handling potential missing tables gracefully if app changed
                result = sqlite_conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()
                keys = result.keys()
                
                if not rows:
                    logger.info(f"  No data in {table_name}, skipping.")
                    continue
                
                # Insert into Postgres
                # We simply create a list of dicts
                data = [dict(zip(keys, row)) for row in rows]
                
                # Setup insert statement
                # We use SQLAlchemy core to make it db-agnostic enough
                table_obj = Base.metadata.tables[table_name]
                
                pg_conn.execute(table_obj.insert(), data)
                pg_conn.commit()
                
                logger.info(f"  Migrated {len(rows)} rows.")
                
                # Reset Sequence for Serial ID columns
                # Postgres sequences usually named table_id_seq
                if 'id' in keys:
                    # Find max id
                    max_id = max(row[0] for row in rows) # Assuming 'id' is first or we can look it up.
                    # Safer:
                    max_id_val = 0
                    for d in data:
                        if d['id'] > max_id_val:
                            max_id_val = d['id']
                    
                    if max_id_val > 0:
                        seq_name = f"{table_name}_id_seq"
                        # Check if sequence exists (it should for Serial)
                        try:
                            pg_conn.execute(text(f"SELECT setval('{seq_name}', {max_id_val})"))
                            pg_conn.commit()
                            logger.info(f"  Sequence {seq_name} reset to {max_id_val}")
                        except Exception as seq_err:
                            logger.warn(f"  Could not reset sequence {seq_name} (might not exist): {seq_err}")
                            pg_conn.rollback()

            except Exception as e:
                # Check for "no such table" specific error which is common if a feature isn't used
                if "no such table" in str(e):
                    logger.warning(f"  Table {table_name} not found in source SQLite. Skipping.")
                    continue
                
                logger.error(f"Error migrating {table_name}: {e}")
                pg_conn.rollback()
                # Decide whether to stop or continue. Stopping is safer.
                return

    logger.info("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
