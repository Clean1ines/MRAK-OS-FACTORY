# routers/auth.py
from fastapi import APIRouter, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import os
import hashlib
import secrets
import logging

logger = logging.getLogger("MRAK-SERVER")

router = APIRouter(prefix="/api/auth", tags=["auth"])

active_sessions = {}
SESSION_DURATION = timedelta(hours=24)
SESSION_COOKIE_NAME = "mrak_session"

def generate_session_token(master_key: str) -> str:
    key_hash = hashlib.sha256(master_key.encode()).hexdigest()
    session_salt = secrets.token_hex(16)
    return f"{key_hash[:32]}:{session_salt}"

def validate_session(session_token: str) -> bool:
    if session_token not in active_sessions:
        return False
    session = active_sessions[session_token]
    if datetime.now() > session["expires_at"]:
        del active_sessions[session_token]
        return False
    return True

@router.post("/login")
async def login(body: dict, response: Response, request: Request):
    logger.info(f"Login attempt from {request.client.host if request.client else 'unknown'}")
    
    master_key = body.get("master_key")
    
    if not master_key:
        raise HTTPException(status_code=400, detail="Master key required")
    
    expected_key = os.getenv("MASTER_KEY")
    if not expected_key:
        if len(master_key) < 8:
            raise HTTPException(status_code=401, detail="Invalid master key (min 8 characters)")
    else:
        if master_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid master key")
    
    session_token = generate_session_token(master_key)
    
    active_sessions[session_token] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + SESSION_DURATION,
        "master_key_hash": hashlib.sha256(master_key.encode()).hexdigest(),
    }
    
    logger.info(f"Login successful")
    
    # #CHANGED: secure=True + samesite=none for Firefox compatibility
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=True,      # REQUIRED for HTTPS
        samesite="lax",   # Changed from "none" - lax works for same-site
        path="/",
    )
    
    set_cookie_header = response.headers.get('set-cookie', 'NOT SET')
    logger.info(f"Set-Cookie: {set_cookie_header[:150]}...")
    
    return JSONResponse(content={"status": "authenticated", "expires_in": SESSION_DURATION.total_seconds()})

@router.post("/logout")
async def logout(response: Response, request: Request):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token and session_token in active_sessions:
        del active_sessions[session_token]
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return JSONResponse(content={"status": "logged_out"})

@router.get("/session")
async def get_session(request: Request):
    all_cookies = dict(request.cookies)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    
    logger.info(f"Session check: mrak_session present={bool(session_token)}")
    logger.info(f"All cookies: {list(all_cookies.keys())}")
    
    if not session_token:
        return JSONResponse(content={"authenticated": False})
    
    if validate_session(session_token):
        session = active_sessions[session_token]
        return JSONResponse(content={
            "authenticated": True,
            "expires_at": session["expires_at"].isoformat(),
        })
    else:
        return JSONResponse(content={"authenticated": False})
