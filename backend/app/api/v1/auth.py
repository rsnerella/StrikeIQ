from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import logging
from app.services.upstox_auth_service import get_upstox_auth_service
from app.services.token_manager import token_manager
from core.logger import auth_logger, start_trace, get_trace_id, clear_trace

logger = logging.getLogger(__name__)

router = APIRouter(tags=["authentication"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.get("/status")
async def auth_status():
    """
    Production-grade authentication status check
    Returns authentication status based on Redis token availability
    """
    try:
        # Check if token exists in Redis
        from app.services.token_manager import token_manager
        auth_state = token_manager.get_auth_state()
        
        if auth_state["token_available"]:
            return {
                "authenticated": True,
                "login_url": None
            }
        else:
            # No token available - return login URL
            auth_service = get_upstox_auth_service()
            login_url = auth_service.get_authorization_url()
            
            return {
                "authenticated": False,
                "login_url": login_url
            }
            
    except Exception as e:
        logger.error(f"Auth status check failed: {str(e)}")
        
        # Treat any unexpected error as authentication failure
        auth_service = get_upstox_auth_service()
        login_url = auth_service.get_authorization_url()
        
        return {
            "authenticated": False,
            "login_url": login_url
        }


@router.get("/upstox")
def login():

    auth_service = get_upstox_auth_service()
    auth_url = auth_service.get_authorization_url()

    return RedirectResponse(auth_url)


@router.get("/upstox/callback")
async def callback(code: str = Query(None), request: Request = None):
    # Start trace for OAuth callback
    trace_id = start_trace()
    
    # Log when callback endpoint is hit
    auth_logger.info(f"OAUTH CALLBACK HIT", { 
        "trace_id": trace_id,
        "method": request.method if request else "UNKNOWN",
        "url": str(request.url) if request else "UNKNOWN",
        "user_agent": request.headers.get("user-agent") if request else "UNKNOWN"
    })
    
    # Log query parameters
    query_params = dict(request.query_params) if request else {}
    auth_logger.info(f"OAUTH CALLBACK QUERY PARAMS", { 
        "trace_id": trace_id,
        "params": query_params,
        "param_count": len(query_params)
    })
    
    # Log received authorization code
    if code:
        auth_logger.info(f"OAUTH AUTHORIZATION CODE RECEIVED", { 
            "trace_id": trace_id,
            "code_length": len(code),
            "code_prefix": code[:10] + "..." if len(code) > 10 else code,
            "has_code": True
        })
    else:
        auth_logger.warning(f"OAUTH AUTHORIZATION CODE MISSING", { 
            "trace_id": trace_id,
            "has_code": False
        })
        clear_trace()
        raise HTTPException(status_code=400, detail="Authorization code missing")

    try:
        # Log token exchange request
        auth_logger.info(f"OAUTH TOKEN EXCHANGE START", { 
            "trace_id": trace_id,
            "code_length": len(code),
            "exchange_type": "authorization_code"
        })
        
        token_data = await token_manager.login(code)
        
        # Log full Upstox token response
        auth_logger.info(f"OAUTH TOKEN EXCHANGE SUCCESS", { 
            "trace_id": trace_id,
            "access_token_length": len(token_data.get("access_token", "")),
            "access_token_prefix": token_data.get("access_token", "")[:10] + "..." if token_data.get("access_token") else "NONE",
            "refresh_token_length": len(token_data.get("refresh_token", "")),
            "refresh_token_prefix": token_data.get("refresh_token", "")[:10] + "..." if token_data.get("refresh_token") else "NONE",
            "token_type": token_data.get("token_type"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope"),
            "response_keys": list(token_data.keys())
        })
        
        logger.info("Upstox connected successfully")
        
        # Auto-start market feed after successful login
        try:
            from app.services.websocket_market_feed import start_market_feed
            logger.info("STARTING UPSTOX MARKET FEED AFTER OAUTH")
            await start_market_feed()
            logger.info("OAUTH MARKET FEED STARTED")
        except Exception as e:
            logger.warning(f"OAUTH MARKET FEED AUTO-START FAILED: {e}")
        
        # Log redirect to frontend
        redirect_url = "http://localhost:3000/auth/success?broker=upstox"
        auth_logger.info(f"OAUTH REDIRECT TO FRONTEND", { 
            "trace_id": trace_id,
            "redirect_url": redirect_url,
            "status_code": 302,
            "redirect_type": "success"
        })
        
        # Redirect to frontend success page - token stays server-side
        clear_trace()
        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )
        
    except Exception as e:
        # Log token exchange failure
        auth_logger.error(f"OAUTH TOKEN EXCHANGE FAILED", { 
            "trace_id": trace_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "code_length": len(code) if code else 0
        })
        
        logger.error(f"Token exchange failed: {str(e)}")
        
        # Log redirect to frontend error page
        error_redirect_url = "http://localhost:3000/auth/error?message=authentication_failed"
        auth_logger.info(f"OAUTH REDIRECT TO FRONTEND", { 
            "trace_id": trace_id,
            "redirect_url": error_redirect_url,
            "status_code": 302,
            "redirect_type": "error",
            "error_message": "authentication_failed"
        })
        
        clear_trace()
        # Redirect to frontend error page
        return RedirectResponse(
            url=error_redirect_url,
            status_code=302
        )


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    NOTE: Upstox does not support automatic token refresh
    """
    logger.warning("Token refresh requested - not supported by Upstox")
    raise HTTPException(
        status_code=400,
        detail="Token refresh not supported - please regenerate access token via OAuth"
    )