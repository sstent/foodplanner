import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, Food, Meal, MealFood, TrackedDay, TrackedMeal, get_db
from main import app
from datetime import date
import os
import tempfile


@pytest.fixture(scope="function")
def test_engine():
    """Create a temporary test database engine for each test"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    database_url = f"sqlite:///{db_path}"
    
    # Create engine and tables
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a database session for tests using the test engine"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_client(test_engine):
    """Create a test client with test database"""
    def override_get_db():
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


def test_add_food_quantity_saved_correctly(test_client: TestClient, test_engine):
    """
    Test that the quantity from the add food endpoint is saved correctly as grams.
    This test reproduces the bug where the backend expects "grams" but frontend sends "quantity".
    """
    # Create a session for initial setup
    setup_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)()
    
    try:
        # Create a test food using setup session
        food = Food(
            name="Test Food",
            serving_size=100.0,
            serving_unit="g",
            calories=100.0,
            protein=10.0,
            carbs=20.0,
            fat=5.0
        )
        setup_session.add(food)
        setup_session.commit()
        setup_session.refresh(food)

        # Simulate the frontend request: sends "quantity" key (as the frontend does)
        response = test_client.post(
            "/tracker/add_food",
            json={
                "person": "Sarah",
                "date": date.today().isoformat(),
                "food_id": food.id,
                "quantity": 50.0,  # User enters 50 grams
                "meal_time": "Snack 1"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Create a new session to query the committed data
        query_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)()
        
        try:
            # Find the created Meal
            created_meal = query_session.query(Meal).order_by(Meal.id.desc()).first()
            assert created_meal is not None
            assert created_meal.name == "Test Food"
            assert created_meal.meal_type == "single_food"

            # Find the MealFood
            meal_food = query_session.query(MealFood).filter(MealFood.meal_id == created_meal.id).first()
            assert meal_food is not None
            assert meal_food.food_id == food.id

            # This assertion fails because the backend used data.get("grams", 1.0), so quantity=1.0 instead of 50.0
            # After the fix changing to data.get("quantity", 1.0), it will pass
            assert meal_food.quantity == 50.0, f"Expected quantity 50.0, but got {meal_food.quantity}"

            # Also verify TrackedDay and TrackedMeal were created
            tracked_day = query_session.query(TrackedDay).filter(
                TrackedDay.person == "Sarah",
                TrackedDay.date == date.today()
            ).first()
            assert tracked_day is not None
            assert tracked_day.is_modified is True

            tracked_meal = query_session.query(TrackedMeal).filter(TrackedMeal.tracked_day_id == tracked_day.id).first()
            assert tracked_meal is not None
            assert tracked_meal.meal_id == created_meal.id
            assert tracked_meal.meal_time == "Snack 1"
            
        finally:
            query_session.close()
    
    finally:
        setup_session.close()