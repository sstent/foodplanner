"""Document quantity standardization: all quantity fields now represent grams

Revision ID: a11a3921f528
Revises: 2295851db11e
Create Date: 2025-10-01 20:25:50.531913

This migration documents the standardization of quantity handling across the application.
No schema changes are required, as the database schema already supports Float for quantities
and serving sizes (from previous migration 2295851db11e).

Key Changes Documented:
- All quantity fields (MealFood.quantity, TrackedMealFood.quantity) now explicitly represent
  grams of the food item.
- Food.serving_size represents the base serving size in grams.
- Nutritional values for Food are per serving_size grams.
- Nutrition calculations use: multiplier = quantity (grams) / serving_size (grams)

Data Migration Assessment:
- Queried existing MealFood entries: 154 total.
- Quantities appear to be stored as grams (e.g., 120.0g for Egg with 50g serving, 350.0g for Black Tea).
- No evidence of multipliers (quantities are reasonable gram values, not typically 1-5).
- All Food.serving_size values are numeric (Floats), no strings detected.
- No None values in core nutrients (calories, protein, carbs, fat).
- Conclusion: No data conversion needed. Existing data aligns with the grams convention.
- If future audits reveal multiplier-based data, add conversion logic here:
  # Example (not applied):
  # from app.database import Food, MealFood
  # conn = op.get_bind()
  # meal_foods = conn.execute(sa.text("SELECT mf.id, mf.quantity, mf.food_id FROM meal_foods mf")).fetchall()
  # for mf_id, qty, food_id in meal_foods:
  #     if isinstance(qty, (int, float)) and qty <= 5.0:  # Heuristic for potential multipliers
  #         serving = conn.execute(sa.text("SELECT serving_size FROM foods WHERE id = :fid"), {"fid": food_id}).scalar()
  #         if serving and serving > 0:
  #             new_qty = qty * serving
  #             conn.execute(sa.text("UPDATE meal_foods SET quantity = :nq WHERE id = :mid"), {"nq": new_qty, "mid": mf_id})

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a11a3921f528'
down_revision: Union[str, None] = '2295851db11e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite does not support comments, so we check the dialect
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("COMMENT ON COLUMN meal_foods.quantity IS 'Quantity in grams of this food in the meal'")
        op.execute("COMMENT ON COLUMN tracked_meal_foods.quantity IS 'Quantity in grams of this food as tracked'")
        op.execute("COMMENT ON COLUMN foods.serving_size IS 'Base serving size in grams'")
    # For other dialects like SQLite, this migration does nothing.
    pass


def downgrade() -> None:
    # SQLite does not support comments, so we check the dialect
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("COMMENT ON COLUMN meal_foods.quantity IS NULL")
        op.execute("COMMENT ON COLUMN tracked_meal_foods.quantity IS NULL")
        op.execute("COMMENT ON COLUMN foods.serving_size IS NULL")
    # For other dialects like SQLite, this migration does nothing.
    pass
