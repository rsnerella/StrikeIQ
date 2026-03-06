"""
Market Session API Endpoints
Exposes market status and engine mode information to frontend
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any
import logging

from app.services.market_session_manager import check_market_time, IST

router = APIRouter(tags=["market-session"])
logger = logging.getLogger(__name__)


@router.get("/session", response_model=Dict[str, Any])
async def get_market_session():
    """Return current market session"""

    try:
        now = datetime.now(IST)
        market_open = check_market_time()
        session = "LIVE" if market_open else "CLOSED"
        
        logger.info(f"Market session check → time={now} → open={market_open}")
        
        return {
            "market_open": market_open,
            "session": session,
            "timestamp": now.isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting market session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/refresh", response_model=Dict[str, Any])
async def refresh_market_status():
    """Force refresh market status"""
    try:
        manager = get_market_session_manager()
        new_status = await manager.force_status_check()
        
        return {
            "status": "success",
            "data": {
                "market_status": new_status.value,
                "engine_mode": manager.get_engine_mode().value,
                "message": f"Market status refreshed to {new_status.value}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing market status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/status", response_model=Dict[str, str])
async def get_simple_status():
    """Get simple market status for quick frontend checks"""
    try:
        manager = get_market_session_manager()
        
        return {
            "market_status": manager.get_market_status().value,
            "engine_mode": manager.get_engine_mode().value
        }
        
    except Exception as e:
        logger.error(f"Error getting simple status: {e}")
        return {
            "market_status": "UNKNOWN",
            "engine_mode": "OFFLINE"
        }

@router.get("/session/health", response_model=Dict[str, Any])
async def get_session_health():
    """Get health status of market session manager"""
    try:
        manager = get_market_session_manager()
        status_info = manager.get_status_info()
        
        # Determine health based on last check time
        is_healthy = True
        health_issues = []
        
        if status_info["last_check"] is None:
            is_healthy = False
            health_issues.append("No status checks performed")
        else:
            last_check = datetime.fromisoformat(status_info["last_check"].replace('Z', '+00:00'))
            time_since_check = datetime.utcnow().replace(tzinfo=last_check.tzinfo) - last_check
            
            if time_since_check.total_seconds() > 120:  # 2 minutes
                is_healthy = False
                health_issues.append(f"Status check stale: {time_since_check.total_seconds():.0f}s ago")
        
        if not status_info["is_polling"]:
            health_issues.append("Status polling not active")
        
        return {
            "healthy": is_healthy,
            "issues": health_issues,
            "status": status_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting session health: {e}")
        return {
            "healthy": False,
            "issues": [f"Health check failed: {str(e)}"],
            "timestamp": datetime.utcnow().isoformat()
        }
