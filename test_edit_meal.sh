#!/bin/bash

# Curl-based test script for exercising the Edit Tracked Meal modal functionality.
# This script demonstrates how to:
# 1. Update the quantity of a food in a tracked meal.
# 2. Remove a food from a tracked meal.
# 3. Add a new food to a tracked meal.
#
# Prerequisites:
# - The FastAPI server must be running (e.g., uvicorn main:app --reload --port 8000).
# - You need a valid tracked_meal_id (from the database or API response).
# - You need valid food_id(s) (from the foods table or API).
#
# How to find IDs:
# 1. tracked_meal_id: Use the GET /tracker endpoint or query the database:
#    SELECT id FROM tracked_meal WHERE tracked_day_id = (SELECT id FROM tracked_day WHERE person = 'Sarah' AND date = '2025-10-02');
# 2. food_id: Use the GET /api/foods endpoint or query:
#    SELECT id, name FROM food LIMIT 5;
#
# Base URL (adjust if your server is on a different host/port)
BASE_URL="http://localhost:8999"

# Set your specific IDs here (replace with actual values)
TRACKED_MEAL_ID=1  # Example: Replace with your tracked_meal_id
FOOD_ID_TO_UPDATE=1  # Example: Food to update quantity
FOOD_ID_TO_REMOVE=2  # Example: Food to remove
FOOD_ID_TO_ADD=3     # Example: New food to add

echo "Testing Edit Tracked Meal functionality..."
echo "Using tracked_meal_id: $TRACKED_MEAL_ID"
echo ""

# 1. Update Quantity of a Food
echo "1. Updating quantity of food $FOOD_ID_TO_UPDATE to 200g..."
curl -X POST "$BASE_URL/tracker/update_tracked_meal_foods" \
  -H "Content-Type: application/json" \
  -d '{
    "tracked_meal_id": '"$TRACKED_MEAL_ID"',
    "foods": [
      {
        "food_id": '"$FOOD_ID_TO_UPDATE"',
        "grams": 200.0
      }
    ],
    "removed_food_ids": []
  }'

echo ""
echo "Expected response: {\"status\": \"success\"}"
echo ""

# Verify the update (optional: GET the foods)
echo "2. Verifying updated foods..."
curl -X GET "$BASE_URL/tracker/get_tracked_meal_foods/$TRACKED_MEAL_ID"

echo ""
echo "----------------------------------------"
echo ""

# 3. Remove a Food
echo "3. Removing food $FOOD_ID_TO_REMOVE..."
curl -X POST "$BASE_URL/tracker/update_tracked_meal_foods" \
  -H "Content-Type: application/json" \
  -d '{
    "tracked_meal_id": '"$TRACKED_MEAL_ID"',
    "foods": [],
    "removed_food_ids": ['"$FOOD_ID_TO_REMOVE"']
  }'

echo ""
echo "Expected response: {\"status\": \"success\"}"
echo ""

# Verify removal
echo "4. Verifying removed foods..."
curl -X GET "$BASE_URL/tracker/get_tracked_meal_foods/$TRACKED_MEAL_ID"

echo ""
echo "----------------------------------------"
echo ""

# 5. Add a New Food
echo "5. Adding new food $FOOD_ID_TO_ADD with 150g..."
curl -X POST "$BASE_URL/tracker/add_food_to_tracked_meal" \
  -H "Content-Type: application/json" \
  -d '{
    "tracked_meal_id": '"$TRACKED_MEAL_ID"',
    "food_id": '"$FOOD_ID_TO_ADD"',
    "grams": 150.0
  }'

echo ""
echo "Expected response: {\"status\": \"success\"}"
echo ""

# Verify addition
echo "6. Verifying added foods..."
curl -X GET "$BASE_URL/tracker/get_tracked_meal_foods/$TRACKED_MEAL_ID"

echo ""
echo "Script completed. Check responses for success/error messages."
echo "Note: After running, the tracked day will be marked as modified."