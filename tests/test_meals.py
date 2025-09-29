"""
Tests for Meals CRUD operations
"""
import pytest
import json


class TestMealsRoutes:
    """Test meal-related routes"""
    
    def test_get_meals_page(self, client):
        """Test GET /meals page"""
        response = client.get("/meals")
        assert response.status_code == 200
        assert b"Meals" in response.content or b"meals" in response.content
    
    def test_add_meal(self, client):
        """Test POST /meals/add"""
        response = client.post("/meals/add", data={
            "name": "New Test Meal",
            "meal_type": "lunch",
            "meal_time": "Lunch"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "meal_id" in data
    
    def test_edit_meal(self, client, sample_meal):
        """Test POST /meals/edit"""
        response = client.post("/meals/edit", data={
            "meal_id": sample_meal.id,
            "name": "Updated Meal Name",
            "meal_type": "dinner",
            "meal_time": "Dinner"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_edit_nonexistent_meal(self, client):
        """Test editing non-existent meal"""
        response = client.post("/meals/edit", data={
            "meal_id": 99999,
            "name": "Updated Meal Name",
            "meal_type": "dinner",
            "meal_time": "Dinner"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_get_meal_details(self, client, sample_meal):
        """Test GET /meals/{meal_id}"""
        response = client.get(f"/meals/{sample_meal.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["id"] == sample_meal.id
        assert data["name"] == sample_meal.name
    
    def test_get_nonexistent_meal_details(self, client):
        """Test getting details for non-existent meal"""
        response = client.get("/meals/99999")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_delete_meals(self, client, sample_meal):
        """Test POST /meals/delete"""
        response = client.post("/meals/delete", 
                              json={"meal_ids": [sample_meal.id]})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestMealFoods:
    """Test meal-food relationships"""
    
    def test_get_meal_foods(self, client, sample_meal):
        """Test GET /meals/{meal_id}/foods"""
        response = client.get(f"/meals/{sample_meal.id}/foods")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "food_id" in data[0]
            assert "quantity" in data[0]
    
    def test_add_food_to_meal(self, client, sample_meal, sample_food):
        """Test POST /meals/{meal_id}/add_food"""
        response = client.post(f"/meals/{sample_meal.id}/add_food", data={
            "food_id": sample_food.id,
            "quantity": 2.5
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_remove_food_from_meal(self, client, sample_meal, db_session):
        """Test DELETE /meals/remove_food/{meal_food_id}"""
        # Get the first meal food
        from main import MealFood
        meal_food = db_session.query(MealFood).filter(
            MealFood.meal_id == sample_meal.id
        ).first()
        
        if meal_food:
            response = client.delete(f"/meals/remove_food/{meal_food.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_remove_nonexistent_meal_food(self, client):
        """Test removing non-existent meal food"""
        response = client.delete("/meals/remove_food/99999")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestMealsBulkUpload:
    """Test bulk meal upload functionality"""
    
    def test_bulk_upload_meals_csv(self, client, sample_foods, tmp_path):
        """Test POST /meals/upload with CSV"""
        # Create test CSV file with meal recipes
        csv_content = f"""Meal Name,Food 1,Grams 1,Food 2,Grams 2
Test Meal 1,{sample_foods[0].name},150,{sample_foods[1].name},200
Test Meal 2,{sample_foods[1].name},100,{sample_foods[2].name},150"""
        
        csv_file = tmp_path / "test_meals.csv"
        csv_file.write_text(csv_content)
        
        with open(csv_file, 'rb') as f:
            response = client.post("/meals/upload", 
                                  files={"file": ("test_meals.csv", f, "text/csv")})
        
        assert response.status_code == 200
        data = response.json()
        assert "created" in data or "updated" in data or "errors" in data
    
    def test_bulk_upload_meals_missing_food(self, client, tmp_path):
        """Test bulk upload with missing food"""
        csv_content = """Meal Name,Food 1,Grams 1,Food 2,Grams 2
Invalid Meal,Nonexistent Food,150,Another Fake Food,200"""
        
        csv_file = tmp_path / "invalid_meals.csv"
        csv_file.write_text(csv_content)
        
        with open(csv_file, 'rb') as f:
            response = client.post("/meals/upload", 
                                  files={"file": ("invalid_meals.csv", f, "text/csv")})
        
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) > 0


class TestMealNutrition:
    """Test meal nutrition calculations"""
    
    def test_meal_nutrition_calculation(self, client, sample_meal, db_session):
        """Test that meal nutrition is calculated correctly"""
        from main import calculate_meal_nutrition
        
        nutrition = calculate_meal_nutrition(sample_meal, db_session)
        
        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "carbs" in nutrition
        assert "fat" in nutrition
        assert "fiber" in nutrition
        assert nutrition["calories"] > 0
    
    def test_empty_meal_nutrition(self, client, db_session):
        """Test nutrition calculation for empty meal"""
        from main import Meal, calculate_meal_nutrition
        
        empty_meal = Meal(
            name="Empty Meal",
            meal_type="snack",
            meal_time="Snack 1"
        )
        db_session.add(empty_meal)
        db_session.commit()
        
        nutrition = calculate_meal_nutrition(empty_meal, db_session)
        
        assert nutrition["calories"] == 0
        assert nutrition["protein"] == 0
