from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timezone
from ...services.upstox_auth_service import get_upstox_auth_service
from ...models.database import get_db
import logging

router = APIRouter(tags=["debug"])
logger = logging.getLogger(__name__)

@router.get("/auth-session", response_model=Dict[str, Any])
async def get_auth_session_status(db: Session = Depends(get_db)):
    """Production-safe debug endpoint to check authentication status"""
    try:
        auth_service = get_upstox_auth_service()
        
        # Check authentication status
        is_auth = auth_service.is_authenticated()
        
        # Get token details if available
        token_expiry = None
        seconds_remaining = None
        refresh_supported = False
        
        if auth_service._credentials:
            token_expiry = auth_service._credentials.expires_at.isoformat()
            seconds_remaining = max(0, int((auth_service._credentials.expires_at - datetime.now(timezone.utc)).total_seconds()))
            refresh_supported = bool(auth_service._credentials.refresh_token)
        
        return {
            "authenticated": is_auth,
            "token_expiry": token_expiry,
            "seconds_remaining": seconds_remaining,
            "refresh_supported": refresh_supported,
            "state_validation_enabled": True,
            "debug_info": {
                "has_credentials": auth_service._credentials is not None,
                "credentials_file": auth_service._credentials_file,
                "current_time": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in auth session debug: {e}")
        raise HTTPException(status_code=500, detail="Failed to get auth session status")
