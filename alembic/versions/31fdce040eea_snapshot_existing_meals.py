"""snapshot_existing_meals

Revision ID: 31fdce040eea
Revises: 4522e2de4143
Create Date: 2026-01-10 13:30:49.977264

"""
from typing import Sequence, Union
from sqlalchemy import orm, text
from app.database import Base
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31fdce040eea'
down_revision: Union[str, None] = '4522e2de4143'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # Use reflection or raw SQL to avoid importing app models directly
    # This ensures the migration remains valid even if app models change later
    
    # 1. Get all tracked meals that are NOT already snapshots
    # We join tracked_meals with meals to check the meal_type
    sql = text("""
        SELECT tm.id as tracked_meal_id, tm.meal_id, m.name, m.meal_time
        FROM tracked_meals tm
        JOIN meals m ON tm.meal_id = m.id
        WHERE m.meal_type != 'tracked_snapshot'
    """)
    
    tracked_meals_to_snapshot = session.execute(sql).fetchall()
    
    print(f"Found {len(tracked_meals_to_snapshot)} tracked meals to snapshot.")
    
    for row in tracked_meals_to_snapshot:
        tm_id = row.tracked_meal_id
        original_meal_id = row.meal_id
        original_name = row.name
        original_meal_time = row.meal_time
        
        # 2. Create a new snapshot meal
        # We can't easily use ORM since we don't have the classes, so we use raw SQL
        insert_meal_sql = text("""
            INSERT INTO meals (name, meal_type, meal_time)
            VALUES (:name, 'tracked_snapshot', :meal_time)
        """)
        
        # execution_options={"autocommit": True} might be needed for some drivers, 
        # but session.execute usually handles it. 
        # For SQLite, we can get the last inserted id via cursor, but SQLAlchemy does this via result.lastrowid
        
        result = session.execute(insert_meal_sql, {
            "name": original_name, 
            "meal_time": original_meal_time
        })
        new_meal_id = result.lastrowid
        
        # 3. Copy ingredients from original meal to new snapshot
        # Get ingredients
        get_foods_sql = text("""
            SELECT food_id, quantity 
            FROM meal_foods 
            WHERE meal_id = :meal_id
        """)
        foods = session.execute(get_foods_sql, {"meal_id": original_meal_id}).fetchall()
        
        if foods:
            insert_food_sql = text("""
                INSERT INTO meal_foods (meal_id, food_id, quantity)
                VALUES (:meal_id, :food_id, :quantity)
            """)
            
            for food in foods:
                session.execute(insert_food_sql, {
                    "meal_id": new_meal_id,
                    "food_id": food.food_id,
                    "quantity": food.quantity
                })
        
        # 4. Update the stored tracked_meal to point to the new snapshot
        update_tm_sql = text("""
            UPDATE tracked_meals
            SET meal_id = :new_meal_id
            WHERE id = :tm_id
        """)
        session.execute(update_tm_sql, {"new_meal_id": new_meal_id, "tm_id": tm_id})
        
    session.commit()



def downgrade() -> None:
    pass
