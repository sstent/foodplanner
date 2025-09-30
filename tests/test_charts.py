import pytest
from datetime import date, timedelta
from app.database import TrackedDay, TrackedMeal, Meal, MealFood, Food, calculate_day_nutrition_tracked
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def sample_chart_data(db_session):
    """Create sample tracked data for chart testing"""
    # Create sample food
    food = Food(
        name="Sample Food",
        serving_size="100g",
        serving_unit="g",
        calories=100.0,
        protein=10.0,
        carbs=20.0,
        fat=5.0
    )
    db_session.add(food)
    db_session.commit()
    db_session.refresh(food)
    
    # Create sample meal
    meal = Meal(
        name="Sample Meal",
        meal_type="breakfast",
        meal_time="Breakfast"
    )
    db_session.add(meal)
    db_session.commit()
    db_session.refresh(meal)
    
    # Link meal to food
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=1.0
    )
    db_session.add(meal_food)
    db_session.commit()
    
    # Create tracked days
    person = "Sarah"
    today = date.today()
    tracked_days = []
    
    for i in range(3):  # Last 3 days
        tracked_date = today - timedelta(days=i)
        tracked_day = TrackedDay(
            person=person,
            date=tracked_date,
            is_modified=False
        )
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)
        
        # Add a tracked meal
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=meal.id,
            meal_time="Breakfast",
            quantity=1.0
        )
        db_session.add(tracked_meal)
        db_session.commit()
        
        tracked_days.append(tracked_day)
    
    return tracked_days, meal

def test_get_charts_data(client, db_session, sample_chart_data):
    """Test the charts data endpoint returns correct calorie data"""
    tracked_days, meal = sample_chart_data
    
    # Expected calories: 100 per day
    expected_data = [
        {
            "date": tracked_days[0].date.isoformat(),
            "calories": 100.0
        },
        {
            "date": tracked_days[1].date.isoformat(),
            "calories": 100.0
        },
        {
            "date": tracked_days[2].date.isoformat(),
            "calories": 100.0
        }
    ]
    
    response = client.get("/api/charts?person=Sarah&days=3")
    assert response.status_code == 200
    data = response.json()
    
    # Sort by date descending
    data_sorted = sorted(data, key=lambda x: x["date"], reverse=True)
    assert data_sorted == expected_data

def test_get_charts_data_default_days(client, db_session, sample_chart_data):
    """Test default days parameter"""
    response = client.get("/api/charts?person=Sarah")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # Should return last 3 days

def test_get_charts_data_no_data(client, db_session):
    """Test endpoint when no tracked data exists"""
    response = client.get("/api/charts?person=Sarah&days=7")
    assert response.status_code == 200
    data = response.json()
    assert data == []  # Empty list if no data