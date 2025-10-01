Fix Detailed View Food Breakdown - Implementation Plan
Problem Statement
The detailed view (/detailed route) is incorrectly calculating and displaying per-food nutrition values:

Display Issue: Shows "34.0 × 34.0g" instead of "34.0g" in the Serving column
Calculation Issue: Multiplies nutrition by quantity directly instead of calculating proper multiplier (quantity ÷ serving_size)

Current incorrect calculation:
python'calories': mf.food.calories * mf.quantity  # Wrong: 125cal * 34g = 4250cal
Should be:
pythonmultiplier = mf.quantity / mf.food.serving_size  # 34g / 34g = 1.0
'calories': mf.food.calories * multiplier        # 125cal * 1.0 = 125cal

Files to Modify

app/api/routes/plans.py - Fix calculation logic in detailed() function
templates/detailed.html - Update serving column display


Implementation Steps
Step 1: Fix Template View Calculation (plans.py)
Location: app/api/routes/plans.py, in the detailed() function around lines 190-220
Find this section (for template meals):
pythonfor mf in tm.meal.meal_foods:
    try:
        serving_size_value = float(mf.food.serving_size)
        num_servings = mf.quantity / serving_size_value if serving_size_value != 0 else 0
    except (ValueError, TypeError):
        num_servings = 0
    
    foods.append({
        'name': mf.food.name,
        'total_grams': mf.quantity,
        'num_servings': num_servings,
        'serving_size': mf.food.serving_size,
        'serving_unit': mf.food.serving_unit,
        'calories': mf.food.calories * num_servings,  # May be wrong
        'protein': mf.food.protein * num_servings,
        # ... etc
    })
Replace with:
pythonfor mf in tm.meal.meal_foods:
    try:
        serving_size = float(mf.food.serving_size)
        multiplier = mf.quantity / serving_size if serving_size > 0 else 0
    except (ValueError, TypeError):
        multiplier = 0
    
    foods.append({
        'name': mf.food.name,
        'quantity': mf.quantity,  # Grams used in this meal
        'serving_unit': mf.food.serving_unit,
        # Calculate nutrition for the actual amount used
        'calories': (mf.food.calories or 0) * multiplier,
        'protein': (mf.food.protein or 0) * multiplier,
        'carbs': (mf.food.carbs or 0) * multiplier,
        'fat': (mf.food.fat or 0) * multiplier,
        'fiber': (mf.food.fiber or 0) * multiplier,
        'sodium': (mf.food.sodium or 0) * multiplier,
    })
Step 2: Fix Tracked Day View Calculation (plans.py)
Location: Same file, around lines 247-280 (in the tracked meals section)
Find this section:
pythonfor mf in tracked_meal.meal.meal_foods:
    foods.append({
        'name': mf.food.name,
        'quantity': mf.quantity,
        'serving_size': mf.food.serving_size,
        'serving_unit': mf.food.serving_unit,
    })
Replace with (add nutrition calculations):
pythonfor mf in tracked_meal.meal.meal_foods:
    try:
        serving_size = float(mf.food.serving_size)
        multiplier = mf.quantity / serving_size if serving_size > 0 else 0
    except (ValueError, TypeError):
        multiplier = 0
    
    foods.append({
        'name': mf.food.name,
        'quantity': mf.quantity,
        'serving_unit': mf.food.serving_unit,
        'calories': (mf.food.calories or 0) * multiplier,
        'protein': (mf.food.protein or 0) * multiplier,
        'carbs': (mf.food.carbs or 0) * multiplier,
        'fat': (mf.food.fat or 0) * multiplier,
        'fiber': (mf.food.fiber or 0) * multiplier,
        'sodium': (mf.food.sodium or 0) * multiplier,
    })
Step 3: Fix Template Display
Location: templates/detailed.html
Find the Serving column display (likely something like):
html<td>{{ food.total_grams }} × {{ food.serving_size }}{{ food.serving_unit }}</td>
or
html<td>{{ food.quantity }} × {{ food.serving_size }}{{ food.serving_unit }}</td>
Replace with:
html<td>{{ food.quantity }}{{ food.serving_unit }}</td>
This will show "34.0g" instead of "34.0 × 34.0g"

Testing Checklist
After making changes, test these scenarios:
Test 1: Basic Calculation

 Food with 100g serving size, 100 calories
 Add 50g to meal
 Should show: "50g" and "50 calories"

Test 2: Your Current Example

 Pea Protein: 34g serving, 125 cal/serving
 Add 34g to meal
 Should show: "34.0g" and "125 calories"
 NOT "4250 calories"

Test 3: Fractional Servings

 Food with 100g serving size, 200 calories
 Add 150g to meal
 Should show: "150g" and "300 calories"

Test 4: Template View

 View a template from the detailed page
 Verify food breakdown shows correct grams and nutrition

Test 5: Tracked Day View

 View a tracked day from the detailed page
 Verify food breakdown shows correct grams and nutrition


Code Quality Notes
Why Use Multiplier Pattern?
pythonmultiplier = quantity / serving_size
nutrition_value = base_nutrition * multiplier
This is consistent with:

calculate_meal_nutrition() function
The standardization plan
Makes the math explicit and debuggable

Error Handling
The try/except block handles:

Non-numeric serving_size values
Division by zero
NULL values (though migration confirmed none exist)


Expected Results
Before:
Serving: 34.0 × 34.0g
Calories: 4250
Protein: 952.0g
After:
Serving: 34.0g
Calories: 125
Protein: 28.0g
