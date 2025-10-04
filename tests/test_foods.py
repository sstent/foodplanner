"""
Tests for Foods CRUD operations
"""
import pytest
from datetime import date
import json


class TestFoodsRoutes:
    """Test food-related routes"""
    
    def test_get_foods_page(self, client):
        """Test GET /foods page"""
        response = client.get("/foods")
        assert response.status_code == 200
        assert b"Foods" in response.content or b"foods" in response.content
    
    def test_add_food(self, client):
        """Test POST /foods/add"""
        response = client.post("/foods/add", data={
            "name": "New Test Food",
            "serving_size": "100",
            "serving_unit": "g",
            "calories": 150.0,
            "protein": 8.0,
            "carbs": 15.0,
            "fat": 3.0,
            "fiber": 2.0,
            "sugar": 1.0,
            "sodium": 75.0,
            "calcium": 30.0,
            "source": "manual",
            "brand": "Test Brand"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_add_food_duplicate_name(self, client, sample_food):
        """Test adding food with duplicate name"""
        response = client.post("/foods/add", data={
            "name": sample_food.name,
            "serving_size": "100",
            "serving_unit": "g",
            "calories": 150.0,
            "protein": 8.0,
            "carbs": 15.0,
            "fat": 3.0,
            "fiber": 2.0,
            "sugar": 1.0,
            "sodium": 75.0,
            "calcium": 30.0,
            "source": "manual",
            "brand": "Test Brand"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_edit_food(self, client, sample_food):
        """Test POST /foods/edit"""
        response = client.post("/foods/edit", data={
            "food_id": sample_food.id,
            "name": "Updated Food Name",
            "serving_size": "150",
            "serving_unit": "g",
            "calories": 250.0,
            "protein": 12.0,
            "carbs": 25.0,
            "fat": 6.0,
            "fiber": 3.0,
            "sugar": 4.0,
            "sodium": 120.0,
            "calcium": 60.0,
            "source": "manual",
            "brand": "Updated Brand"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_edit_nonexistent_food(self, client):
        """Test editing non-existent food"""
        response = client.post("/foods/edit", data={
            "food_id": 99999,
            "name": "Updated Food Name",
            "serving_size": "150",
            "serving_unit": "g",
            "calories": 250.0,
            "protein": 12.0,
            "carbs": 25.0,
            "fat": 6.0,
            "fiber": 3.0,
            "sugar": 4.0,
            "sodium": 120.0,
            "calcium": 60.0,
            "source": "manual",
            "brand": "Updated Brand"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_delete_foods(self, client, sample_foods):
        """Test POST /foods/delete"""
        food_ids = [food.id for food in sample_foods[:2]]
        response = client.post("/foods/delete", 
                              json={"food_ids": food_ids})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_search_openfoodfacts(self, client):
        """Test GET /foods/search_openfoodfacts"""
        # This test requires OpenFoodFacts SDK to be installed
        response = client.get("/foods/search_openfoodfacts?query=apple&limit=5")
        assert response.status_code == 200
        data = response.json()
        # Should either succeed or fail gracefully if module not installed
        assert "status" in data

    def test_search_openfoodfacts_results(self, client):
        """Test GET /foods/search_openfoodfacts returns actual results"""
        response = client.get("/foods/search_openfoodfacts?query=yogurt&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data
        assert len(data["results"]) > 0
        assert "name" in data["results"][0]

class TestFoodsBulkUpload:
    """Test bulk food upload functionality"""
    
    def test_bulk_upload_foods_csv(self, client, tmp_path):
        """Test POST /foods/upload with CSV"""
        # Create test CSV file
        csv_content = """ID,Brand,Serving (g),Calories,Protein (g),Carbohydrate (g),Fat (g),Fiber (g),Sugar (g),Sodium (mg),Calcium (mg)
Apple,Generic,100,52,0.3,14,0.2,2.4,10,1,6
Banana,Generic,100,89,1.1,23,0.3,2.6,12,1,5"""
        
        csv_file = tmp_path / "test_foods.csv"
        csv_file.write_text(csv_content)
        
        with open(csv_file, 'rb') as f:
            response = client.post("/foods/upload", 
                                  files={"file": ("test_foods.csv", f, "text/csv")})
        
        assert response.status_code == 200
        data = response.json()
        assert "created" in data or "updated" in data
    
    def test_bulk_upload_invalid_csv(self, client, tmp_path):
        """Test bulk upload with invalid CSV"""
        csv_content = """Invalid,CSV,Format
1,2,3"""
        
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text(csv_content)
        
        with open(csv_file, 'rb') as f:
            response = client.post("/foods/upload", 
                                  files={"file": ("invalid.csv", f, "text/csv")})
        
        assert response.status_code == 200
        data = response.json()
        # Should handle errors gracefully
        assert "status" in data or "errors" in data


class TestOpenFoodFacts:
    """Test OpenFoodFacts integration"""
    
    def test_add_openfoodfacts_food(self, client):
        """Test POST /foods/add_openfoodfacts"""
        response = client.post("/foods/add_openfoodfacts", data={
            "name": "OpenFoodFacts Test Food",
            "serving_size": "100",
            "serving_unit": "g",
            "calories": 180.0,
            "protein": 7.0,
            "carbs": 18.0,
            "fat": 4.0,
            "fiber": 2.5,
            "sugar": 3.5,
            "sodium": 90.0,
            "calcium": 40.0,
            "openfoodfacts_id": "12345678",
            "brand": "OFF Brand",
            "categories": "test,food"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_openfoodfacts_product(self, client):
        """Test GET /foods/get_openfoodfacts_product/{barcode}"""
        # Test with a well-known barcode (Nutella)
        response = client.get("/foods/get_openfoodfacts_product/3017620422003")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_openfoodfacts_by_category(self, client):
        """Test GET /foods/openfoodfacts_by_category"""
        response = client.get("/foods/openfoodfacts_by_category?category=beverages&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
