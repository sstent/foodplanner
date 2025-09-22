#!/usr/bin/env python3
"""
Migration script to add is_modified column to tracked_days table.
Run this script to add the modification tracking functionality.
"""

import sqlite3
import os

def migrate_add_is_modified():
    """Add is_modified column to tracked_days table"""
    db_path = "./meal_planner.db"

    if not os.path.exists(db_path):
        print("Database file not found. Please run the main application first to create the database.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(tracked_days)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'is_modified' in column_names:
            print("Column 'is_modified' already exists in tracked_days table.")
            conn.close()
            return

        print("Adding is_modified column to tracked_days table...")

        # Add the column with default value 0 (False)
        cursor.execute("ALTER TABLE tracked_days ADD COLUMN is_modified INTEGER DEFAULT 0")

        # Update existing rows to have is_modified = 0 (not modified)
        cursor.execute("UPDATE tracked_days SET is_modified = 0 WHERE is_modified IS NULL")

        conn.commit()
        conn.close()

        print("Migration completed successfully!")
        print("Added column: is_modified (INTEGER, DEFAULT 0)")

    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_add_is_modified()