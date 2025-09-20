#!/usr/bin/env python3
"""
Database migration script to add new fields for food sources and meal times.
Run this script to update the database schema.
"""

import sqlite3
from sqlalchemy import create_engine, text
from main import Base, engine

def migrate_database():
    """Add new columns to existing tables"""

    # Connect to database
    conn = sqlite3.connect('./meal_planner.db')
    cursor = conn.cursor()

    try:
        # Check if source column exists in foods table
        cursor.execute("PRAGMA table_info(foods)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'source' not in column_names:
            print("Adding 'source' column to foods table...")
            cursor.execute("ALTER TABLE foods ADD COLUMN source TEXT DEFAULT 'manual'")
            print("✓ Added source column to foods table")

        # Check if meal_time column exists in plans table
        cursor.execute("PRAGMA table_info(plans)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'meal_time' not in column_names:
            print("Adding 'meal_time' column to plans table...")
            cursor.execute("ALTER TABLE plans ADD COLUMN meal_time TEXT DEFAULT 'Breakfast'")
            print("✓ Added meal_time column to plans table")

        # Update existing records to have proper source values
        print("Updating existing food records with source information...")

        # Set source to 'csv' for foods that might have been imported
        # Note: This is a heuristic - you may need to adjust based on your data
        cursor.execute("""
            UPDATE foods
            SET source = 'csv'
            WHERE name LIKE '%(%'
            AND source = 'manual'
        """)

        conn.commit()
        print("✓ Migration completed successfully!")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting database migration...")
    migrate_database()
    print("Migration script completed.")