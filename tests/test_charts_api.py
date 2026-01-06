
import pytest
from datetime import date, timedelta
from app.database import TrackedDay, TrackedMeal, TrackedMealFood, Meal, MealFood, Food

class TestChartsData:
    """Test charts data API"""
    
    def test_charts_api_returns_macros(self, client, sample_meal, db_session):
        """Test that /api/charts returns protein, fat, and net_carbs"""
        
        # Create a tracked day with data
        tracked_day = TrackedDay(person="Sarah", date=date.today(), is_modified=True)
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)
        
        # Add meal
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=sample_meal.id,
            meal_time="Breakfast"
        )
        db_session.add(tracked_meal)
        db_session.commit()
        
        # Fetch chart data
        response = client.get("/api/charts?person=Sarah&days=7")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        # Check fields
        item = data[0]
        assert "date" in item
        assert "calories" in item
        assert "protein" in item
        assert "fat" in item
        assert "net_carbs" in item
        
        # Check values (protein > 0 based on sample_meal)
        assert item["protein"] >= 0
        assert item["fat"] >= 0
        assert item["net_carbs"] >= 0
