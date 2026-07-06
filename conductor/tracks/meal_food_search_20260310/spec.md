# Specification: Meal/Food Search & Sorting (Track: meal_food_search_20260310)

## Overview
Enhance the user experience on the Tracker page by implementing real-time searching and alphabetical sorting for the "Add Meal" and "Add Food" modals. This will allow users to quickly locate specific items in their potentially large database of foods and meals.

## Functional Requirements
1. **Alphabetical Sorting**:
   - The list of available meals in the "Add Meal" modal must be sorted alphabetically (A-Z) by name.
   - The list of available foods in the "Add Food" modal must be sorted alphabetically (A-Z) by name.
2. **Real-time Search Filter**:
   - A search bar (text input) must be added above the lists in both "Add Meal" and "Add Food" modals.
   - As the user types in the search bar, the list must filter in real-time.
   - The filter should be case-insensitive.
3. **Search Scope**:
   - For **Meals**: The search should match against the `name` field.
   - For **Foods**: The search should match against both the `name` and `brand` fields.

## Non-Functional Requirements
- **Performance**: Filtering should be near-instantaneous on the client-side for a smooth user experience.
- **Maintainability**: Use standard Bootstrap and Vanilla JavaScript patterns consistent with the existing codebase.

## Acceptance Criteria
- [ ] Open the "Add Meal" modal on the Tracker page; meals are sorted A-Z.
- [ ] Type in the search bar in the "Add Meal" modal; the list filters to show only matching meals.
- [ ] Open the "Add Food" modal on the Tracker page; foods are sorted A-Z.
- [ ] Type a food name or brand in the search bar in the "Add Food" modal; the list filters correctly.
- [ ] Clearing the search bar restores the full (sorted) list.

## Out of Scope
- Server-side searching (filtering will be done on the already-loaded client-side list).
- Advanced fuzzy matching (initially, simple substring matching is sufficient).
- Searching for other tabs like "Foods" or "Meals" (this track is specific to the Tracker page modals).