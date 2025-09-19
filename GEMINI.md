## Project Overview

This is a Meal Planner application built with FastAPI. It allows users to manage a food database, create meals from foods, and generate 2-week meal plans. The application uses SQLAlchemy for database interactions and Jinja2 for templating the user interface.

**Key Features:**
*   **Foods** - Manage a database of food items with nutritional information.
*   **Meals** - Create custom meals by combining various food items.
*   **Plans** - Generate and manage 2-week meal plans, including daily nutritional totals.
*   **Detailed Planner** - View a detailed breakdown of meals for a specific day.

## Building and Running

This project uses `uvicorn` to serve the FastAPI application.

1.  **Install Dependencies:**
    Ensure you have Python 3.7+ installed. Install the required Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Application:**
    Start the FastAPI server using uvicorn. The `--reload` flag enables auto-reloading on code changes, which is useful for development.
    ```bash
    uvicorn main:app --reload
    ```
    The application will typically be accessible at `http://127.0.0.1:8000` (or the port specified in `main.py` if different, e.g., `8999`).

## Development Conventions

*   **Framework:** FastAPI is used for the backend API and serving HTML templates.
*   **Database:** SQLAlchemy is used as the ORM for interacting with the SQLite database (`meal_planner.db`).
*   **Templating:** Jinja2 is used for rendering HTML pages. Templates are located in the `templates/` directory.
*   **Dependency Injection:** Database sessions are managed using FastAPI's dependency injection system (`Depends(get_db)`).
*   **Pydantic Models:** Pydantic models are used for data validation and serialization of API requests and responses.
*   **Static Files:** Static files (CSS, JS, images) are served from the `static/` directory (though not explicitly shown in the provided file list, it's a common FastAPI convention).
