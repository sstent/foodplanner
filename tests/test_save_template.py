import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.database import TrackedDay, TrackedMeal, Meal, Food, Template, TemplateMeal

@pytest.fixture
def setup_tracker_data(db_session: Session, sample_food: Food):
    """Set up tracked day and meals for testing template saving."""
    person_name = "Test Person"
    today = date.today()

    # Create a TrackedDay
    tracked_day = TrackedDay(person=person_name, date=today)
    db_session.add(tracked_day)
    db_session.commit()
    db_session.refresh(tracked_day)

    # Create a Meal
    meal = Meal(name="Test Meal", meal_type="breakfast", meal_time="08:00")
    db_session.add(meal)
    db_session.commit()
    db_session.refresh(meal)

    # Link food to meal (assuming MealFood is handled by Meal creation or omitted for simplicity here)
    # For now, let's assume sample_meal already has food linked or we don't need to test food details
    # If detailed food linking is needed, we'd add MealFood entries here.

    # Create a TrackedMeal
    tracked_meal = TrackedMeal(tracked_day_id=tracked_day.id, meal_id=meal.id, meal_time="08:00")
    db_session.add(tracked_meal)
    db_session.commit()
    db_session.refresh(tracked_meal)

    return {"person": person_name, "date": today, "tracked_day_id": tracked_day.id, "meal_id": meal.id}

def test_save_template_no_meals_found(client: TestClient, db_session: Session, setup_tracker_data: dict):
    """
    Test that saving a template fails when no meals are found for the tracked day.
    """
    person = setup_tracker_data["person"]
    test_date = setup_tracker_data["date"]
    template_name = "No Meals Template"

    # Clear meals for the tracked day created by the fixture
    tracked_day = db_session.query(TrackedDay).filter_by(person=person, date=test_date).first()
    if tracked_day:
        db_session.query(TrackedMeal).filter_by(tracked_day_id=tracked_day.id).delete()
        db_session.commit()

    response = client.post(
        "/tracker/save_template",
        data={
            "person": person,
            "date": test_date.isoformat(),
            "template_name": template_name
        }
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "error"
    assert "No meals found on this day to save as a template." in response_data["message"]

    # Verify that no template was created
    templates = db_session.query(Template).filter(Template.name == template_name).all()
    assert len(templates) == 0

def test_save_template_success(client: TestClient, db_session: Session, setup_tracker_data: dict):
    """
    Test the "Save as Template" functionality after the fix is applied.
    This test is expected to pass and create a new template and template meals.
    """
    person = setup_tracker_data["person"]
    test_date = setup_tracker_data["date"]
    template_name = "Successful Template"

    response = client.post(
        "/tracker/save_template",
        data={
            "person": person,
            "date": test_date.isoformat(),
            "template_name": template_name
        }
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["message"] == "Template saved successfully."

    # Verify that the template was created
    new_template = db_session.query(Template).filter(Template.name == template_name).first()
    assert new_template is not None
    assert new_template.name == template_name

    # Verify that template meals were created
    template_meals = db_session.query(TemplateMeal).filter(TemplateMeal.template_id == new_template.id).all()
    assert len(template_meals) > 0
    assert template_meals[0].meal_id == setup_tracker_data["meal_id"]

def test_save_template_duplicate_name(client: TestClient, db_session: Session, setup_tracker_data: dict):
    """
    Test saving a template with a duplicate name, expecting an error.
    """
    person = setup_tracker_data["person"]
    test_date = setup_tracker_data["date"]
    template_name = "Duplicate Template"

    # First successful save
    response = client.post(
        "/tracker/save_template",
        data={
            "person": person,
            "date": test_date.isoformat(),
            "template_name": template_name
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Attempt to save again with the same name
    response_duplicate = client.post(
        "/tracker/save_template",
        data={
            "person": person,
            "date": test_date.isoformat(),
            "template_name": template_name
        }
    )
    assert response_duplicate.status_code == 200
    response_data = response_duplicate.json()
    assert response_data["status"] == "error"
    assert f"Template name '{template_name}' already exists." in response_data["message"]