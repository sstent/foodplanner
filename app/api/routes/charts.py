from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
from app.database import get_db, TrackedDay, TrackedMeal, calculate_day_nutrition_tracked, WeightLog

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
    # Fetch all tracked days and weight logs for the period
    tracked_days_map = {
        d.date: d for d in db.query(TrackedDay).filter(
            TrackedDay.person == person,
            TrackedDay.date >= start_date,
            TrackedDay.date <= end_date
        ).all()
    }

    # Sort logs desc
    weight_logs_map = {
        w.date: w for w in db.query(WeightLog).filter(
            WeightLog.date >= start_date,
            WeightLog.date <= end_date
        ).order_by(WeightLog.date.desc()).all()
    }
    
    # Get last weight BEFORE start_date (for initial carry forward)
    last_historical_weight_log = db.query(WeightLog).filter(
        WeightLog.date < start_date
    ).order_by(WeightLog.date.desc()).first()
    
    last_historical_weight_val = last_historical_weight_log.weight * 2.20462 if last_historical_weight_log else None
    
    # Find the most recent weight available (either in range or history)
    # This is for "Today" (end_date)
    latest_weight_val = last_historical_weight_val
    
    # Check if we have newer weights in the map
    # Values in weight_logs_map are WeightLog objects.
    # Find the one with max date <= end_date. Since map key is date, we can check.
    # But filtering the map is tedious. Let's just iterate.
    # Actually, we already have `weight_logs_map` (in range).
    # If the range has weights, the newest one is the "latest" known weight relevant to the end of chart.
    if weight_logs_map:
        # Get max date
        max_date = max(weight_logs_map.keys())
        latest_weight_val = weight_logs_map[max_date].weight * 2.20462

    chart_data = []
    
    # Iterate dates. Note: i=0 is end_date (Today), i=days-1 is start_date (Oldest)
    for i in range(days):
        current_date = end_date - timedelta(days=i)
        
        tracked_day = tracked_days_map.get(current_date)
        weight_log = weight_logs_map.get(current_date)

        calories = 0
        protein = 0
        fat = 0
        net_carbs = 0
        
        # Calculate nutrition
        if tracked_day:
            tracked_meals = db.query(TrackedMeal).filter(
                TrackedMeal.tracked_day_id == tracked_day.id
            ).all()
            day_totals = calculate_day_nutrition_tracked(tracked_meals, db)
            calories = round(day_totals.get("calories", 0), 2)
            protein = round(day_totals.get("protein", 0), 2)
            fat = round(day_totals.get("fat", 0), 2)
            net_carbs = round(day_totals.get("net_carbs", 0), 2)
        
        weight_lbs = None
        is_real = False
        
        if weight_log:
            weight_lbs = round(weight_log.weight * 2.20462, 2)
            is_real = True
            
        # Logic for Start and End Points (to ensure line connects across view)
        
        # If this is the Oldest date in view (start_date) and no real weight
        if i == days - 1 and weight_lbs is None:
             # Use historical weight if available (to start the line)
             if last_historical_weight_val is not None:
                 weight_lbs = round(last_historical_weight_val, 2)
                 # is_real remains False (inferred)
        
        # If this is the Newest date in view (end_date/Today) and no real weight
        if i == 0 and weight_lbs is None:
            # Use latest known weight (to end the line)
            if latest_weight_val is not None:
                weight_lbs = round(latest_weight_val, 2)
                # is_real remains False (inferred)

        chart_data.append({
            "date": current_date.isoformat(),
            "calories": calories,
            "protein": protein,
            "fat": fat,
            "net_carbs": net_carbs,
            "weight_lbs": weight_lbs,
            "weight_is_real": is_real
        })
            
    return chart_data