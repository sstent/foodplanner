# Implementation Plan: Meal/Food Search & Sorting (Track: meal_food_search_20260310)

## Phase 1: Preparation and Testing
- [ ] Task: Create a new Playwright test file `tests/meal_food_search.spec.js` to verify searching and sorting in modals.
- [ ] Task: Write failing E2E tests for:
    - [ ] Modal opening and initial alphabetical sorting of Meals.
    - [ ] Real-time filtering in the "Add Meal" modal.
    - [ ] Modal opening and initial alphabetical sorting of Foods.
    - [ ] Real-time filtering (by name and brand) in the "Add Food" modal.
- [ ] Task: Run the tests and confirm they fail.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Preparation and Testing' (Protocol in workflow.md)

## Phase 2: Implement Sorting & Searching in "Add Meal" Modal
- [ ] Task: Update `templates/modals/add_meal.html` to add a search input field above the meal list.
- [ ] Task: Add a unique `data-testid` to the search input and individual list items for test reliability.
- [ ] Task: Update the backend route `app/api/routes/tracker.py` to sort the `meals` list alphabetically before passing it to the template.
- [ ] Task: Implement client-side JavaScript in `templates/modals/add_meal.html` to filter the meal list in real-time as the user types.
- [ ] Task: Verify Phase 2 with E2E tests.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Implement Sorting & Searching in Add Meal Modal' (Protocol in workflow.md)

## Phase 3: Implement Sorting & Searching in "Add Food" Modal
- [ ] Task: Update `templates/modals/add_single_food.html` (or the relevant "Add Food" modal) to add a search input field above the food list.
- [ ] Task: Add a unique `data-testid` to the search input and food list items.
- [ ] Task: Update the backend route `app/api/routes/tracker.py` to sort the `foods` list alphabetically before passing it to the template.
- [ ] Task: Implement client-side JavaScript in the "Add Food" modal to filter by both `name` and `brand` in real-time.
- [ ] Task: Verify Phase 3 with E2E tests.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Implement Sorting & Searching in Add Food Modal' (Protocol in workflow.md)

## Phase 4: Final Verification and Cleanup
- [ ] Task: Perform a final run of all tests (E2E and Backend).
- [ ] Task: Ensure code coverage for any new logic (if applicable) is >80%.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Verification and Cleanup' (Protocol in workflow.md)