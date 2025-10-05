from fastapi import APIRouter

from app.api.routes import (
    admin,
    charts,
    export,
    foods,
    llm,
    meals,
    plans,
    templates,
    tracker,
    weekly_menu,
)

api_router = APIRouter()
api_router.include_router(tracker.router, tags=["tracker"])
api_router.include_router(foods.router, tags=["foods"])
api_router.include_router(meals.router, tags=["meals"])
api_router.include_router(templates.router, tags=["templates"])
api_router.include_router(charts.router, tags=["charts"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(weekly_menu.router, tags=["weekly_menu"])
api_router.include_router(plans.router, tags=["plans"])
api_router.include_router(export.router, tags=["export"])
api_router.include_router(llm.router, tags=["llm"])