"""
Tests for Plans CRUD operations
"""
import pytest
from datetime import date, timedelta


class TestPlansRoutes:
    """Test plan-related routes"""
    
    def test_get_plan_page(self, client):
        """Test GET /plan page"""
        response = client.get("/plan?person=Sarah")
        assert response.status_code == 200
        assert b"Plan" in response.content or b"plan" in response.content
    
    def test_get_plan_page_with_date(self, client):
        """Test GET /plan page with specific date"""
        test_date = date.today().isoformat()
        response = client.get(f"/plan?person=Stuart&week_start_date={test_date}")
        assert response.status_code == 200
    
    def test_add_to_plan(self, client, sample_meal):
        """Test POST /plan/add"""
        test_date = date.today().isoformat()
        response = client.post("/plan/add", data={
            "person": "Sarah",
            "plan_date": test_date,
            "meal_id": str(sample_meal.id),
            "meal_time": "Breakfast"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_add_to_plan_missing_fields(self, client):
        """Test adding to plan with missing fields"""
        response = client.post("/plan/add", data={
            "person": "Sarah"
            # Missing plan_date, meal_id, meal_time
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_add_to_plan_invalid_meal(self, client):
        """Test adding non-existent meal to plan"""
        test_date = date.today().isoformat()
        response = client.post("/plan/add", data={
            "person": "Sarah",
            "plan_date": test_date,
            "meal_id": "99999",
            "meal_time": "Breakfast"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_get_day_plan(self, client, sample_plan):
        """Test GET /plan/{person}/{date}"""
        test_date = sample_plan.date.isoformat()
        response = client.get(f"/plan/{sample_plan.person}/{test_date}")
        assert response.status_code == 200
        data = response.json()
        assert "meals" in data
        assert "day_totals" in data
        assert isinstance(data["meals"], list)
    
    def test_get_day_plan_empty(self, client):
        """Test getting plan for day with no meals"""
        future_date = (date.today() + timedelta(days=365)).isoformat()
        response = client.get(f"/plan/Sarah/{future_date}")
        assert response.status_code == 200
        data = response.json()
        assert "meals" in data
        assert len(data["meals"]) == 0
    
    def test_update_day_plan(self, client, sample_meal):
        """Test POST /plan/update_day"""
        test_date = date.today().isoformat()
        response = client.post("/plan/update_day", data={
            "person": "Stuart",
            "date": test_date,
            "meal_ids": f"{sample_meal.id}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_update_day_plan_multiple_meals(self, client, sample_meal, sample_foods, db_session):
        """Test updating plan with multiple meals"""
        from main import Meal
        
        # Create another meal
        meal2 = Meal(name="Second Meal", meal_type="lunch", meal_time="Lunch")
        db_session.add(meal2)
        db_session.commit()
        db_session.refresh(meal2)
        
        test_date = date.today().isoformat()
        response = client.post("/plan/update_day", data={
            "person": "Sarah",
            "date": test_date,
            "meal_ids": f"{sample_meal.id},{meal2.id}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_remove_from_plan(self, client, sample_plan):
        """Test DELETE /plan/{plan_id}"""
        response = client.delete(f"/plan/{sample_plan.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_remove_nonexistent_plan(self, client):
        """Test removing non-existent plan"""
        response = client.delete("/plan/99999")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestPlanNavigation:
    """Test plan navigation functionality"""
    
    def test_plan_week_navigation(self, client, sample_meal):
        """Test navigating between weeks"""
        # Get current week
        response = client.get("/plan?person=Sarah")
        assert response.status_code == 200
        
        # Add meal to today
        test_date = date.today().isoformat()
        client.post("/plan/add", data={
            "person": "Sarah",
            "plan_date": test_date,
            "meal_id": str(sample_meal.id),
            "meal_time": "Breakfast"
        })
        
        # Get next week
        next_week = (date.today() + timedelta(days=7)).isoformat()
        response = client.get(f"/plan?person=Sarah&week_start_date={next_week}")
        assert response.status_code == 200
        
        # Get previous week
        prev_week = (date.today() - timedelta(days=7)).isoformat()
        response = client.get(f"/plan?person=Sarah&week_start_date={prev_week}")
        assert response.status_code == 200


class TestDayNutrition:
    """Test day nutrition calculations"""
    
    def test_calculate_day_nutrition(self, client, sample_plan, db_session):
        """Test day nutrition calculation"""
        from main import calculate_day_nutrition, Plan
        
        plans = db_session.query(Plan).filter(
            Plan.person == sample_plan.person,
            Plan.date == sample_plan.date
        ).all()
        
        nutrition = calculate_day_nutrition(plans, db_session)
        
        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "carbs" in nutrition
        assert "fat" in nutrition
        assert "protein_pct" in nutrition
        assert "carbs_pct" in nutrition
        assert "fat_pct" in nutrition
    
    def test_empty_day_nutrition(self, db_session):
        """Test nutrition calculation for day with no meals"""
        from main import calculate_day_nutrition
        
        nutrition = calculate_day_nutrition([], db_session)
        
        assert nutrition["calories"] == 0
        assert nutrition["protein"] == 0
        assert nutrition["protein_pct"] == 0
