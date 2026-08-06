import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database import Base, get_db, Food, TrackedDay, TrackedMeal, TrackedMealFood
from datetime import date

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
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_single_food_edit_retrieval(client: TestClient, session):
    # 1. Create a food item (e.g. Asparagus)
    asparagus = Food(
        name="Asparagus", serving_size=100, serving_unit="g",
        calories=20, protein=2.2, carbs=3.9, fat=0.2, fiber=2.1, sugar=1.9, sodium=2
    )
    session.add(asparagus)
    session.commit()
    session.refresh(asparagus)

    # 2. Add single food to tracker
    response = client.post(
        "/tracker/add_food",
        json={
            "date": "2026-08-05",
            "food_id": asparagus.id,
            "quantity": 150.0,
            "meal_time": "Breakfast"
        },
        cookies={"person": "stuart"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # 3. Verify TrackedMeal was created
    tracked_meal = session.query(TrackedMeal).first()
    assert tracked_meal is not None
    assert tracked_meal.name == "Asparagus"
    assert tracked_meal.meal_id is None

    # 4. Attempt to get foods for editing this tracked meal
    edit_response = client.get(f"/tracker/get_tracked_meal_foods/{tracked_meal.id}")
    assert edit_response.status_code == 200
    edit_data = edit_response.json()
    
    # Assert successful retrieval of meal foods
    assert edit_data.get("status") == "success", f"Expected success but got: {edit_data}"
    assert len(edit_data.get("meal_foods", [])) == 1
    assert edit_data["meal_foods"][0]["food_name"] == "Asparagus"
    assert edit_data["meal_foods"][0]["quantity"] == 150.0
