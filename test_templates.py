import sys
import os
print(f"DEBUG: Running with Python executable: {sys.executable}")
print(f"DEBUG: Python version: {sys.version}")

import pytest
from fastapi.testclient import TestClient
from main import app, get_db, SessionLocal, engine, Base, Template, TemplateMeal, Meal, MealFood, Food
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_meal_planner.db"
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

def test_templates_page(client, session):
    response = client.get("/templates")
    assert response.status_code == 200
    assert "Meal Templates" in response.text

def test_create_template(client, session):
    # Create a food and a meal first
    food1 = Food(name="Apple", serving_size="1", serving_unit="medium", calories=95, protein=0.5, carbs=25, fat=0.3)
    session.add(food1)
    session.commit()
    session.refresh(food1)

    meal1 = Meal(name="Fruit Salad", meal_type="breakfast", meal_time="Breakfast")
    session.add(meal1)
    session.commit()
    session.refresh(meal1)

    meal_food1 = MealFood(meal_id=meal1.id, food_id=food1.id, quantity=1.0)
    session.add(meal_food1)
    session.commit()

    response = client.post(
        "/templates/create", 
        data={"name": "Test Template", "meal_assignments": f"Breakfast:{meal1.id},Lunch:"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Template created successfully"}

    template = session.query(Template).filter(Template.name == "Test Template").first()
    assert template is not None
    assert len(template.template_meals) == 1
    assert template.template_meals[0].meal_time == "Breakfast"
    assert template.template_meals[0].meal_id == meal1.id

def test_create_template_duplicate_name(client, session):
    template = Template(name="Existing Template")
    session.add(template)
    session.commit()

    response = client.post("/templates/create", data={"name": "Existing Template"})
    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "Template with name 'Existing Template' already exists"}

def test_get_template_details(client, session):
    template = Template(name="Detail Template")
    session.add(template)
    session.commit()
    session.refresh(template)

    response = client.get(f"/templates/{template.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["template"]["name"] == "Detail Template"

def test_update_template(client, session):
    food1 = Food(name="Orange", serving_size="1", serving_unit="medium", calories=62, protein=1.2, carbs=15.4, fat=0.2)
    session.add(food1)
    session.commit()
    session.refresh(food1)

    meal1 = Meal(name="Orange Juice", meal_type="breakfast", meal_time="Breakfast")
    session.add(meal1)
    session.commit()
    session.refresh(meal1)

    template = Template(name="Update Template")
    session.add(template)
    session.commit()
    session.refresh(template)

    response = client.put(
        f"/templates/{template.id}",
        data={"name": "Updated Template Name", "meal_assignments": f"Breakfast:{meal1.id}"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Template updated successfully"}

    updated_template = session.query(Template).filter(Template.id == template.id).first()
    assert updated_template.name == "Updated Template Name"
    assert len(updated_template.template_meals) == 1
    assert updated_template.template_meals[0].meal_time == "Breakfast"
    assert updated_template.template_meals[0].meal_id == meal1.id

def test_delete_template(client, session):
    template = Template(name="Delete Template")
    session.add(template)
    session.commit()
    session.refresh(template)

    response = client.delete(f"/templates/{template.id}")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    deleted_template = session.query(Template).filter(Template.id == template.id).first()
    assert deleted_template is None

def test_use_template(client, session):
    food1 = Food(name="Banana", serving_size="1", serving_unit="medium", calories=105, protein=1.3, carbs=27, fat=0.4)
    session.add(food1)
    session.commit()
    session.refresh(food1)

    meal1 = Meal(name="Banana Smoothie", meal_type="breakfast", meal_time="Breakfast")
    session.add(meal1)
    session.commit()
    session.refresh(meal1)

    template = Template(name="Use Template")
    session.add(template)
    session.commit()
    session.refresh(template)

    template_meal = TemplateMeal(template_id=template.id, meal_id=meal1.id, meal_time="Breakfast")
    session.add(template_meal)
    session.commit()

    response = client.post(
        f"/templates/{template.id}/use",
        data={"person": "Sarah", "start_date": "2025-01-01"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Template applied successfully"}