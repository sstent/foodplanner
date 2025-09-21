from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import re

DATABASE_URL = "sqlite:///./meal_planner.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Food(Base):
    __tablename__ = "foods"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    brand = Column(String, default="") # New field

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_food_brands():
    db = next(get_db())
    foods = db.query(Food).all()
    
    updated_count = 0
    for food in foods:
        # Check if the name contains a brand in parentheses
        match = re.search(r'\s*\((\w[^)]*)\)$', food.name)
        if match:
            brand_name = match.group(1).strip()
            # If brand is found and not already set, update
            if not food.brand and brand_name:
                food.brand = brand_name
                # Optionally remove brand from name
                food.name = re.sub(r'\s*\((\w[^)]*)\)$', '', food.name).strip()
                updated_count += 1
                print(f"Updated food '{food.name}' with brand '{food.brand}'")
        
    db.commit()
    print(f"Migration complete. Updated {updated_count} food brands.")
    db.close()

if __name__ == "__main__":
    print("Starting food brand migration...")
    # This will add the 'brand' column if it doesn't exist.
    # Note: For SQLite, ALTER TABLE ADD COLUMN is limited.
    # If the column already exists and you're just populating, Base.metadata.create_all() is fine.
    # If you're adding a new column to an existing table, you might need Alembic for proper migrations.
    # For this task, we'll assume the column is added manually or via a previous step.
    # Base.metadata.create_all(bind=engine) # This line should only be run if the table/column is new and not yet in DB
    
    # We need to reflect the existing table schema to ensure the 'brand' column is known
    # by SQLAlchemy before attempting to set its value.
    # For a real-world scenario, a proper migration tool like Alembic would handle schema changes.
    # For this simplified example, we assume the 'brand' column already exists in the DB or will be added manually.
    
    migrate_food_brands()