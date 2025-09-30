import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from app.database import get_db, Base, Food, Meal, MealFood, Plan, Template, TemplateMeal
from datetime import date, timedelta

# Setup test database to match Docker environment
import os
from pathlib import Path

# Create test database directory if it doesn't exist
test_db_dir = "/app/data"
os.makedirs(test_db_dir, exist_ok=True)

# Use the same database path as Docker container
SQLALCHEMY_DATABASE_URL = "sqlite:////app/data/test_detailed.db"
print(f"Using test database at: {SQLALCHEMY_DATABASE_URL}")

test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(name="session")
def session_fixture():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def test_detailed_page_no_params(client):
    response = client.get("/detailed")
    assert response.status_code == 200
    assert "Detailed View for" in response.text


def test_detailed_page_default_date(client, session):
    # Create mock data for today
    food = Food(
        name="Apple", 
        serving_size="100", 
        serving_unit="g", 
        calories=52, 
        protein=0.3, 
        carbs=14, 
        fat=0.2,
        fiber=2.4,  # Added fiber
        sugar=10.0,  # Added sugar
        sodium=1.0,  # Added sodium
        calcium=6.0,  # Added calcium
        source="manual"
    )
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
    # Check for the unescaped version or the page title
    assert "Detailed Plan for" in response.text
    assert test_date.strftime('%B %d, %Y') in response.text
    assert "Fruit Snack" in response.text


def test_detailed_page_with_plan_date(client, session):
    # Create mock data
    food = Food(
        name="Apple", 
        serving_size="100", 
        serving_unit="g", 
        calories=52, 
        protein=0.3, 
        carbs=14, 
        fat=0.2,
        fiber=2.4,
        sugar=10.0,
        sodium=1.0,
        calcium=6.0,
        source="manual"
    )
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

    response = client.get(f"/detailed?person=Sarah&plan_date={test_date.isoformat()}")
    assert response.status_code == 200
    # Check for the page content without assuming apostrophe encoding
    assert "Detailed Plan for" in response.text
    assert "Fruit Snack" in response.text


def test_detailed_page_with_template_id(client, session):
    # Create mock data
    food = Food(
        name="Banana", 
        serving_size="100", 
        serving_unit="g", 
        calories=89, 
        protein=1.1, 
        carbs=23, 
        fat=0.3,
        fiber=2.6,
        sugar=12.0,
        sodium=1.0,
        calcium=5.0,
        source="manual"
    )
    session.add(food)
    session.commit()
    session.refresh(food)

    meal = Meal(name="Banana Smoothie", meal_type="breakfast", meal_time="Breakfast")
    session.add(meal)
    session.commit()
    session.refresh(meal)

    meal_food = MealFood(meal_id=meal.id, food_id=food.id, quantity=1.0)
    session.add(meal_food)
    session.commit()

    template = Template(name="Morning Boost")
    session.add(template)
    session.commit()
    session.refresh(template)

    template_meal = TemplateMeal(template_id=template.id, meal_id=meal.id, meal_time="Breakfast")
    session.add(template_meal)
    session.commit()

    response = client.get(f"/detailed?template_id={template.id}")
    assert response.status_code == 200
    assert "Morning Boost Template" in response.text
    assert "Banana Smoothie" in response.text


def test_detailed_page_with_invalid_plan_date(client):
    invalid_date = date.today() + timedelta(days=100)
    response = client.get(f"/detailed?person=Sarah&plan_date={invalid_date.isoformat()}")
    assert response.status_code == 200
    # Check for content that indicates empty plan
    assert "Detailed Plan for" in response.text
    assert "No meals planned for this day." in response.text


def test_detailed_page_with_invalid_template_id(client):
    response = client.get(f"/detailed?template_id=99999")
    assert response.status_code == 200
    assert "Template Not Found" in response.text


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
    assert "View Template" in response.text
    assert "Morning Boost" in response.text
    assert "Evening Energy" in response.text
    
    # Verify that template IDs are present in the dropdown options
    # Use url_for style or direct check
    assert str(template1.id) in response.text
    assert str(template2.id) in response.text