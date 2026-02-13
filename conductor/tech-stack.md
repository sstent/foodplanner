# Tech Stack - FoodPlanner

## Core Backend
- **Language:** Python 3.7+
- **Web Framework:** FastAPI (Asynchronous, high-performance web framework)
- **Data Validation:** Pydantic (Used for schema definition and request/response validation)

## Data Layer
- **ORM:** SQLAlchemy (Using 2.0+ patterns for database interactions)
- **Database:** Support for SQLite (local development) and PostgreSQL (production)
- **Migrations:** Alembic (Handles database schema evolution)

## Frontend & UI
- **Templating:** Jinja2 (Server-side rendering for HTML templates)
- **Frontend Logic:** Minimal JavaScript for reactive UI updates and modal management

## External Integrations
- **Food Data:** Open Food Facts API (For importing nutritional information)
- **AI/Extraction:** OpenAI API (Used for extracting food data from unstructured text)

## Quality Assurance
- **E2E Testing:** Playwright (For browser-based integration tests)
- **Unit/Integration Testing:** pytest (For backend logic and API testing)
