# Specification - Meal Tracker Refactoring

**Overview:**
Refactor the meal tracking system to decouple "Journal Logs" from "Cookbook Recipes". Currently, adding a single food item via the tracker incorrectly creates a permanent 'Meal' record of type 'single_food', leading to database pollution and duplicate entries in the Meals library.

**Functional Requirements:**
- **TrackedMeal Schema Update:** Add a 'name' column to the 'TrackedMeal' model to store the display name of a logged meal or a single food item.
- **Nullable meal_id:** Modify 'TrackedMeal.meal_id' to be nullable, allowing "template-less" logs.
- **Refactored Tracker Logic:** Update the 'tracker_add_food' route to log single items directly as a 'TrackedMeal' with 'meal_id=NULL' and the 'name' set to the food item's name.
- **Nutrition Calculation:** Update nutrition calculation logic to handle 'TrackedMeal' entries without a parent 'Meal' template.
- **Tracker UI Update:** Ensure the tracker page displays 'TrackedMeal.name' for these logs and maintains the seamless visual style of existing entries.
- **Cookbook Cleanup (One-time Migration):** Migrate existing 'single_food' meals to the new format and purge the redundant records from the 'meals' and 'meal_foods' tables.
- **Cookbook Filtering:** Update the Meals page to exclude 'single_food' and 'snapshot' meal types from view.

**Non-Functional Requirements:**
- **Database Integrity:** Ensure all existing logs remain accurate and correctly linked to their food items during migration.
- **Performance:** The tracker page should remain fast and responsive with the new logic.

**Acceptance Criteria:**
- [ ] Adding a single food to the tracker does **not** create a new entry in the 'meals' table.
- [ ] Existing 'single_food' duplicates are removed from the 'meals' library.
- [ ] The Meals page only shows "Cookbook Recipes" (e.g., proper combined meals).
- [ ] The Tracker page correctly displays names and calculates nutrition for all logs (both template-based and template-less).
- [ ] "Save as New Meal" remains available for all log entries, including single foods.

**Out of Scope:**
- Refactoring the entire meal planning system beyond the tracker/cookbook separation.
- Changes to the external Open Food Facts integration.
