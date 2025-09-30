"""
Pytest configuration and fixtures for meal planner tests
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, timedelta

# Import from main application and database module
from main import app
from app.database import Base, get_db, Food, Meal, MealFood, Plan, Template, TemplateMeal, WeeklyMenu, WeeklyMenuDay, TrackedDay, TrackedMeal


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database for each test"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    database_url = f"sqlite:///{db_path}"
    
    # Create engine and tables
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Provide a database session for tests"""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with test database"""
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_food(db_session):
    """Create a sample food item"""
    food = Food(
        name="Test Food",
        serving_size="100",
        serving_unit="g",
        calories=200.0,
        protein=10.0,
        carbs=20.0,
        fat=5.0,
        fiber=2.0,
        sugar=3.0,
        sodium=100.0,
        calcium=50.0,
        source="manual",
        brand="Test Brand"
    )
    db_session.add(food)
    db_session.commit()
    db_session.refresh(food)
    return food


@pytest.fixture
def sample_foods(db_session):
    """Create multiple sample food items"""
    foods = [
        Food(
            name=f"Food {i}",
            serving_size="100",
            serving_unit="g",
            calories=100.0 * i,
            protein=5.0 * i,
            carbs=10.0 * i,
            fat=2.0 * i,
            fiber=1.0,
            sugar=2.0,
            sodium=50.0,
            calcium=25.0,
            source="manual",
            brand=f"Brand {i}"
        )
        for i in range(1, 4)
    ]
    for food in foods:
        db_session.add(food)
    db_session.commit()
    for food in foods:
        db_session.refresh(food)
    return foods


@pytest.fixture
def sample_meal(db_session, sample_foods):
    """Create a sample meal with foods"""
    meal = Meal(
        name="Test Meal",
        meal_type="breakfast",
        meal_time="Breakfast"
    )
    db_session.add(meal)
    db_session.commit()
    db_session.refresh(meal)
    
    # Add foods to meal
    for i, food in enumerate(sample_foods[:2], 1):
        meal_food = MealFood(
            meal_id=meal.id,
            food_id=food.id,
            quantity=float(i)
        )
        db_session.add(meal_food)
    
    db_session.commit()
    db_session.refresh(meal)
    return meal


@pytest.fixture
def sample_template(db_session, sample_meal):
    """Create a sample template"""
    template = Template(name="Test Template")
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    
    template_meal = TemplateMeal(
        template_id=template.id,
        meal_id=sample_meal.id,
        meal_time="Breakfast"
    )
    db_session.add(template_meal)
    db_session.commit()
    db_session.refresh(template)
    return template


@pytest.fixture
def sample_weekly_menu(db_session, sample_template):
    """Create a sample weekly menu with templates assigned to days"""
    weekly_menu = WeeklyMenu(name="Sample Weekly Menu")
    db_session.add(weekly_menu)
    db_session.commit()
    db_session.refresh(weekly_menu)

    # Assign sample_template to Monday (day 0) and Tuesday (day 1)
    weekly_menu_day_monday = WeeklyMenuDay(
        weekly_menu_id=weekly_menu.id,
        day_of_week=0,
        template_id=sample_template.id
    )
    weekly_menu_day_tuesday = WeeklyMenuDay(
        weekly_menu_id=weekly_menu.id,
        day_of_week=1,
        template_id=sample_template.id
    )
    db_session.add(weekly_menu_day_monday)
    db_session.add(weekly_menu_day_tuesday)
    db_session.commit()
    db_session.refresh(weekly_menu)
    return weekly_menu


@pytest.fixture
def sample_plan(db_session, sample_meal):
    """Create a sample plan"""
    plan = Plan(
        person="Sarah",
        date=date.today(),
        meal_id=sample_meal.id,
        meal_time="Breakfast"
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def sample_tracked_day(db_session, sample_meal):
    """Create a sample tracked day with meals"""
    tracked_day = TrackedDay(
        person="Sarah",
        date=date.today(),
        is_modified=False
    )
    db_session.add(tracked_day)
    db_session.commit()
    db_session.refresh(tracked_day)
    
    tracked_meal = TrackedMeal(
        tracked_day_id=tracked_day.id,
        meal_id=sample_meal.id,
        meal_time="Breakfast"
    )
    db_session.add(tracked_meal)
    db_session.commit()
    db_session.refresh(tracked_day)
    return tracked_day
