# Plan for Adding New Tests to test_detailed.py

## Overview
This plan outlines the additional tests that need to be added to `tests/test_detailed.py` to cover the following functionality:
- Load today's date by default
- View date should return the meals planned for a date (already covered)
- The template dropdown should show a list of templates available to view

## Current Test Coverage
The existing tests in `tests/test_detailed.py` already cover:
- `test_detailed_page_no_params` - when no params are provided
- `test_detailed_page_with_plan_date` - when plan_date is provided
- `test_detailed_page_with_template_id` - when template_id is provided
- `test_detailed_page_with_invalid_plan_date` - when invalid plan_date is provided
- `test_detailed_page_with_invalid_template_id` - when invalid template_id is provided

## New Tests to Add

### 1. Test Default Date Loading
**Test Name:** `test_detailed_page_default_date`
**Purpose:** Verify that when no plan_date is provided, the detailed page loads with today's date by default
**Implementation:**
```python
def test_detailed_page_default_date(client, session):
    # Create mock data for today
    food = Food(name="Apple", serving_size="100", serving_unit="g", calories=52, protein=0.3, carbs=14, fat=0.2)
    session.add(food)
    session.commit()
    session.refresh(food)

    meal = Meal(name="Fruit Snack", meal_type="snack", meal_time="Snack")
    session.add(meal)
    session.commit()
    session.refresh(meal)

    meal_food = MealFood(meal_id=meal.id, food_id=food.id, quantity=1.0)
    session.add(meal_food)
    session.commit()

    test_date = date.today()
    plan = Plan(person="Sarah", date=test_date, meal_id=meal.id, meal_time="Snack")
    session.add(plan)
    session.commit()

    # Test that when no plan_date is provided, today's date is used by default
    response = client.get("/detailed?person=Sarah")
    assert response.status_code == 200
    assert "Sarah's Detailed Plan for" in response.text
    assert test_date.strftime('%B %d, %Y') in response.text  # Check if today's date appears in the formatted date
    assert "Fruit Snack" in response.text
```

### 2. Test Template Dropdown
**Test Name:** `test_detailed_page_template_dropdown`
**Purpose:** Verify that the template dropdown shows available templates
**Implementation:**
```python
def test_detailed_page_template_dropdown(client, session):
    # Create multiple templates
    template1 = Template(name="Morning Boost")
    template2 = Template(name="Evening Energy")
    session.add(template1)
    session.add(template2)
    session.commit()
    session.refresh(template1)
    session.refresh(template2)

    # Test that the template dropdown shows available templates
    response = client.get("/detailed")
    assert response.status_code == 200
    
    # Check that the response contains template selection UI elements
    assert "Select Template..." in response.text
    assert "Morning Boost" in response.text
    assert "Evening Energy" in response.text
    
    # Verify that template IDs are present in the dropdown options
    assert f'value="{template1.id}"' in response.text
    assert f'value="{template2.id}"' in response.text
```

## Implementation Notes
- Both tests should use the existing session and client fixtures
- The tests should create necessary mock data to ensure proper functionality testing
- The date default test should verify that today's date appears in the response when no date is specified
- The template dropdown test should verify that templates are properly listed in the UI

## Expected Outcome
After implementing these tests, the test coverage for the detailed page will include:
- Default date loading functionality
- Template dropdown functionality
- All existing functionality remains covered