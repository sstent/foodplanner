"""
Tests for Tracker CRUD operations
"""
import pytest
from datetime import date, timedelta
from app.database import (
    TrackedDay, TrackedMeal, TrackedMealFood, Meal, MealFood, Food,
    Template, calculate_day_nutrition_tracked
)


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


class TestTrackerView:
    """Test tracker view rendering"""
    
    def test_tracker_page_shows_food_breakdown(self, client, sample_meal, sample_food, db_session):
        """Test that tracker page shows food breakdown for tracked meals"""
        
        # Create sample tracked day and meal
        tracked_day = TrackedDay(person="Sarah", date=date.today(), is_modified=True)
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)
        
        # Add the meal to tracker (assuming meal has the food)
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=sample_meal.id,
            meal_time="Breakfast",
            quantity=1.0
        )
        db_session.add(tracked_meal)
        db_session.commit()
        
        # Get tracker page
        response = client.get(f"/tracker?person=Sarah")
        assert response.status_code == 200
        
        # Check if food name appears in the response (breakdown should show it)
        assert sample_food.name.encode() in response.content


class TestTrackerEdit:
    """Test editing tracked meals"""
    
    def test_update_tracked_food_quantity(self, client, sample_meal, sample_food, db_session):
        """Test updating quantity of a custom food in a tracked meal"""
        
        # Create sample tracked day and meal
        tracked_day = TrackedDay(person="Sarah", date=date.today(), is_modified=True)
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)
        
        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=sample_meal.id,
            meal_time="Breakfast",
            quantity=1.0
        )
        db_session.add(tracked_meal)
        db_session.commit()
        db_session.refresh(tracked_meal)
        
        # Add a custom tracked food
        tracked_food = TrackedMealFood(
            tracked_meal_id=tracked_meal.id,
            food_id=sample_food.id,
            quantity=2.0,
            is_override=True
        )
        db_session.add(tracked_food)
        db_session.commit()
        db_session.refresh(tracked_food)
        
        original_quantity = tracked_food.quantity
        
        # Update the food quantity via API
        response = client.post("/tracker/update_tracked_food", json={
            "tracked_food_id": tracked_food.id,
            "quantity": 3.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
        # Verify the update
        db_session.commit()
        updated_food = db_session.query(TrackedMealFood).get(tracked_food.id)
        assert updated_food.quantity == 3.0
        assert updated_food.quantity != original_quantity


class TestTrackerSaveAsNewMeal:
    """Test saving an edited tracked meal as a new meal"""

    def test_save_as_new_meal(self, client, sample_meal, sample_food, db_session):
        """Test POST /tracker/save_as_new_meal"""
        
        # Create a tracked day and meal with custom foods
        tracked_day = TrackedDay(person="Sarah", date=date.today(), is_modified=True)
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)

        tracked_meal = TrackedMeal(
            tracked_day_id=tracked_day.id,
            meal_id=sample_meal.id,
            meal_time="Breakfast",
            quantity=1.0
        )
        db_session.add(tracked_meal)
        db_session.commit()
        db_session.refresh(tracked_meal)

        # Add a custom food to the tracked meal
        tracked_food = TrackedMealFood(
            tracked_meal_id=tracked_meal.id,
            food_id=sample_food.id,
            quantity=2.5,
            is_override=False # This is an addition, not an override for this test
        )
        db_session.add(tracked_food)
        db_session.commit()
        db_session.refresh(tracked_food)

        new_meal_name = "My Custom Breakfast"
        
        response = client.post("/tracker/save_as_new_meal", json={
            "tracked_meal_id": tracked_meal.id,
            "new_meal_name": new_meal_name,
            "foods": [
                {"food_id": sample_food.id, "quantity": 3.0}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "new_meal_id" in data

        # Verify a new meal was created
        new_meal = db_session.query(Meal).filter(Meal.name == new_meal_name).first()
        assert new_meal is not None
        assert len(new_meal.meal_foods) == 1 # Only the custom food should be here

        # Verify the original tracked meal now points to the new meal
        db_session.commit()
        updated_tracked_meal = db_session.query(TrackedMeal).get(tracked_meal.id)
        assert updated_tracked_meal.meal_id == new_meal.id
        assert len(updated_tracked_meal.tracked_foods) == 0 # Custom foods should be moved to the new meal


class TestTrackerAddFood:
    """Test adding a single food directly to the tracker"""

    def test_add_food_to_tracker(self, client, sample_food, db_session):
        """Test POST /tracker/add_food"""
        
        # Create a tracked day
        tracked_day = TrackedDay(person="Sarah", date=date.today(), is_modified=False)
        db_session.add(tracked_day)
        db_session.commit()
        db_session.refresh(tracked_day)

        # Add food directly to tracker
        response = client.post("/tracker/add_food", json={
            "person": "Sarah",
            "date": date.today().isoformat(),
            "food_id": sample_food.id,
            "quantity": 100.0,
            "meal_time": "Snack 1"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify that a new tracked meal was created with the food
        tracked_meals = db_session.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day.id,
            TrackedMeal.meal_time == "Snack 1"
        ).all()
        assert len(tracked_meals) == 1
        
        tracked_meal = tracked_meals[0]
        assert tracked_meal.meal.name == sample_food.name # The meal name should be the food name
        assert tracked_meal.quantity == 1.0 # The meal quantity should be 1.0

        # Verify the food is in the tracked meal's foods
        assert len(tracked_meal.meal.meal_foods) == 1
        assert tracked_meal.meal.meal_foods[0].food_id == sample_food.id
        assert tracked_meal.meal.meal_foods[0].quantity == 100.0
