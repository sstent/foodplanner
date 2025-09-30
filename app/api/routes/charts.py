from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
from app.database import get_db, TrackedDay, TrackedMeal, calculate_day_nutrition_tracked

router = APIRouter(tags=["charts"])

@router.get("/charts", response_class=HTMLResponse)
async def charts_page(request: Request, person: str = "Sarah", db: Session = Depends(get_db)):
    """Render the charts page"""
    from main import templates
    return templates.TemplateResponse("charts.html", {
        "request": request,
        "person": person
    })

@router.get("/api/charts", response_model=List[dict])
async def get_charts_data(
    person: str = Query(..., description="Person name (e.g., Sarah)"),
    days: int = Query(7, description="Number of past days to fetch data for", ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get daily calorie data for the last N days for a person.
    Returns list of {"date": "YYYY-MM-DD", "calories": float} sorted by date descending.
    """
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    tracked_days = db.query(TrackedDay).filter(
        TrackedDay.person == person,
        TrackedDay.date >= start_date,
        TrackedDay.date <= end_date
    ).order_by(TrackedDay.date.desc()).all()
    
    chart_data = []
    for tracked_day in tracked_days:
        tracked_meals = db.query(TrackedMeal).filter(
            TrackedMeal.tracked_day_id == tracked_day.id
        ).all()
        day_totals = calculate_day_nutrition_tracked(tracked_meals, db)
        chart_data.append({
            "date": tracked_day.date.isoformat(),
            "calories": round(day_totals.get("calories", 0), 2)
        })
    
    return chart_data