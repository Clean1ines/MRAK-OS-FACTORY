# routers/auth.py
# ADDED: New file for session-based authentication
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import os
import hashlib
import secrets

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Session storage (in production: use Redis)
active_sessions = {}

# Session configuration
SESSION_DURATION = timedelta(hours=24)
SESSION_COOKIE_NAME = "mrak_session"

def generate_session_token(master_key: str) -> str:
    """Generate secure session token from master key."""
    # Hash the master key (never store raw)
    key_hash = hashlib.sha256(master_key.encode()).hexdigest()
    # Add random salt for session
    session_salt = secrets.token_hex(16)
    return f"{key_hash[:32]}:{session_salt}"

def validate_session(session_token: str) -> bool:
    """Validate session token."""
    if session_token not in active_sessions:
        return False
    
    session = active_sessions[session_token]
    # Check expiration
    if datetime.now() > session["expires_at"]:
        del active_sessions[session_token]
        return False
    
    return True

@router.post("/login")
async def login(body: dict, response: Response):
    """Login with master key, set httpOnly cookie."""
    master_key = body.get("master_key")
    
    if not master_key:
        raise HTTPException(status_code=400, detail="Master key required")
    
    # Validate master key (in production: check against database)
    expected_key = os.getenv("MASTER_KEY")
    if not expected_key:
        # For development: accept any non-empty key
        if len(master_key) < 8:
            raise HTTPException(status_code=401, detail="Invalid master key")
    else:
        if master_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid master key")
    
    # Generate session token
    session_token = generate_session_token(master_key)
    
    # Store session
    active_sessions[session_token] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + SESSION_DURATION,
        "master_key_hash": hashlib.sha256(master_key.encode()).hexdigest(),
    }
    
    # Set httpOnly cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,      # //ADDED: Prevent XSS access
        secure=True,        # //ADDED: HTTPS only
        samesite="lax",     # //ADDED: CSRF protection
        path="/",
    )
    
    return JSONResponse(content={"status": "authenticated", "expires_in": SESSION_DURATION.total_seconds()})

@router.post("/logout")
async def logout(response: Response, request: Request):
    """Logout and clear session cookie."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    
    if session_token and session_token in active_sessions:
        del active_sessions[session_token]
    
    # Clear cookie
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )
    
    return JSONResponse(content={"status": "logged_out"})

@router.get("/session")
async def get_session(request: Request):
    """Check current session status."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    
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