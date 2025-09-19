#!/usr/bin/env python3
"""
Migration script to convert Plan.date from String to Date type
and convert existing "DayX" values to actual calendar dates.
"""

import sqlite3
from datetime import datetime, timedelta

def migrate_plans_to_dates():
    """Convert existing DayX plans to actual dates"""

    # Connect to database
    conn = sqlite3.connect('meal_planner.db')
    cursor = conn.cursor()

    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(plans)")
        columns = cursor.fetchall()
        date_column_type = None

        for col in columns:
            if col[1] == 'date':  # column name
                date_column_type = col[2]  # column type
                break

        if date_column_type and 'DATE' in date_column_type.upper():
            print("Migration already completed - date column is already DATE type")
            return

        print("Starting migration from String to Date...")

        # Create backup
        print("Creating backup of plans table...")
        cursor.execute("""
            CREATE TABLE plans_backup AS
            SELECT * FROM plans
        """)

        # Add new date column
        print("Adding new date column...")
        cursor.execute("""
            ALTER TABLE plans ADD COLUMN date_new DATE
        """)

        # Convert DayX to actual dates (starting from today as Day1)
        print("Converting DayX values to dates...")
        today = datetime.now().date()

        # Get all unique day values
        cursor.execute("SELECT DISTINCT date FROM plans WHERE date LIKE 'Day%'")
        day_values = cursor.fetchall()

        for (day_str,) in day_values:
            if day_str.startswith('Day'):
                try:
                    day_num = int(day_str[3:])  # Extract number from "Day1", "Day2", etc.
                    # Convert to date (Day1 = today, Day2 = tomorrow, etc.)
                    actual_date = today + timedelta(days=day_num - 1)

                    cursor.execute("""
                        UPDATE plans
                        SET date_new = ?
                        WHERE date = ?
                    """, (actual_date.isoformat(), day_str))

                    print(f"Converted {day_str} to {actual_date.isoformat()}")

                except (ValueError, IndexError) as e:
                    print(f"Error converting {day_str}: {e}")

        # Handle any non-DayX dates (if they exist)
        cursor.execute("""
            UPDATE plans
            SET date_new = date
            WHERE date NOT LIKE 'Day%' AND date_new IS NULL
        """)

        # Recreate table with new structure (SQLite doesn't support DROP COLUMN with indexes)
        print("Recreating table with new structure...")
        cursor.execute("""
            CREATE TABLE plans_new (
                id INTEGER PRIMARY KEY,
                person VARCHAR NOT NULL,
                date DATE NOT NULL,
                meal_id INTEGER NOT NULL REFERENCES meals(id)
            )
        """)

        # Copy data to new table
        cursor.execute("""
            INSERT INTO plans_new (id, person, date, meal_id)
            SELECT id, person, date_new, meal_id FROM plans
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE plans")
        cursor.execute("ALTER TABLE plans_new RENAME TO plans")

        # Create index on new date column
        cursor.execute("CREATE INDEX ix_plans_date ON plans(date)")

        conn.commit()
        print("Migration completed successfully!")

        # Show summary
        cursor.execute("SELECT COUNT(*) FROM plans")
        total_plans = cursor.fetchone()[0]
        print(f"Total plans migrated: {total_plans}")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()

        # Restore backup if something went wrong
        try:
            cursor.execute("DROP TABLE IF EXISTS plans")
            cursor.execute("ALTER TABLE plans_backup RENAME TO plans")
            print("Restored from backup")
        except Exception as backup_error:
            print(f"Failed to restore backup: {backup_error}")

    finally:
        conn.close()

if __name__ == "__main__":
    migrate_plans_to_dates()