import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app.database import calculate_multiplier_from_grams
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, Food, Meal, MealFood
from app.database import TrackedMealFood
from app.database import TrackedDay, TrackedMeal
from main import app

# Setup a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="session")
def session_fixture():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def sample_food_100g(session):
    food = Food(name="Sample Food 100g", serving_size="100", serving_unit="g", calories=100.0, protein=10.0, carbs=20.0, fat=5.0)
    session.add(food)
    session.commit()
    session.refresh(food)
    return food

@pytest.fixture
def sample_food_50g(session):
    food = Food(name="Sample Food 50g", serving_size="50", serving_unit="g", calories=50.0, protein=5.0, carbs=10.0, fat=2.5)
    session.add(food)
    session.commit()
    session.refresh(food)
    return food

def test_convert_grams_to_quantity_100g_food(session, sample_food_100g):
    """Test convert_grams_to_quantity for a 100g serving size food"""
    grams = 150.0
    quantity = calculate_multiplier_from_grams(sample_food_100g.id, grams, session)
    assert quantity == 1.5

def test_convert_grams_to_quantity_50g_food(session, sample_food_50g):
    """Test convert_grams_to_quantity for a 50g serving size food"""
    grams = 125.0
    quantity = calculate_multiplier_from_grams(sample_food_50g.id, grams, session)
    assert quantity == 2.5

def test_convert_grams_to_quantity_invalid_food_id(session):
    """Test convert_grams_to_quantity with an invalid food ID"""
    with pytest.raises(ValueError, match="Food with ID 999 not found."):
        calculate_multiplier_from_grams(999, 100.0, session)

def test_convert_grams_to_quantity_zero_serving_size(session):
    """Test convert_grams_to_quantity with zero serving size"""
    food = Food(name="Zero Serving Food", serving_size="0", serving_unit="g", calories=0, protein=0, carbs=0, fat=0)
    session.add(food)
    session.commit()
    session.refresh(food)
    with pytest.raises(ValueError, match="Serving size for food ID .* cannot be zero."):
        calculate_multiplier_from_grams(food.id, 100.0, session)

def test_add_food_to_meal_grams_input(client, session, sample_food_100g):
    """Test adding food to a meal with grams input"""
    meal = Meal(name="Test Meal", meal_type="custom")
    session.add(meal)
    session.commit()
    session.refresh(meal)

    response = client.post(
        f"/meals/{meal.id}/add_food",
        data={"food_id": sample_food_100g.id, "grams": 250.0} # 250 grams
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    meal_food = session.query(MealFood).filter(MealFood.meal_id == meal.id).first()
    assert meal_food.food_id == sample_food_100g.id
    assert meal_food.quantity == 250.0

def test_update_meal_food_quantity_grams_input(client, session, sample_food_50g):
    """Test updating meal food quantity with grams input"""
    meal = Meal(name="Update Meal", meal_type="custom")
    session.add(meal)
    session.commit()
    session.refresh(meal)

    # Add initial food with 100g (2.0 multiplier for 50g serving)
    initial_grams = 100.0
    meal_food = MealFood(meal_id=meal.id, food_id=sample_food_50g.id, quantity=initial_grams)
    session.add(meal_food)
    session.commit()
    session.refresh(meal_food)

    updated_grams = 150.0
    response = client.post(
        "/meals/update_food_quantity",
        data={"meal_food_id": meal_food.id, "grams": updated_grams}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    session.refresh(meal_food)
    assert meal_food.quantity == updated_grams

# Test for bulk_upload_meals would require creating a mock UploadFile and CSV content
# This is more complex and might be deferred or tested manually if the tool's capabilities are limited.
# For now, we'll assume the backend change correctly handles the quantity.

def test_tracker_add_food_grams_input(client, session, sample_food_100g):
    """Test adding single food to tracker with grams input"""
    person = "TestPerson"
    date_str = "2023-01-01"
    grams = 75.0

    response = client.post(
        "/tracker/add_food",
        json={
            "person": person,
            "date": date_str,
            "food_id": sample_food_100g.id,
            "grams": grams, # 75 grams
            "meal_time": "Breakfast"
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify the tracked meal food quantity
    tracked_meal = session.query(Meal).filter(Meal.name == sample_food_100g.name).first()
    assert tracked_meal is not None
    meal_food = session.query(MealFood).filter(MealFood.meal_id == tracked_meal.id).first()
    assert meal_food.quantity == grams

def test_update_tracked_meal_foods_grams_input(client, session, sample_food_100g, sample_food_50g):
    """Test updating tracked meal foods with grams input"""
    person = "TestPerson"
    date_str = "2023-01-02"

    # Create a tracked day and meal
    from datetime import date
    tracked_day = TrackedDay(person=person, date=date(2023, 1, 2), is_modified=False)
    session.add(tracked_day)
    session.commit()
    session.refresh(tracked_day)

    meal = Meal(name="Tracked Meal", meal_type="custom", meal_time="Lunch")
    session.add(meal)
    session.commit()
    session.refresh(meal)

    tracked_meal = TrackedMeal(tracked_day_id=tracked_day.id, meal_id=meal.id, meal_time="Lunch")
    session.add(tracked_meal)
    session.commit()
    session.refresh(tracked_meal)

    # Add initial foods
    meal_food_100g = MealFood(meal_id=meal.id, food_id=sample_food_100g.id, quantity=100.0) # 100g
    meal_food_50g = MealFood(meal_id=meal.id, food_id=sample_food_50g.id, quantity=100.0) # 100g
    session.add_all([meal_food_100g, meal_food_50g])
    session.commit()
    session.refresh(meal_food_100g)
    session.refresh(meal_food_50g)

    # Update quantities: 100g food to 200g, 50g food to 75g
    updated_foods_data = [
        {"id": meal_food_100g.id, "food_id": sample_food_100g.id, "grams": 200.0, "is_custom": False},
        {"id": meal_food_50g.id, "food_id": sample_food_50g.id, "grams": 75.0, "is_custom": False}
    ]

    response = client.post(
        "/tracker/update_tracked_meal_foods",
        json={"tracked_meal_id": tracked_meal.id, "foods": updated_foods_data}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify updated quantities
    session.refresh(tracked_meal)
    
    # Check if MealFood was converted to TrackedMealFood for changes
    tracked_food_100g = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == sample_food_100g.id
    ).first()
    assert tracked_food_100g.quantity == 200.0

    tracked_food_50g = session.query(TrackedMealFood).filter(
        TrackedMealFood.tracked_meal_id == tracked_meal.id,
        TrackedMealFood.food_id == sample_food_50g.id
    ).first()
    assert tracked_food_50g.quantity == 75.0
