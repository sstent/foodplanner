import pytest
from app.database import Food, TrackedMeal, TrackedMealFood, calculate_tracked_meal_nutrition
from sqlalchemy.orm import Session

def test_calculate_tracked_meal_nutrition_no_meal_template(db_session: Session):
    """Test nutrition calculation for a tracked meal with no parent meal template (meal_id=None)"""
    # Create a food
    food = Food(
        name="Test Food",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0,
        protein=10.0,
        carbs=20.0,
        fat=5.0,
        fiber=5.0,
        sugar=10.0,
        sodium=100.0,
        calcium=50.0
    )
    db_session.add(food)
    db_session.commit()
    db_session.refresh(food)

    # Create a tracked meal without a template
    tracked_meal = TrackedMeal(
        meal_id=None,
        meal_time="Snack",
        name="Single Food Log"
    )
    db_session.add(tracked_meal)
    db_session.commit()
    db_session.refresh(tracked_meal)

    # Add a tracked food entry to it
    tracked_food = TrackedMealFood(
        tracked_meal_id=tracked_meal.id,
        food_id=food.id,
        quantity=200.0, # 2 servings
        is_override=False,
        is_deleted=False
    )
    db_session.add(tracked_food)
    db_session.commit()
    db_session.refresh(tracked_food)

    # Calculate nutrition
    nutrition = calculate_tracked_meal_nutrition(tracked_meal, db_session)

    # Assertions
    assert nutrition['calories'] == 200.0
    assert nutrition['protein'] == 20.0
    assert nutrition['carbs'] == 40.0
    assert nutrition['fat'] == 10.0
    assert nutrition['fiber'] == 10.0
    assert nutrition['sugar'] == 20.0
    assert nutrition['sodium'] == 200.0
    assert nutrition['calcium'] == 100.0
    assert nutrition['net_carbs'] == 30.0
    assert nutrition['protein_pct'] == 40.0 # (20 * 4) / 200 = 80 / 200 = 40%
    assert nutrition['carbs_pct'] == 80.0 # (40 * 4) / 200 = 160 / 200 = 80%
    assert nutrition['fat_pct'] == 45.0 # (10 * 9) / 200 = 90 / 200 = 45%

def test_tracker_add_food_api_no_new_meal(client, db_session: Session):
    """Test /tracker/add_food endpoint to ensure it doesn't create redundant Meal templates"""
    # Create a food
    food = Food(
        name="API Test Food",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0,
        protein=10.0,
        carbs=20.0,
        fat=5.0
    )
    db_session.add(food)
    db_session.commit()
    db_session.refresh(food)

    from app.database import Meal
    initial_meal_count = db_session.query(Meal).count()

    # Call the API
    response = client.post("/tracker/add_food", json={
        "person": "Sarah",
        "date": "2025-02-24",
        "food_id": food.id,
        "quantity": 150.0,
        "meal_time": "Snack"
    })

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify NO new Meal was created
    assert db_session.query(Meal).count() == initial_meal_count

    # Verify TrackedMeal exists with meal_id=None and correct name
    from app.database import TrackedMeal, TrackedDay
    tracked_day = db_session.query(TrackedDay).filter(TrackedDay.date == "2025-02-24").first()
    assert tracked_day is not None
    
    tracked_meal = db_session.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).first()
    assert tracked_meal is not None
    assert tracked_meal.meal_id is None
    assert tracked_meal.name == "API Test Food"
    
    # Verify TrackedMealFood exists
    from app.database import TrackedMealFood
    tmf = db_session.query(TrackedMealFood).filter(TrackedMealFood.tracked_meal_id == tracked_meal.id).first()
    assert tmf is not None
    assert tmf.food_id == food.id
    assert tmf.quantity == 150.0
