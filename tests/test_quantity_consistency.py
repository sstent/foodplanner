import pytest

from app.database import (
    calculate_meal_nutrition,
    Food,
    Meal,
    MealFood,
)


def test_meal_nutrition_uses_grams_correctly(db_session):
    """Verify that MealFood.quantity as grams calculates nutrition correctly"""
    # Create a food: 100 cal per 100g
    food = Food(
        name="Test Food",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0,
        protein=10.0,
        carbs=20.0,
        fat=5.0
    )
    db_session.add(food)
    db_session.commit()
    
    # Create a meal with 200g of this food
    meal = Meal(name="Test Meal", meal_type="breakfast")
    db_session.add(meal)
    db_session.commit()
    
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=200.0  # 200 grams
    )
    db_session.add(meal_food)
    db_session.commit()
    
    # Calculate nutrition
    nutrition = calculate_meal_nutrition(meal, db_session)
    
    # Should be 2x the base values (200g / 100g = 2x multiplier)
    assert nutrition['calories'] == 200.0
    assert nutrition['protein'] == 20.0
    assert nutrition['carbs'] == 40.0
    assert nutrition['fat'] == 10.0


def test_fractional_servings(db_session):
    """Test that fractional grams work correctly"""
    food = Food(
        name="Test Food",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0
    )
    db_session.add(food)
    db_session.commit()
    
    meal = Meal(name="Test Meal")
    db_session.add(meal)
    db_session.commit()
    
    # Add 50g (half serving)
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=50.0
    )
    db_session.add(meal_food)
    db_session.commit()
    
    nutrition = calculate_meal_nutrition(meal, db_session)
    assert nutrition['calories'] == 50.0


def test_zero_serving_size_handling(db_session):
    """Test handling of zero serving_size - should not divide by zero"""
    food = Food(
        name="Test Food Zero Serving",
        serving_size=0.0,
        serving_unit="g",
        calories=100.0
    )
    db_session.add(food)
    db_session.commit()
    
    meal = Meal(name="Test Meal Zero")
    db_session.add(meal)
    db_session.commit()
    
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=100.0
    )
    db_session.add(meal_food)
    db_session.commit()
    
    nutrition = calculate_meal_nutrition(meal, db_session)
    # Multiplier should be 0, so no nutrition added
    assert nutrition['calories'] == 0.0


def test_small_gram_values(db_session):
    """Test very small gram values (e.g., 0.1g)"""
    food = Food(
        name="Test Food Small",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0
    )
    db_session.add(food)
    db_session.commit()
    
    meal = Meal(name="Test Meal Small")
    db_session.add(meal)
    db_session.commit()
    
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=0.1  # Very small amount
    )
    db_session.add(meal_food)
    db_session.commit()
    
    nutrition = calculate_meal_nutrition(meal, db_session)
    # Should be 0.001x multiplier
    assert nutrition['calories'] == 0.1


def test_large_gram_values(db_session):
    """Test large gram values (e.g., 10000g)"""
    food = Food(
        name="Test Food Large",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0
    )
    db_session.add(food)
    db_session.commit()
    
    meal = Meal(name="Test Meal Large")
    db_session.add(meal)
    db_session.commit()
    
    meal_food = MealFood(
        meal_id=meal.id,
        food_id=food.id,
        quantity=10000.0  # Very large amount
    )
    db_session.add(meal_food)
    db_session.commit()
    
    nutrition = calculate_meal_nutrition(meal, db_session)
    # Should be 100x multiplier
    assert nutrition['calories'] == 10000.0


def test_invalid_serving_size(db_session):
    """Test invalid/non-numeric serving_size values"""
    # First create a valid food to test with
    valid_food = Food(
        name="Test Food Valid",
        serving_size=100.0,
        serving_unit="g",
        calories=100.0
    )
    db_session.add(valid_food)
    db_session.commit()

    # Now create a meal and add the valid food
    meal = Meal(name="Test Meal Valid")
    db_session.add(meal)
    db_session.commit()

    meal_food = MealFood(
        meal_id=meal.id,
        food_id=valid_food.id,
        quantity=100.0
    )
    db_session.add(meal_food)
    db_session.commit()

    # Test that the calculation works with valid serving_size
    nutrition = calculate_meal_nutrition(meal, db_session)
    assert nutrition['calories'] == 100.0

    # Now test with None serving_size by updating the food
    valid_food.serving_size = None
    db_session.commit()

    # Recalculate - should handle None gracefully
    nutrition = calculate_meal_nutrition(meal, db_session)
    assert nutrition['calories'] == 0