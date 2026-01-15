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
from app.services.fitbit_service import get_config, refresh_tokens, sync_fitbit_weight

from urllib.parse import quote

router = APIRouter()

# --- Helpers ---
# Moved to app.services.fitbit_service

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
    result = sync_fitbit_weight(db, scope)
    status_code = 200 if result['status'] == 'success' else 400
    return JSONResponse(result, status_code=status_code)

