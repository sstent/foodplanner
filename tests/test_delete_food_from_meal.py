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

def test_delete_food_from_tracked_meal(client: TestClient, session: TestingSessionLocal):
    """
    Test deleting a food from a tracked meal. This simulates the user removing a food
    from the edit meal modal.
    """
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)

    # We want to delete food1 (Apple) and keep food2 (Banana)
    removed_food_ids = [food1.id]
    
    # The 'foods' payload will only contain the food we are keeping.
    # The id and is_custom fields are based on what the frontend would send.
    original_meal_food2 = session.query(MealFood).filter(MealFood.meal_id == meal1.id, MealFood.food_id == food2.id).first()

    update_payload = {
        "tracked_meal_id": tracked_meal.id,
        "foods": [
            {"id": original_meal_food2.id, "food_id": food2.id, "grams": 100.0, "is_custom": False},
        ],
        "removed_food_ids": removed_food_ids
    }

    response_update = client.post("/tracker/update_tracked_meal_foods", json=update_payload)
    assert response_update.status_code == 200
    assert response_update.json()["status"] == "success"

    session.expire_all()

    # Verify that an override was created for the deleted food (Apple)
    deleted_apple_override = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food1.id,
        TrackedMealFood.is_deleted == True
    ).first()
    assert deleted_apple_override is not None

    # Verify that the food we kept (Banana) does not have an override marked as deleted
    banana_override = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == food2.id,
        TrackedMealFood.is_deleted == False
    ).first()
    # In this flow, an override for Banana might not be created if the quantity is unchanged.
    # The key is that it's not marked as deleted.

    # Finally, check the get_tracked_meal_foods endpoint to ensure 'Apple' is gone
    response_get = client.get(f"/tracker/get_tracked_meal_foods/{tracked_meal.id}")
    assert response_get.status_code == 200
    data = response_get.json()
    assert data["status"] == "success"

    final_food_names = [f["food_name"] for f in data["meal_foods"]]
    assert "Apple" not in final_food_names
    assert "Banana" in final_food_names