# Data-TestID Implementation Strategy

This document outlines the new strategy for implementing stable, non-ambiguous `data-testid` attributes across the application. This approach will resolve "strict mode violation" errors in Playwright and ensure our tests are robust against changes in UI class names, element order, and data duplication (e.g., duplicate meal names).

## Goal

To create unique and consistent identifiers for every dynamic element on a page, where consistency is based on stable data (e.g., meal name, meal time) rather than dynamic database IDs.

## I. General Naming Convention

All new testing identifiers will be implemented using the `data-testid` HTML attribute and follow the format:

`data-testid="[element-type-prefix]-[unique-id]"`

The core of this strategy is the **Unique ID**, which ensures that duplicate item names are handled correctly.

## II. The Unique Meal ID Structure (Example from `tracker.html`)

The Unique Meal ID is a composite slug generated using Jinja variables. It provides a unique identifier for a specific instance of a meal in a specific time slot.

**Unique Meal ID** = `[meal-time-slug]-[meal-name-slug]-[loop-index]`

| Component | Jinja Source | Description | Example |
| :--- | :--- | :--- | :--- |
| **meal-time-slug** | `meal_time\|lower\|replace(' ', '-')` | The slugified meal time category (e.g., "Breakfast"). | `breakfast` |
| **meal-name-slug** | `tracked_meal.meal.name\|lower\|replace(' ', '-')\|replace(',', '')\|replace('.', '')` | The slugified and sanitized name of the meal. | `protein-shake` |
| **loop-index** | `loop.index\|string` | The 1-based index of the meal within its time slot. This is critical for solving duplicate meal name ambiguity. | `1` |

### Example of a Full Unique Meal ID:

| Scenario | Generated ID |
| :--- | :--- |
| First "Protein Shake" in Breakfast | `breakfast-protein-shake-1` |
| Second "Protein Shake" in Breakfast | `breakfast-protein-shake-2` |

## III. Implementation Details (`templates/tracker.html`)

The following slugs and variables must be defined inside the main `{% for tracked_meal in meals_for_time %}` loop.

### A. Setup Variables (To be placed at the top of the loop)

```jinja
{% for tracked_meal in meals_for_time %}
    {# 1. Create stable slugs #}
    {% set meal_time_slug = meal_time|lower|replace(' ', '-') %}
    {% set meal_name_safe = tracked_meal.meal.name|lower|replace(' ', '-')|replace(',', '')|replace('.', '') %}
    
    {# 2. Construct the core Unique Meal ID for non-ambiguous locating #}
    {% set unique_meal_id = meal_time_slug + '-' + meal_name_safe + '-' + loop.index|string %}
    
    ...
{% endfor %}
```

### B. HTML Element Locators

| Element | Prefix | HTML Attribute (using the Jinja variable) | Example `data-testid` |
| :--- | :--- | :--- | :--- |
| Meal Card Container | `meal-card` | `data-testid="meal-card-{{ unique_meal_id }}"` | `meal-card-breakfast-protein-shake-1` |
| Meal Name (`<strong>`) | `meal-name` | `data-testid="meal-name-{{ unique_meal_id }}"` | `meal-name-breakfast-protein-shake-1` |
| Edit Button | `edit-meal` | `data-testid="edit-meal-{{ unique_meal_id }}"` | `edit-meal-breakfast-protein-shake-1` |
| Delete Button | `delete-meal` | `data-testid="delete-meal-{{ unique_meal_id }}"` | `delete-meal-breakfast-protein-shake-1` |
| Food Item Display (`<div>`) | `food-display` | `data-testid="food-display-{{ unique_meal_id }}-{{ food_name_safe }}-{{ inner_loop.index }}"` | `food-display-breakfast-ps-1-strawberry-1` |

**Action Required:** This pattern should be used to update existing Playwright tests and applied to other templates to ensure testing consistency.