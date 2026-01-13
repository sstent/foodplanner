from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
import shutil
import sqlite3
import logging
from datetime import datetime
from typing import Optional

# Import from the database module
from app.database import get_db, DATABASE_URL, engine
from main import templates
from app.models.llm_config import LLMConfig
from pydantic import BaseModel

router = APIRouter()

class LLMConfigUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None
    preferred_model: str
    browserless_api_key: Optional[str] = None

def backup_database(source_db_path, backup_db_path):
    """Backs up an SQLite database using the online backup API."""
    logging.info(f"DEBUG: Starting backup - source: {source_db_path}, backup: {backup_db_path}")
    import tempfile
    
    try:
        # Check if source database exists
        if not os.path.exists(source_db_path):
            logging.error(f"DEBUG: Source database file does not exist: {source_db_path}")
            return False
        
        # Create backup in temporary directory first (local fast storage)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_backup_path = temp_file.name
        
        logging.info(f"DEBUG: Creating temporary backup at: {temp_backup_path}")
        
        # Backup to local temp file (fast)
        source_conn = sqlite3.connect(source_db_path)
        temp_conn = sqlite3.connect(temp_backup_path)
        
        with temp_conn:
            source_conn.backup(temp_conn)
        
        source_conn.close()
        temp_conn.close()
        
        logging.info(f"DEBUG: Temporary backup created, copying to final destination")
        
        # Ensure backup directory exists
        backup_dir = os.path.dirname(backup_db_path)
        if backup_dir and not os.path.exists(backup_dir):
            logging.info(f"DEBUG: Creating backup directory: {backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)
        
        # Copy to NAS (this may be slow but won't block SQLite)
        shutil.copy2(temp_backup_path, backup_db_path)
        
        # Clean up temp file
        os.unlink(temp_backup_path)
        
        logging.info(f"Backup of '{source_db_path}' created successfully at '{backup_db_path}'")
        return True

    except sqlite3.Error as e:
        logging.error(f"SQLite error during backup: {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error during backup: {e}", exc_info=True)
        return False
    finally:
        # Cleanup temp file if it still exists
        if 'temp_backup_path' in locals() and os.path.exists(temp_backup_path):
            try:
                os.unlink(temp_backup_path)
            except:
                pass


# Admin Section
@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin/index.html", {"request": request})

@router.get("/admin/imports", response_class=HTMLResponse)
async def admin_imports_page(request: Request):
    return templates.TemplateResponse(request, "admin/imports.html", {"request": request})

@router.get("/admin/llm_config", response_class=HTMLResponse)
async def admin_llm_config_page(request: Request, db: Session = Depends(get_db)):
    logging.info("DEBUG: Starting llm_config route")
    try:
        llm_config = db.query(LLMConfig).first()
        logging.info(f"DEBUG: LLMConfig query result: {llm_config}")
        if not llm_config:
            logging.info("DEBUG: No LLMConfig found, creating new one")
            llm_config = LLMConfig()
            db.add(llm_config)
            db.commit()
            db.refresh(llm_config)
            logging.info(f"DEBUG: Created new LLMConfig: {llm_config}")
        logging.info(f"DEBUG: Final llm_config object: {llm_config}")

        logging.info("DEBUG: About to render llm_config.html template")
        response = templates.TemplateResponse(
            request,
            "admin/llm_config.html",
            {"request": request, "llm_config": llm_config}
        )
        logging.info("DEBUG: Template rendered successfully")
        return response
    except Exception as e:
        logging.error(f"DEBUG: Error in llm_config route: {e}", exc_info=True)
        raise

@router.post("/admin/llm_config", response_class=RedirectResponse)
async def update_llm_config(
    request: Request,
    openrouter_api_key: Optional[str] = Form(None),
    preferred_model: str = Form(...),
    browserless_api_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    llm_config = db.query(LLMConfig).first()
    if not llm_config:
        llm_config = LLMConfig()
        db.add(llm_config)
        db.commit()
        db.refresh(llm_config)

    llm_config.openrouter_api_key = openrouter_api_key
    llm_config.preferred_model = preferred_model
    llm_config.browserless_api_key = browserless_api_key
    db.commit()
    db.refresh(llm_config)
    
    return RedirectResponse(url="/admin/llm_config", status_code=303)

@router.get("/admin/backups", response_class=HTMLResponse)
async def admin_backups_page(request: Request):
    BACKUP_DIR = "./backups"
    backups = []
    if os.path.exists(BACKUP_DIR):
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
            reverse=True
        )
    return templates.TemplateResponse(request, "admin/backups.html", {"backups": backups})

@router.post("/admin/backups/create", response_class=HTMLResponse)
async def create_backup(request: Request, db: Session = Depends(get_db)):
    db_path = DATABASE_URL.split("///")[1]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = "./backups"
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_path = os.path.join(backup_dir, f"meal_planner_{timestamp}.db")
    backup_database(db_path, backup_path)

    # Redirect back to the backups page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/backups", status_code=303)

@router.post("/admin/backups/restore", response_class=HTMLResponse)
async def restore_backup(request: Request, backup_file: str = Form(...)):
    import shutil

    BACKUP_DIR = "./backups"
    db_path = DATABASE_URL.split("///")[1]
    backup_path = os.path.join(BACKUP_DIR, backup_file)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup file not found.")

    try:
        # It's a good practice to close the current connection before overwriting the database
        engine.dispose()
        shutil.copyfile(backup_path, db_path)
        logging.info(f"Database restored from {backup_path}")
    except Exception as e:
        logging.error(f"Failed to restore backup: {e}")
        # You might want to add some user-facing error feedback here
        pass

    # Redirect back to the backups page
    # Redirect back to the backups page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/backups", status_code=303)

@router.get("/admin/config-status", response_class=HTMLResponse)
async def admin_config_status_page(request: Request):
    """Display current system configuration and database status."""
    from urllib.parse import urlparse
    
    # Analyze DATABASE_URL securely
    db_url = DATABASE_URL
    masked_url = db_url
    db_host = "Unknown"
    db_type = "Unknown"

    try:
        # Simple parsing logic to avoid exposing credentials if urlparse fails or acts unexpectedly
        if "sqlite" in db_url:
            db_type = "SQLite"
            db_host = db_url.replace("sqlite:///", "")
            masked_url = "sqlite:///" + db_host
        elif "postgresql" in db_url:
            db_type = "PostgreSQL"
            parsed = urlparse(db_url)
            db_host = parsed.hostname
            # Mask password
            if parsed.password:
                masked_url = db_url.replace(parsed.password, "******")
    except Exception as e:
        logging.error(f"Error parsing database URL: {e}")
        masked_url = "Error parsing URL"
    
    config_data = {
        "database_url": db_url, 
        "database_url_masked": masked_url,
        "database_type": db_type,
        "database_host": db_host,
        "debug": True 
    }

    return templates.TemplateResponse(request, "admin/config.html", {"request": request, "config": config_data})