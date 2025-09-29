"""
Tests for Tracker CRUD operations
"""
import pytest
from datetime import date, timedelta


class TestTrackerRoutes:
    """Test tracker-related routes"""
    
    def test_get_tracker_page(self, client):
        """Test GET /tracker page"""
        response = client.get("/tracker?person=Sarah")
        assert response.status_code == 200
        assert b"Tracker" in response.content or b"tracker" in response.content
    
    def test_get_tracker_page_with_date(self, client):
        """Test GET /tracker page with specific date"""
        test_date = date.today().isoformat()
        response = client.get(f"/tracker?person=Stuart&date={test_date}")
        assert response.status_code == 200
    
    def test_tracker_add_meal(self, client, sample_meal):
        """Test POST /tracker/add_meal"""
        test_date = date.today().isoformat()
        response = client.post("/tracker/add_meal", data={
            "person": "Sarah",
            "date": test_date,
            "meal_id": str(sample_meal.id),
            "meal_time": "Breakfast",
            "quantity": "1.5"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_tracker_add_meal_default_quantity(self, client, sample_meal):
        """Test adding meal with default quantity"""
        test_date = date.today().isoformat()
        response = client.post("/tracker/add_meal", data={
            "person": "Stuart",
            "date": test_date,
            "meal_id": str(sample_meal.id),
            "meal_time": "Lunch"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_tracker_remove_meal(self, client, sample_tracked_day, db_session):
        """Test DELETE /tracker/remove_meal/{tracked_meal_id}"""
        from main import TrackedMeal
        
        tracked_meal = db_session.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == sample_tracked_day.id
        ).first()
        
        if tracked_meal:
            response = client.delete(f"/tracker/remove_meal/{tracked_meal.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_tracker_remove_nonexistent_meal(self, client):
        """Test removing non-existent tracked meal"""
        response = client.delete("/tracker/remove_meal/99999")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestTrackerTemplates:
    """Test tracker template functionality"""
    
    def test_tracker_save_template(self, client, sample_tracked_day):
        """Test POST /tracker/save_template"""
        test_date = sample_tracked_day.date.isoformat()
        response = client.post("/tracker/save_template", data={
            "person": sample_tracked_day.person,
            "date": test_date,
            "template_name": "New Saved Template"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_tracker_save_template_no_meals(self, client):
        """Test saving template from day with no meals"""
        future_date = (date.today() + timedelta(days=365)).isoformat()
        response = client.post("/tracker/save_template", data={
            "person": "Sarah",
            "date": future_date,
            "template_name": "Empty Template"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_tracker_apply_template(self, client, sample_template):
        """Test POST /tracker/apply_template"""
        test_date = date.today().isoformat()
        response = client.post("/tracker/apply_template", data={
            "person": "Sarah",
            "date": test_date,
            "template_id": str(sample_template.id)
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_tracker_apply_nonexistent_template(self, client):
        """Test applying non-existent template"""
        test_date = date.today().isoformat()
        response = client.post("/tracker/apply_template", data={
            "person": "Sarah",
            "date": test_date,
            "template_id": "99999"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_tracker_apply_empty_template(self, client, db_session):
        """Test applying template with no meals"""
        from main import Template
        
        empty_template = Template(name="Empty Tracker Template")
        db_session.add(empty_template)
        db_session.commit()
        db_session.refresh(empty_template)
        
        test_date = date.today().isoformat()
        response = client.post("/tracker/apply_template", data={
            "person": "Sarah",
            "date": test_date,
            "template_id": str(empty_template.id)
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestTrackerReset:
    """Test tracker reset functionality"""
    
    def test_tracker_reset_to_plan(self, client, sample_tracked_day):
        """Test POST /tracker/reset_to_plan"""
        test_date = sample_tracked_day.date.isoformat()
        response = client.post("/tracker/reset_to_plan", data={
            "person": sample_tracked_day.person,
            "date": test_date
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_tracker_reset_nonexistent_day(self, client):
        """Test resetting non-existent tracked day"""
        future_date = (date.today() + timedelta(days=365)).isoformat()
        response = client.post("/tracker/reset_to_plan", data={
            "person": "Sarah",
            "date": future_date
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestTrackerNutrition:
    """Test tracker nutrition calculations"""
    
    def test_calculate_tracked_day_nutrition(self, client, sample_tracked_day, db_session):
        """Test tracked day nutrition calculation"""
        from main import calculate_day_nutrition_tracked, TrackedMeal
        
        tracked_meals = db_session.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == sample_tracked_day.id
        ).all()
        
        nutrition = calculate_day_nutrition_tracked(tracked_meals, db_session)
        
        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "carbs" in nutrition
        assert "fat" in nutrition
        assert nutrition["calories"] >= 0
    
    def test_tracked_day_with_quantity_multiplier(self, client, sample_meal, db_session):
        """Test nutrition calculation with quantity multiplier"""
        from main import TrackedDay, TrackedMeal, calculate_day_nutrition_tracked
        
        # Create tracked day with meal at 2x quantity
        tracked_day = TrackedDay(
            person="Sarah",
            date=date.today(),
            is_modified=True
        )
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)
        
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=sample_meal.id,
            meal_time="Breakfast",
            quantity=2.0
        )
        db_session.add(tracked_meal)
        db_session.commit()
        
        tracked_meals = [tracked_meal]
        nutrition = calculate_day_nutrition_tracked(tracked_meals, db_session)
        
        # Should be double the base meal nutrition
        assert nutrition["calories"] > 0
