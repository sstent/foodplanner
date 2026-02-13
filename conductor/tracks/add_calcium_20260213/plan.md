# Implementation Plan - Add Calcium to Tracker Totals

This plan follows the Test-Driven Development (TDD) process as outlined in `conductor/workflow.md`.

## Phase 1: Infrastructure and Red Phase
- [ ] Task: Create a failing E2E test for Calcium display
    - [ ] Define a new test in `tests/calcium_display.spec.js` that navigates to the tracker and expects a "Calcium" label and a numeric value in the Daily Totals section.
    - [ ] Execute the test and confirm it fails (Red Phase).

## Phase 2: Implementation (Green Phase)
- [ ] Task: Update tracker template to include Calcium
    - [ ] Modify `templates/tracker.html` to add a fourth column to the third row of the "Daily Totals" card.
    - [ ] Update existing `col-4` classes in that row to `col-3` to accommodate the new column.
    - [ ] Bind the display to `day_totals.calcium` with a `0` decimal place filter and "mg" unit.
- [ ] Task: Verify implementation
    - [ ] Execute the E2E test created in Phase 1 and confirm it passes (Green Phase).
    - [ ] Run existing backend tests to ensure no regressions in nutrition calculations.
- [ ] Task: Conductor - User Manual Verification 'Implementation' (Protocol in workflow.md)
