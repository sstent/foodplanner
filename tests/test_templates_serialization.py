import pytest
from fastapi.testclient import TestClient
from main import app, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date
import os

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
from main import Base, Template, Meal, TemplateMeal
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_templates_page_renders_without_error():
    """Test that the /templates page renders without a TypeError."""
    # Create a test template and meal
    db = TestingSessionLocal()
    
    meal = Meal(name="Test Meal", meal_type="breakfast", meal_time="Breakfast")
    db.add(meal)
    db.commit()
    db.refresh(meal)
    
    template = Template(name="Test Template")
    db.add(template)
    db.commit()
    db.refresh(template)
    
    template_meal = TemplateMeal(template_id=template.id, meal_id=meal.id, meal_time="Breakfast")
    db.add(template_meal)
    db.commit()
    
    db.close()
    
    # Test the HTML page
    response = client.get("/templates")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Test the API endpoint
    response = client.get("/api/templates")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Template"
    assert len(data[0]["template_meals"]) == 1
    assert data[0]["template_meals"][0]["meal_name"] == "Test Meal"