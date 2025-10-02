import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database import Base, get_db, Food, Meal, MealFood, TrackedDay, TrackedMeal, TrackedMealFood
from datetime import date

# Setup for in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="session")
def session_fixture():
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def create_test_data(session: TestingSessionLocal):
    food1 = Food(name="Apple", serving_size=100, serving_unit="g", calories=52, protein=0.3, carbs=14, fat=0.2, fiber=2.4, sugar=10.4, sodium=1)
    food2 = Food(name="Banana", serving_size=100, serving_unit="g", calories=89, protein=1.1, carbs=23, fat=0.3, fiber=2.6, sugar=12.2, sodium=1)
    session.add_all([food1, food2])
    session.commit()
    session.refresh(food1)
    session.refresh(food2)

    meal1 = Meal(name="Fruit Salad", meal_type="custom", meal_time="Breakfast")
    session.add(meal1)
    session.commit()
    session.refresh(meal1)

    meal_food1 = MealFood(meal_id=meal1.id, food_id=food1.id, quantity=150)
    meal_food2 = MealFood(meal_id=meal1.id, food_id=food2.id, quantity=100)
    session.add_all([meal_food1, meal_food2])
    session.commit()

    tracked_day = TrackedDay(person="Sarah", date=date.today(), is_modified=False)
    session.add(tracked_day)
    session.commit()
    session.refresh(tracked_day)

    tracked_meal = TrackedMeal(tracked_day_id=tracked_day.id, meal_id=meal1.id, meal_time="Breakfast")
    session.add(tracked_meal)
    session.commit()
    session.refresh(tracked_meal)
    
    return food1, food2, meal1, tracked_day, tracked_meal

def test_get_tracked_meal_foods_endpoint(client: TestClient, session: TestingSessionLocal):
    """Test retrieving foods for a tracked meal"""
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)

    response = client.get(f"/tracker/get_tracked_meal_foods/{tracked_meal.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["meal_foods"]) == 2

    # Check if food details are correct
    food_names = [f["food_name"] for f in data["meal_foods"]]
    assert "Apple" in food_names
    assert "Banana" in food_names

    # Check quantities
    for food_data in data["meal_foods"]:
        if food_data["food_name"] == "Apple":
            assert food_data["quantity"] == 150.0
        elif food_data["food_name"] == "Banana":
            assert food_data["quantity"] == 100.0

def test_edit_tracked_meal_with_override_flow(client: TestClient, session: TestingSessionLocal):
    """
    Test the full flow of editing a tracked meal, overriding a food's quantity,
    and verifying the new override system.
    """
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)

    # 1. Get the original MealFood for food1 (Apple)
    original_meal_food1 = session.query(MealFood).filter(
        MealFood.meal_id == meal1.id,
        MealFood.food_id == food1.id
    ).first()
    assert original_meal_food1 is not None

    # 2. Prepare update data: update food1's quantity and keep food2 the same.
    updated_foods_data = [
        {"id": original_meal_food1.id, "food_id": food1.id, "grams": 175.0, "is_custom": False},
    ]

    # 3. Call the update endpoint
    response_update = client.post(
        "/tracker/update_tracked_meal_foods",
        json={
            "tracked_meal_id": tracked_meal.id,
            "foods": updated_foods_data,
            "removed_food_ids": []
        }
    )
    assert response_update.status_code == 200
    assert response_update.json()["status"] == "success"

    session.expire_all()

    # 4. Verify that a new TrackedMealFood override was created for food1
    override_food = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food1.id
    ).first()
    assert override_food is not None
    assert override_food.quantity == 175.0
    assert override_food.is_override is True

    # 5. Verify the original MealFood still exists
    assert session.query(MealFood).filter(MealFood.id == original_meal_food1.id).first() is not None

    # 6. Get the foods for the tracked meal and check the final state
    response_get = client.get(f"/tracker/get_tracked_meal_foods/{tracked_meal.id}")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get["status"] == "success"
    assert len(data_get["meal_foods"]) == 2

    food_map = {f["food_name"]: f for f in data_get["meal_foods"]}
    assert "Apple" in food_map
    assert "Banana" in food_map
    assert food_map["Apple"]["quantity"] == 175.0
    assert food_map["Apple"]["is_custom"] is True  # It's an override
    assert food_map["Banana"]["quantity"] == 100.0
    assert food_map["Banana"]["is_custom"] is False # It's from the base meal


def test_update_tracked_meal_foods_endpoint(client: TestClient, session: TestingSessionLocal):
    """Test updating quantities of foods in a tracked meal"""
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)

    # Add a tracked meal food for food1 to allow updates
    tracked_meal_food1 = TrackedMealFood(tracked_meal_id=tracked_meal.id, food_id=food1.id, quantity=150.0)
    session.add(tracked_meal_food1)
    session.commit()
    session.refresh(tracked_meal_food1)

    # Prepare update data
    updated_foods = [
        {"id": tracked_meal_food1.id, "food_id": food1.id, "grams": 200.0, "is_custom": True},
        {"id": None, "food_id": food2.id, "grams": 50.0, "is_custom": False} # This represents original meal food
    ]

    response = client.post(
        "/tracker/update_tracked_meal_foods",
        json={
            "tracked_meal_id": tracked_meal.id,
            "foods": updated_foods
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    session.expire_all() # Expire all objects in the session to ensure a fresh load

    # Verify updates in the database
    updated_meal_foods = session.query(TrackedMealFood).filter(TrackedMealFood.tracked_meal_id == tracked_meal.id).all()
    assert len(updated_meal_foods) == 2

    for tmf in updated_meal_foods:
        if tmf.food_id == food1.id:
            assert tmf.quantity == 200.0
        elif tmf.food_id == food2.id:
            assert tmf.quantity == 50.0

def test_add_food_to_tracked_meal_endpoint(client: TestClient, session: TestingSessionLocal):
    """Test adding a new food to an existing tracked meal"""
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)

    # Create a new food to add
    food3 = Food(name="Orange", serving_size=130, serving_unit="g", calories=62, protein=1.2, carbs=15, fat=0.2, fiber=3.1, sugar=12, sodium=0)
    session.add(food3)
    session.commit()
    session.refresh(food3)

    response = client.post(
        "/tracker/add_food_to_tracked_meal",
        json={
            "tracked_meal_id": tracked_meal.id,
            "food_id": food3.id,
            "grams": 200
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify the food was added as a TrackedMealFood, not a MealFood
    new_tracked_food = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food3.id
    ).first()
    assert new_tracked_food is not None
    assert new_tracked_food.quantity == 200
    assert new_tracked_food.is_override is False # It's a new addition

    # Verify the base meal is unchanged
    base_meal_foods = session.query(MealFood).filter(MealFood.meal_id == meal1.id).all()
    assert len(base_meal_foods) == 2

def test_edit_tracked_meal_bug_scenario(client: TestClient, session: TestingSessionLocal):
    """
    Simulates the full bug scenario described:
    1. Start with a meal with 2 foods.
    2. Add a 3rd food.
    3. Delete one of the original foods.
    4. Update the quantity of the other original food.
    5. Save and verify the state.
    """
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)
    
    # 1. Initial state: tracked_meal with food1 (Apple) and food2 (Banana)
    
    # 2. Add a 3rd food (Orange)
    food3 = Food(name="Orange", serving_size=130, serving_unit="g", calories=62, protein=1.2, carbs=15, fat=0.2)
    session.add(food3)
    session.commit()
    session.refresh(food3)
    
    add_food_payload = {
        "tracked_meal_id": tracked_meal.id,
        "food_id": food3.id,
        "grams": 200
    }
    response_add = client.post("/tracker/add_food_to_tracked_meal", json=add_food_payload)
    assert response_add.status_code == 200
    assert response_add.json()["status"] == "success"
    
    # Verify Orange was added as a TrackedMealFood
    orange_tmf = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food3.id
    ).first()
    assert orange_tmf is not None
    assert orange_tmf.quantity == 200
    
    # 3. Delete an original food (Apple, food1)
    # This requires an update call with the food removed from the list
    
    # 4. Update quantity of the other original food (Banana, food2)
    
    # Simulate the data sent from the frontend after edits
    final_foods_payload = [
        # food1 (Apple) is omitted, signifying deletion
        {"id": None, "food_id": food2.id, "grams": 125.0, "is_custom": False}, # Banana quantity updated
        {"id": orange_tmf.id, "food_id": food3.id, "grams": 210.0, "is_custom": True} # Orange quantity updated
    ]
    
    removed_food_ids = [food1.id]
    
    update_payload = {
        "tracked_meal_id": tracked_meal.id,
        "foods": final_foods_payload,
        "removed_food_ids": removed_food_ids
    }
    
    response_update = client.post("/tracker/update_tracked_meal_foods", json=update_payload)
    assert response_update.status_code == 200
    assert response_update.json()["status"] == "success"
    
    session.expire_all()
    
    # 5. Verify the final state
    
    # There should be one override for the deleted food (Apple)
    deleted_apple_override = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food1.id,
        TrackedMealFood.is_deleted == True
    ).first()
    assert deleted_apple_override is not None
    
    # There should be one override for the updated food (Banana)
    updated_banana_override = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food2.id
    ).first()
    assert updated_banana_override is not None
    assert updated_banana_override.quantity == 125.0
    
    # The added food (Orange) should be updated
    updated_orange_tmf = session.query(TrackedMealFood).filter(
        TrackedMealFood.id == orange_tmf.id
    ).first()
    assert updated_orange_tmf is not None
    assert updated_orange_tmf.quantity == 210.0
    
    # Let's check the get_tracked_meal_foods endpoint to be sure
    response_get = client.get(f"/tracker/get_tracked_meal_foods/{tracked_meal.id}")
    assert response_get.status_code == 200
    data = response_get.json()
    assert data["status"] == "success"
    
    # The final list should contain Banana and Orange, but not Apple
    final_food_names = [f["food_name"] for f in data["meal_foods"]]
    assert "Apple" not in final_food_names
    assert "Banana" in final_food_names
    assert "Orange" in final_food_names
    
    for food_data in data["meal_foods"]:
        if food_data["food_name"] == "Banana":
            assert food_data["quantity"] == 125.0
        elif food_data["food_name"] == "Orange":
            assert food_data["quantity"] == 210.0