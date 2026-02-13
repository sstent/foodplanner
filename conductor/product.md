# Initial Concept\nAn existing Meal Planner application built with FastAPI, SQLAlchemy, and Jinja2 for managing foods, meals, and nutritional plans.

# Product Definition - FoodPlanner

## Vision
A performance-oriented meal planning application designed for health-conscious households (specifically 2-person units) to hit precise nutritional and macronutrient targets. The application prioritizes speed, data reliability, and structured planning over complex external integrations.

## Target Users
- **Macro-Trackers:** Individuals who meticulously track their caloric and macronutrient intake.
- **2-Person Households:** Users who need to coordinate meal plans for a small, consistent group.

## Core Goals
- **Nutritional Precision:** Enable users to reach specific daily and weekly macro/calorie goals through structured 2-week planning.
- **Efficiency:** Reduce the friction of meal prep by providing tools to save, reuse, and template successful plans and meals.
- **Reliability:** Provide a fast, local-first experience with robust data storage (SQLite/PostgreSQL).

## Key Features
- **Nutritional Totaling:** Automated, real-time calculation of macros and calories for individual foods, combined meals, and full daily/weekly plans.
- **Detailed Daily Planner:** A granular view of each day to visualize meal distribution and ensure macro balance across the day.
- **Meals Library:** A centralized repository to create and save custom meals from individual food components.
- **Template System:** Save and apply successful daily or weekly structures to future plans to minimize repetitive data entry.
- **Open Food Facts Integration:** Rapidly expand the local food database by importing data directly from the Open Food Facts API.

## Technical Philosophy
- **Local-First & Fast:** The UI must be highly responsive, prioritizing a smooth user experience for frequent data entry.
- **Structured Data:** Use a relational database to ensure data integrity across foods, meals, and plans.
