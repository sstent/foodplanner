#!/usr/bin/env python3
"""
Migration script to add tracker tables for meal tracking functionality.
Run this script to add the necessary tables for the Tracker tab.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database setup
DATABASE_URL = "sqlite:///./meal_planner.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# New models for tracker functionality
class TrackedDay(Base):
    """Represents a day being tracked (separate from planned days)"""
    __tablename__ = "tracked_days"

    id = Column(Integer, primary_key=True, index=True)
    person = Column(String, index=True)  # Person A or Person B
    date = Column(Date, index=True)  # Date being tracked

class TrackedMeal(Base):
    """Represents a meal tracked for a specific day"""
    __tablename__ = "tracked_meals"

    id = Column(Integer, primary_key=True, index=True)
    tracked_day_id = Column(Integer)  # Will add FK constraint later
    meal_id = Column(Integer)  # Will add FK constraint later
    meal_time = Column(String)  # Breakfast, Lunch, Dinner, Snack 1, Snack 2, Beverage 1, Beverage 2
    quantity = Column(Float, default=1.0)  # Quantity multiplier (e.g., 1.5 for 1.5 servings)

def migrate_tracker_tables():
    """Create the new tracker tables"""
    try:
        print("Creating tracker tables...")
        Base.metadata.create_all(bind=engine)
        print("Migration completed successfully!")
        print("New tables created:")
        print("- tracked_days: Stores individual days being tracked")
        print("- tracked_meals: Stores meals for each tracked day")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_tracker_tables()