from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import requests
import base64
import json
import datetime
from datetime import date
from typing import Optional

from app.database import get_db, FitbitConfig, WeightLog
from main import templates

from urllib.parse import quote

router = APIRouter()

# --- Helpers ---

def get_config(db: Session) -> FitbitConfig:
    config = db.query(FitbitConfig).first()
    if not config:
        config = FitbitConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def refresh_tokens(db: Session, config: FitbitConfig):
    if not config.refresh_token:
        return None

    token_url = "https://api.fitbit.com/oauth2/token"
    auth_str = f"{config.client_id}:{config.client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": config.refresh_token
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            config.access_token = tokens['access_token']
            config.refresh_token = tokens['refresh_token']
            # config.expires_at = datetime.datetime.now().timestamp() + tokens['expires_in'] # Optional
            db.commit()
            return config.access_token
        else:
            print(f"Failed to refresh token: {response.text}")
            return None
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None

def get_valid_access_token(db: Session, config: FitbitConfig):
    # Simply try to refresh if we suspect it's old (or just always return current and handle 401 caller side)
    # For now, return current, caller handles 401 by calling refresh
    return config.access_token


# --- Routes ---

@router.get("/admin/fitbit", response_class=HTMLResponse)
async def fitbit_page(request: Request, db: Session = Depends(get_db)):
    config = get_config(db)
    # Mask secret
    masked_secret = "*" * 8 if config.client_secret else ""
    is_connected = bool(config.access_token)
    
    # Get recent logs
    logs = db.query(WeightLog).order_by(WeightLog.date.desc()).limit(30).all()
    
    return templates.TemplateResponse("admin/fitbit.html", {
        "request": request,
        "config": config,
        "masked_secret": masked_secret,
        "is_connected": is_connected,
        "logs": logs
    })

@router.post("/admin/fitbit/config")
async def update_config(
    request: Request,
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(...),
    db: Session = Depends(get_db)
):
    config = get_config(db)
    config.client_id = client_id
    config.client_secret = client_secret
    config.redirect_uri = redirect_uri
    db.commit()
    return RedirectResponse(url="/admin/fitbit", status_code=303)

@router.get("/admin/fitbit/auth_url")
async def get_auth_url(db: Session = Depends(get_db)):
    config = get_config(db)
    if not config.client_id or not config.redirect_uri:
        return {"status": "error", "message": "Client ID and Redirect URI must be configured first."}

    encoded_redirect_uri = quote(config.redirect_uri, safe='')
    auth_url = (
        "https://www.fitbit.com/oauth2/authorize"
        f"?response_type=code&client_id={config.client_id}"
        f"&redirect_uri={encoded_redirect_uri}"
        "&scope=weight"
        "&expires_in=604800"
    )
    return {"status": "success", "url": auth_url}

@router.post("/admin/fitbit/auth/exchange")
async def exchange_code(
    request: Request, 
    code_input: str = Form(...),
    db: Session = Depends(get_db)
):
    config = get_config(db)
    
    # Parse code from URL if provided
    code = code_input.strip()
    if "?" in code and "code=" in code:
        from urllib.parse import urlparse, parse_qs
        try:
            query = parse_qs(urlparse(code).query)
            if 'code' in query:
                code = query['code'][0]
        except:
            pass
            
    if code.endswith('#_=_'):
        code = code[:-4]

    # Exchange
    token_url = "https://api.fitbit.com/oauth2/token"
    auth_str = f"{config.client_id}:{config.client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "clientId": config.client_id,
        "grant_type": "authorization_code",
        "redirect_uri": config.redirect_uri,
        "code": code
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            config.access_token = tokens['access_token']
            config.refresh_token = tokens['refresh_token']
            db.commit()
            return RedirectResponse(url="/admin/fitbit", status_code=303)
        else:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error_title": "Auth Failed",
                "error_message": f"Fitbit Error: {response.text}",
                "error_details": ""
            })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_title": "Auth Error",
            "error_message": str(e),
            "error_details": ""
        })

@router.post("/admin/fitbit/sync")
async def sync_data(
    request: Request, 
    scope: str = Form("30d"),
    db: Session = Depends(get_db)
):
    config = get_config(db)
    if not config.access_token:
        return JSONResponse({"status": "error", "message": "Not connected"}, status_code=400)
    
    # Helper to fetch with token refresh support
    def fetch_weights_range(start_date: date, end_date: date, token: str):
        url = f"https://api.fitbit.com/1/user/-/body/log/weight/date/{start_date}/{end_date}.json"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        return requests.get(url, headers=headers)

    # Determine ranges
    ranges = []
    today = datetime.date.today()
    
    if scope == "all":
        # Start from a reasonable past date, e.g., 2015-01-01
        current_start = datetime.date(2015, 1, 1)
        while current_start <= today:
            current_end = current_start + datetime.timedelta(days=30)
            if current_end > today:
                current_end = today
            ranges.append((current_start, current_end))
            current_start = current_end + datetime.timedelta(days=1)
    else:
        # Default 30 days
        start = today - datetime.timedelta(days=30)
        ranges.append((start, today))
        
    total_new = 0
    errors = []

    # Iterate ranges
    # We need to manage token state outside the loop to avoid re-refreshing constantly if it fails
    current_token = config.access_token

    print(f"DEBUG: Starting sync for scope={scope} with {len(ranges)} ranges.")

    for start, end in ranges:
        print(f"DEBUG: Fetching range {start} to {end}...")
        resp = fetch_weights_range(start, end, current_token)
        
        print(f"DEBUG: Response status: {resp.status_code}")
        
        # Handle 401 (Refresh)
        if resp.status_code == 401:
            print(f"Token expired during sync of {start}-{end}, refreshing...")
            new_token = refresh_tokens(db, config)
            if new_token:
                current_token = new_token
                resp = fetch_weights_range(start, end, current_token)
                print(f"DEBUG: Retried request status: {resp.status_code}")
            else:
                errors.append("Token expired and refresh failed.")
                break
        
        # Handle 429 (Rate Limit) - Basic handling: stop
        if resp.status_code == 429:
            errors.append("Rate limit exceeded.")
            print("DEBUG: Rate limit exceeded.")
            break
            
        if resp.status_code == 200:
            data = resp.json()
            weights = data.get('weight', [])
            print(f"DEBUG: Found {len(weights)} weights in this range.")
            for w in weights:
                log_id = str(w.get('logId'))
                weight_val = float(w.get('weight'))
                date_str = w.get('date')
                
                existing = db.query(WeightLog).filter(WeightLog.fitbit_log_id == log_id).first()
                if not existing:
                    log = WeightLog(
                        date=datetime.date.fromisoformat(date_str),
                        weight=weight_val,
                        fitbit_log_id=log_id,
                        source='fitbit'
                    )
                    db.add(log)
                    total_new += 1
                else:
                    existing.weight = weight_val
            db.commit()
        else:
             print(f"DEBUG: Error response: {resp.text}")
             errors.append(f"Error {resp.status_code} for range {start}-{end}: {resp.text}")

    print(f"DEBUG: Sync complete. Total new: {total_new}. Errors: {errors}")

    if errors:
        return JSONResponse({"status": "warning", "message": f"Synced {total_new} records, but encountered errors: {', '.join(errors[:3])}..."})
    else:
        return JSONResponse({"status": "success", "message": f"Synced {total_new} new records (" + ("All History" if scope == 'all' else "30d") + ")"})
