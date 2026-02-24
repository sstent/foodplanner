# Implementation Plan - Meal Tracker Refactoring

This plan outlines the steps for refactoring the meal tracking system to decouple "Journal Logs" from "Cookbook Recipes," resolving database pollution and improving system structure.

## Phase 1: Preparation & Schema Updates [checkpoint: 326a82e]
- [x] Task: Create a new branch for the refactoring track.
- [x] Task: Add the 'name' column to the 'TrackedMeal' table and make 'meal_id' nullable in 'app/database.py'.
- [x] Task: Create and run an Alembic migration for the schema changes.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Preparation & Schema Updates' (Protocol in workflow.md)

## Phase 2: Logic & Calculation Updates
- [ ] Task: Write failing unit tests for 'calculate_tracked_meal_nutrition' with 'meal_id=None'.
- [ ] Task: Implement support for 'meal_id=None' in 'calculate_tracked_meal_nutrition' within 'app/database.py'.
- [ ] Task: Write failing unit tests for the refactored 'tracker_add_food' endpoint.
- [ ] Task: Refactor the 'tracker_add_food' route in 'app/api/routes/tracker.py' to use the new 'TrackedMeal' structure.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Logic & Calculation Updates' (Protocol in workflow.md)

## Phase 3: UI & Cookbook Refinement
- [ ] Task: Update the 'tracker.html' template to display 'TrackedMeal.name' for template-less logs.
- [ ] Task: Update the Meals page in 'app/api/routes/meals.py' to filter out 'single_food' and 'snapshot' types.
- [ ] Task: Write failing E2E tests for the new tracking workflow.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: UI & Cookbook Refinement' (Protocol in workflow.md)

## Phase 4: Database Migration & Cleanup
- [ ] Task: Create a Python migration script for cleaning up existing 'single_food' entries.
- [ ] Task: Run the migration script on the development PostgreSQL database.
- [ ] Task: Verify the database state and ensure no orphans remain.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Database Migration & Cleanup' (Protocol in workflow.md)
