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
            "quantity": 200
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify the food was added to the meal associated with the tracked meal
    updated_meal_foods = session.query(MealFood).filter(MealFood.meal_id == meal1.id).all()
    assert len(updated_meal_foods) == 3 # Original 2 + new 1

    # Check the new food's quantity
    orange_meal_food = next(mf for mf in updated_meal_foods if mf.food_id == food3.id)
    assert orange_meal_food.quantity == 200

def test_remove_food_from_tracked_meal_endpoint(client: TestClient, session: TestingSessionLocal):
    """Test removing a food from a tracked meal"""
    food1, food2, meal1, tracked_day, tracked_meal = create_test_data(session)

    # Get the meal_food_id for food1
    meal_food_to_remove = session.query(MealFood).filter(
        MealFood.meal_id == meal1.id,
        MealFood.food_id == food1.id
    ).first()
    
    response = client.delete(f"/tracker/remove_food_from_tracked_meal/{meal_food_to_remove.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify the food was removed from the meal associated with the tracked meal
    updated_meal_foods = session.query(MealFood).filter(MealFood.meal_id == meal1.id).all()
    assert len(updated_meal_foods) == 1 # Original 2 - removed 1
    assert updated_meal_foods[0].food_id == food2.id # Only food2 should remain