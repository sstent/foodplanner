Food Planner Quantity Standardization Plan
Problem Statement
The application has inconsistent handling of food quantities throughout the codebase:

Current Issue: MealFood.quantity is being used sometimes as a multiplier of serving_size and sometimes as grams directly
Impact: Confusing calculations in nutrition functions and unclear user interface expectations
Goal: Standardize so MealFood.quantity always represents grams of the food item


Core Data Model Definition
Standard to Adopt
Food.serving_size = base serving size in grams (e.g., 100)
Food.[nutrients] = nutritional values per serving_size grams
MealFood.quantity = actual grams to use (e.g., 150g)
TrackedMealFood.quantity = actual grams to use (e.g., 200g)

Calculation: multiplier = quantity / serving_size

Implementation Plan
Phase 1: Audit & Document (Non-Breaking)
Task 1.1: Add documentation header to app/database.py
python"""
QUANTITY CONVENTION:
All quantity fields in this application represent GRAMS.

- Food.serving_size: base serving size in grams (e.g., 100.0)
- Food nutrition values: per serving_size grams
- MealFood.quantity: grams of this food in the meal (e.g., 150.0)
- TrackedMealFood.quantity: grams of this food as tracked (e.g., 200.0)

To calculate nutrition: multiplier = quantity / serving_size
"""
Task 1.2: Audit all locations where quantity is read/written

 app/database.py - calculation functions
 app/api/routes/meals.py - meal food operations
 app/api/routes/tracker.py - tracked meal operations
 app/api/routes/plans.py - detailed view
 Templates using quantity values


Phase 2: Fix Core Calculation Functions
Task 2.1: Fix calculate_meal_nutrition() in app/database.py
Current behavior: Assumes quantity is already a multiplier
New behavior: Calculate multiplier from grams
pythondef calculate_meal_nutrition(meal, db: Session):
    """
    Calculate total nutrition for a meal.
    MealFood.quantity is in GRAMS.
    """
    totals = {
        'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
        'fiber': 0, 'sugar': 0, 'sodium': 0, 'calcium': 0
    }
    
    for meal_food in meal.meal_foods:
        food = meal_food.food
        grams = meal_food.quantity
        
        # Convert grams to multiplier based on serving size
        try:
            serving_size = float(food.serving_size)
            multiplier = grams / serving_size if serving_size > 0 else 0
        except (ValueError, TypeError):
            multiplier = 0
        
        totals['calories'] += food.calories * multiplier
        totals['protein'] += food.protein * multiplier
        totals['carbs'] += food.carbs * multiplier
        totals['fat'] += food.fat * multiplier
        totals['fiber'] += (food.fiber or 0) * multiplier
        totals['sugar'] += (food.sugar or 0) * multiplier
        totals['sodium'] += (food.sodium or 0) * multiplier
        totals['calcium'] += (food.calcium or 0) * multiplier
    
    # Calculate percentages (unchanged)
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
Task 2.2: Fix calculate_tracked_meal_nutrition() in app/database.py
Apply the same pattern to handle TrackedMealFood.quantity as grams.
Task 2.3: Remove or fix convert_grams_to_quantity() function
This function appears to be unused but creates confusion. Either:

Remove it entirely, OR
Rename to calculate_multiplier_from_grams() and update documentation


Phase 3: Fix API Routes
Task 3.1: Fix app/api/routes/meals.py
Location: POST /meals/{meal_id}/add_food
python@router.post("/meals/{meal_id}/add_food")
async def add_food_to_meal(
    meal_id: int,
    food_id: int = Form(...),
    grams: float = Form(...),  # Changed from 'quantity' to be explicit
    db: Session = Depends(get_db)
):
    try:
        # Store grams directly - no conversion needed
        meal_food = MealFood(
            meal_id=meal_id,
            food_id=food_id,
            quantity=grams  # This is grams
        )
        db.add(meal_food)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
Location: POST /meals/update_food_quantity
python@router.post("/meals/update_food_quantity")
async def update_meal_food_quantity(
    meal_food_id: int = Form(...),
    grams: float = Form(...),  # Changed from 'quantity'
    db: Session = Depends(get_db)
):
    try:
        meal_food = db.query(MealFood).filter(MealFood.id == meal_food_id).first()
        if not meal_food:
            return {"status": "error", "message": "meal food not found"}
        
        meal_food.quantity = grams  # Store grams directly
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
Task 3.2: Fix app/api/routes/tracker.py
Review all tracked meal operations to ensure they handle grams correctly.
Task 3.3: Fix app/api/routes/plans.py detailed view
The detailed view calculates nutrition per food item. Update to show grams clearly:
pythonfor mf in tm.meal.meal_foods:
    try:
        serving_size_value = float(mf.food.serving_size)
        num_servings = mf.quantity / serving_size_value if serving_size_value != 0 else 0
    except (ValueError, TypeError):
        num_servings = 0
    
    foods.append({
        'name': mf.food.name,
        'total_grams': mf.quantity,  # Explicitly show it's grams
        'num_servings': round(num_servings, 2),
        'serving_size': mf.food.serving_size,
        'serving_unit': mf.food.serving_unit,
        # Don't recalculate nutrition here - it's done in calculate_meal_nutrition
    })

Phase 4: Fix CSV Import Functions
Task 4.1: Fix app/api/routes/meals.py - POST /meals/upload
Currently processes ingredient pairs as (food_name, grams). Ensure it stores grams directly:
pythonfor i in range(1, len(row), 2):
    if i+1 >= len(row) or not row[i].strip():
        continue
    
    food_name = row[i].strip()
    grams = float(row[i+1].strip())  # This is grams
    
    # ... find food ...
    
    ingredients.append((food.id, grams))  # Store grams directly

# Later when creating MealFood:
for food_id, grams in ingredients:
    meal_food = MealFood(
        meal_id=existing.id,
        food_id=food_id,
        quantity=grams  # Store grams directly
    )

Phase 5: Update Templates & UI
Task 5.1: Update templates/detailed.html
Ensure the food breakdown clearly shows grams:
html<li>
    {{ food.total_grams }}g of {{ food.name }}
    ({{ food.num_servings|round(2) }} servings of {{ food.serving_size }}{{ food.serving_unit }})
</li>
Task 5.2: Update meal editing forms
Ensure all forms ask for "grams" not "quantity" to avoid confusion.

Phase 6: Add Tests
Task 6.1: Create test file tests/test_quantity_consistency.py
pythondef test_meal_nutrition_uses_grams_correctly(db_session):
    """Verify that MealFood.quantity as grams calculates nutrition correctly"""
    # Create a food: 100 cal per 100g
    food = Food(
        name="Test Food",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0,
        protein=10.0,
        carbs=20.0,
        fat=5.0
    )
    db_session.add(food)
    db_session.commit()
    
    # Create a meal with 200g of this food
    meal = Meal(name="Test Meal", meal_type="breakfast")
    db_session.add(meal)
    db_session.commit()
    
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=200.0  # 200 grams
    )
    db_session.add(meal_food)
    db_session.commit()
    
    # Calculate nutrition
    nutrition = calculate_meal_nutrition(meal, db_session)
    
    # Should be 2x the base values (200g / 100g = 2x multiplier)
    assert nutrition['calories'] == 200.0
    assert nutrition['protein'] == 20.0
    assert nutrition['carbs'] == 40.0
    assert nutrition['fat'] == 10.0

def test_fractional_servings(db_session):
    """Test that fractional grams work correctly"""
    food = Food(
        name="Test Food",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0
    )
    db_session.add(food)
    db_session.commit()
    
    meal = Meal(name="Test Meal")
    db_session.add(meal)
    db_session.commit()
    
    # Add 50g (half serving)
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=50.0
    )
    db_session.add(meal_food)
    db_session.commit()
    
    nutrition = calculate_meal_nutrition(meal, db_session)
    assert nutrition['calories'] == 50.0
Task 6.2: Run existing tests to verify no regressions

Phase 7: Data Migration (if needed)
Task 7.1: Determine if existing data needs migration
Check if current database has MealFood entries where quantity is already being stored as multipliers instead of grams. If so, create a data migration script.
Task 7.2: Create Alembic migration (documentation only)
python"""clarify quantity fields represent grams

Revision ID: xxxxx
Revises: 2295851db11e
Create Date: 2025-10-01
"""

def upgrade() -> None:
    # No schema changes needed
    # This migration documents that all quantity fields = grams
    # If data migration is needed, add conversion logic here
    pass

def downgrade() -> None:
    pass

Testing Checklist

 Add 100g of a food with 100 cal/100g → should show 100 cal
 Add 200g of a food with 100 cal/100g → should show 200 cal
 Add 50g of a food with 100 cal/100g → should show 50 cal
 Import meals from CSV with gram values → should calculate correctly
 View detailed page for template → should show grams and correct totals
 View detailed page for tracked day → should show grams and correct totals
 Edit meal food quantity → should accept and store grams


Rollout Plan

Deploy to staging: Test all functionality manually
Run automated tests: Verify calculations
Check existing data: Ensure no corruption
Deploy to production: Monitor for errors
Document changes: Update any user documentation


Risk Assessment
Low Risk:

Adding documentation
Fixing calculation functions (if current behavior is already treating quantity as grams)

Medium Risk:

Changing API parameter names from quantity to grams
Updating templates

High Risk:

If existing database has mixed data (some quantities are multipliers, some are grams)
Need to audit actual database content before proceeding


Notes

The CSV import already seems to expect grams based on the code
The main issue appears to be in calculate_meal_nutrition() if it's not properly converting grams to multipliers
Consider adding database constraints or validation to ensure quantity > 0 and reasonable ranges