# Product Guidelines - FoodPlanner

## Visual Identity & Tone
- **Minimalist and Focused:** The interface should be clean and distraction-free, highlighting one primary task at a time to reduce cognitive load.
- **Data Clarity:** Prioritize a high-contrast, readable layout that makes nutritional values easy to scan.

## User Interface Principles
- **Page-Specific Nutritional Awareness:**
    - **Global Context:** Use a subtle, persistent summary (e.g., a sticky header) to keep total macros/calories visible for continuous goal tracking.
    - **Local Context:** On list-heavy pages (like Food Search or Meal Building), integrate nutritional data directly with the items for immediate decision-making.
- **Task-Oriented "Empty States":** When a user encounters an empty view (no foods, no plans), provide clear, actionable instructions and buttons within that space to guide them to the next step.

## Interaction & Behavior
- **Immediate & Reactive:** Every user action (adjusting quantities, adding items) must trigger an instant UI update to the relevant nutritional totals.
- **Unambiguous Validation:** Use Modal Alerts for errors that require immediate attention or could result in data loss, ensuring critical issues are never overlooked.
- **Low Friction:** Design interactions to minimize the number of clicks required for common tasks like portion adjustments or food selection.
