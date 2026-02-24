# routers/auth.py
from fastapi import APIRouter, Response, Request, HTTPException, Depends, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

security = HTTPBearer(auto_error=False)

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

def get_current_session(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Dependency to get current session from Bearer token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    if token not in active_sessions or not validate_session(token):
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return active_sessions[token]

@router.post("/login")
async def login(body: dict, response: Response):
    """Login with master key, return session token in JSON"""
    logger.info(f"Login attempt")
    
    master_key = body.get("master_key")
    
    if not master_key:
        raise HTTPException(status_code=400, detail="Master key required")
    
    expected_key = os.getenv("MASTER_KEY")
    if not expected_key:
        if len(master_key) < 8:
            raise HTTPException(status_code=401, detail="Invalid master key")
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
    
    # Return token in JSON (NOT in cookie)
    return JSONResponse(content={
        "status": "authenticated",
        "session_token": session_token,  # ← Token in body
        "expires_in": SESSION_DURATION.total_seconds()
    })

@router.post("/logout")
async def logout():
    """Logout - client should clear sessionStorage"""
    return JSONResponse(content={"status": "logged_out"})

@router.get("/session")
async def get_session(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)):
    """Check current session from Bearer token"""
    # Try Authorization header first
    if credentials:
        token = credentials.credentials
        if token in active_sessions and validate_session(token):
            session = active_sessions[token]
            return JSONResponse(content={
                "authenticated": True,
                "expires_at": session["expires_at"].isoformat(),
            })
    
    # Fallback to cookie (for backwards compat)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token and validate_session(session_token):
        session = active_sessions[session_token]
        return JSONResponse(content={
            "authenticated": True,
            "expires_at": session["expires_at"].isoformat(),
        })
    
    return JSONResponse(content={"authenticated": False})

# Protected route example
@router.get("/protected")
async def protected_route(session: dict = Depends(get_current_session)):
    """Example protected endpoint"""
    return JSONResponse(content={"message": "You are authenticated", "session": session})
