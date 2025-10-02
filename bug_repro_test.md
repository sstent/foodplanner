# Bug Reproduction Test Plan

This document outlines the test case required to reproduce the quantity calculation bug in the "add food" modal.

## Test File

Create a new file at `tests/test_add_food_bug.py`.

## Test Case

The following pytest test should be implemented in `tests/test_add_food_bug.py`. This test will simulate the buggy behavior by creating a food with a non-standard serving size and then asserting that the stored quantity is incorrect when a specific number of "servings" is added via the API.

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.database import Food, Meal, MealFood, TrackedDay, TrackedMeal
from datetime import date

def test_add_food_with_serving_size_multiplier(client: TestClient, db_session: Session):
    """
    Simulates the bug where the quantity is a multiple of the serving size.
    This test will fail if the bug exists.
    """
    # 1. Create a food with a serving size of 30g
    food = Food(
        name="Test Cracker",
        serving_size=30.0,
        serving_unit="g",
        calories=120,
        protein=2,
        carbs=25,
        fat=2
    )
    db_session.add(food)
    db_session.commit()

    # 2. Simulate adding the food via the API
    # The user enters "2" in the quantity field, but some faulty client-side
    # logic multiplies it by the serving size (2 * 30 = 60) before sending.
    # We are simulating the faulty request here.
    response = client.post(
        "/tracker/add_food",
        json={
            "person": "Sarah",
            "date": date.today().isoformat(),
            "food_id": food.id,
            "grams": 60.0, # This is what the backend receives
            "meal_time": "Snack 1"
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 3. Verify the stored quantity
    # Find the MealFood that was just created.
    # The bug is that the backend stores 60g, instead of what the user *thought* they entered (2 servings, which should be stored as 60g).
    # The user's report is that the quantity is a multiple.
    # A correct implementation would just store the grams value.
    # This test asserts the buggy behavior to prove it exists.
    
    # The endpoint creates a new Meal and a new TrackedMeal for the single food.
    # We need to find the most recently created one.
    created_meal = db_session.query(Meal).order_by(Meal.id.desc()).first()
    assert created_meal is not None
    assert created_meal.name == "Test Cracker"

    meal_food = db_session.query(MealFood).filter(MealFood.meal_id == created_meal.id).first()
    assert meal_food is not None

    # This assertion will pass if the bug exists, because the backend is saving the wrong value.
    # The goal is to make this test *fail* by fixing the backend logic.
    # A correct implementation would require the frontend to always send grams.
    # If the user enters "2" servings of a 30g serving size food, the frontend *should* send 60g.
    # The bug description is a bit ambiguous. Let's clarify the assertion.
    # The user said "the quantity value is a multiple of the serving size not in grams".
    # This implies if they enter "60" in the grams field, it might be getting multiplied AGAIN.
    # Let's write the test to check for THAT.

    # Re-simulating based on a clearer interpretation of the bug report.
    # The user enters "60" grams. The faulty logic might be `60 * 30 = 1800`.
    
    # Let's create a more precise test.

    # Delete the previous test data to be safe.
    db_session.delete(meal_food)
    db_session.delete(created_meal)
    db_session.commit()

    # Re-run with a clearer scenario
    response = client.post(
        "/tracker/add_food",
        json={
            "person": "Sarah",
            "date": date.today().isoformat(),
            "food_id": food.id,
            "grams": 2.0, # User wants 2 grams
            "meal_time": "Snack 1"
        }
    )
    assert response.status_code == 200

    created_meal = db_session.query(Meal).order_by(Meal.id.desc()).first()
    meal_food = db_session.query(MealFood).filter(MealFood.meal_id == created_meal.id).first()
    
    # The bug is that this is NOT 2.0, but something else.
    # Let's assume the bug is `quantity * serving_size`. So `2.0 * 30.0 = 60.0`
    # A failing test should assert the expected *correct* value.
    assert meal_food.quantity == 2.0, f"Quantity should be 2.0, but was {meal_food.quantity}"

```

## Instructions for Implementation

1.  A developer in `code` mode should create the file `tests/test_add_food_bug.py`.
2.  The code above should be added to this file.
3.  The test should be run using the command from the TDD rules to confirm that it fails as expected, thus reproducing the bug.

```bash
docker compose build; docker compose run --remove-orphans foodtracker pytest tests/test_add_food_bug.py