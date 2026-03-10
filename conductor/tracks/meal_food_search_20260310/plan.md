# Implementation Plan: Meal/Food Search & Sorting (Track: meal_food_search_20260310)

## Phase 1: Preparation and Testing
- [x] Task: Create a new Playwright test file `tests/meal_food_search.spec.js` to verify searching and sorting in modals.
- [x] Task: Write failing E2E tests for:
    - [x] Modal opening and initial alphabetical sorting of Meals.
    - [x] Real-time filtering in the "Add Meal" modal.
    - [x] Modal opening and initial alphabetical sorting of Foods.
    - [x] Real-time filtering (by name and brand) in the "Add Food" modal.
- [x] Task: Run the tests and confirm they fail.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Preparation and Testing' (Protocol in workflow.md)

## Phase 2: Implement Sorting & Searching in "Add Meal" Modal
- [x] Task: Update `templates/modals/add_meal.html` to add a search input field above the meal list.
- [x] Task: Add a unique `data-testid` to the search input and individual list items for test reliability.
- [x] Task: Update the backend route `app/api/routes/tracker.py` to sort the `meals` list alphabetically before passing it to the template.
- [x] Task: Implement client-side JavaScript in `templates/modals/add_meal.html` to filter the meal list in real-time as the user types.
- [x] Task: Verify Phase 2 with E2E tests.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Implement Sorting & Searching in Add Meal Modal' (Protocol in workflow.md)

## Phase 3: Implement Sorting & Searching in "Add Food" Modal
- [x] Task: Update `templates/modals/add_single_food.html` (or the relevant "Add Food" modal) to add a search input field above the food list.
- [x] Task: Add a unique `data-testid` to the search input and food list items.
- [x] Task: Update the backend route `app/api/routes/tracker.py` to sort the `foods` list alphabetically before passing it to the template.
- [x] Task: Implement client-side JavaScript in the "Add Food" modal to filter by both `name` and `brand` in real-time.
- [x] Task: Verify Phase 3 with E2E tests.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Implement Sorting & Searching in Add Food Modal' (Protocol in workflow.md)

## Phase 4: Final Verification and Cleanup
- [x] Task: Perform a final run of all tests (E2E and Backend).
- [x] Task: Ensure code coverage for any new logic (if applicable) is >80%.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Final Verification and Cleanup' (Protocol in workflow.md)