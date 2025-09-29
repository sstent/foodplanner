# Plan for Pytest of Details Tab

This plan outlines the steps to create a comprehensive pytest for the "details" tab in the Food Planner application.

## Objective
The goal is to create a suite of tests that verify the functionality of the `/detailed` route, ensuring it correctly handles both plan-based and template-based views, as well as invalid inputs.

## File to be Created
- `tests/test_detailed.py`

## Test Cases

### 1. Test with `plan_date`
- **Description**: This test will check the `/detailed` route when a valid `plan_date` is provided.
- **Steps**:
    1. Create mock data: a `Food`, a `Meal`, a `MealFood`, and a `Plan` for a specific date.
    2. Send a GET request to `/detailed` with the `person` and `plan_date` as query parameters.
    3. Assert that the response status code is 200.
    4. Assert that the response contains the correct data for the plan.

### 2. Test with `template_id`
- **Description**: This test will check the `/detailed` route when a valid `template_id` is provided.
- **Steps**:
    1. Create mock data: a `Food`, a `Meal`, a `Template`, and a `TemplateMeal`.
    2. Send a GET request to `/detailed` with the `template_id` as a query parameter.
    3. Assert that the response status code is 200.
    4. Assert that the response contains the correct data for the template.

### 3. Test with Invalid `plan_date`
- **Description**: This test will ensure the route handles an invalid `plan_date` gracefully.
- **Steps**:
    1. Send a GET request to `/detailed` with a non-existent `plan_date`.
    2. Assert that the response status code is 200 (as the page should still render).
    3. Assert that the response contains a message indicating that no plan was found.

### 4. Test with Invalid `template_id`
- **Description**: This test will ensure the route handles an invalid `template_id` gracefully.
- **Steps**:
    1. Send a GET request to `/detailed` with a non-existent `template_id`.
    2. Assert that the response status code is 200.
    3. Assert that the response contains a message indicating that the template was not found.

## Implementation Details

The `tests/test_detailed.py` file should include:
- Imports for `pytest`, `TestClient`, and the necessary models from `main.py`.
- A `TestClient` instance for making requests to the application.
- Fixtures to set up and tear down the test database for each test function to ensure test isolation.

This plan provides a clear path for a developer to implement the required tests.