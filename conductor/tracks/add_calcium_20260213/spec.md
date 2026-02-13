# Specification - Add Calcium to Tracker Totals

## Overview
This track adds a Calcium display to the "Daily Totals" section of the tracker page. This allows users to track their calcium intake (in mg) alongside other micronutrients and macronutrients.

## Functional Requirements
- **Display Calcium:** Add a new column to the third row of the "Daily Totals" card on the `tracker.html` page.
- **Unit of Measurement:** Calcium shall be displayed in milligrams (mg).
- **Precision:** Calcium values shall be rounded to the nearest whole number (0 decimal places).
- **Data Source:** Use the `day_totals.calcium` value provided by the backend, which is already correctly calculated in `calculate_day_nutrition_tracked`.

## Non-Functional Requirements
- **UI Consistency:** The new Calcium display should match the style of the existing Sugar, Fiber, and Sodium displays (border, padding, centered text, small muted label).
- **Responsiveness:** The layout should remain functional on various screen sizes. Adding a fourth column to the row may require adjusting column widths (e.g., from `col-4` to `col-3`).

## Acceptance Criteria
- [ ] A "Calcium" box is visible in the "Daily Totals" section of the tracker page.
- [ ] The value displayed matches the sum of calcium from all tracked foods for that day.
- [ ] The unit "mg" is displayed next to or below the value.
- [ ] The layout of the "Daily Totals" card remains clean and balanced.

## Out of Scope
- Adding Calcium to individual food or meal breakdown tables.
- Updating Open Food Facts import logic (unless found to be missing Calcium data during verification).
- Adding Calcium targets or progress bars.
