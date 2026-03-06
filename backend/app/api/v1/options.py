from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from ...services.market_data.option_chain_service import OptionChainService
from ...services.market_data.upstox_client import APIResponseError
from ...services.market_data.smart_money_engine import SmartMoneyEngine
from ...services.market_data.smart_money_engine_v2 import SmartMoneyEngineV2
from ...services.market_data.performance_tracking_service import PerformanceTrackingService
from ...models.database import get_db
from ...core.config import settings
import logging
from datetime import datetime
import time
import os

router = APIRouter(tags=["options"])
logger = logging.getLogger(__name__)

# Cache for auth status (1 minute TTL)
_auth_status_cache = {
    'status': None,
    'timestamp': 0,
    'ttl': 60  # 1 minute
}

@router.get("/auth/status", response_model=Dict[str, Any])
async def get_auth_status():
    """Get authentication status with caching (1 minute TTL)"""
    current_time = time.time()
    
    # Check if cache is still valid
    if current_time - _auth_status_cache['timestamp'] < _auth_status_cache['ttl'] and _auth_status_cache['status'] is not None:
        logger.info("Returning cached auth status")
        return _auth_status_cache['status']
    
    try:
        logger.info("Checking fresh auth status...")
        
        # Get access token (this will check with Upstox if needed)
        from ...services.upstox_auth_service import get_upstox_auth_service
        auth_service = get_upstox_auth_service()
        token = await auth_service.get_valid_access_token()
        
        if token:
            # Test token with a lightweight API call
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    'https://api.upstox.com/v3/market-quote/ltp',
                    params={'instrument_key': 'NSE_INDEX|Nifty 50'},
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                if response.status_code == 200:
                    status = {
                        'authenticated': True,
                        'message': 'Token is valid',
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    status = {
                        'session_type': 'AUTH_REQUIRED',
                        'mode': 'AUTH',
                        'message': 'Token validation failed',
                        'login_url': 'http://localhost:8000/api/v1/auth/upstox',
                        'timestamp': datetime.now().isoformat()
                    }
        else:
            status = {
                'session_type': 'AUTH_REQUIRED',
                'mode': 'AUTH', 
                'message': 'No access token available',
                'login_url': 'http://localhost:8000/api/v1/auth/upstox',
                'timestamp': datetime.now().isoformat()
            }
        
        # Cache the result
        _auth_status_cache['status'] = status
        _auth_status_cache['timestamp'] = current_time
        
        logger.info(f"Auth status updated: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Auth status check failed: {e}")
        error_status = {
            'session_type': 'AUTH_REQUIRED',
            'mode': 'AUTH',
            'message': f'Auth check failed: {str(e)}',
            'login_url': 'http://localhost:8000/api/v1/auth/upstox',
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache error status for shorter time (30 seconds)
        _auth_status_cache['status'] = error_status
        _auth_status_cache['timestamp'] = current_time
        _auth_status_cache['ttl'] = 30
        
        return error_status

def get_option_chain_service():
    """Dependency injection for OptionChainService"""
    logger.info("=== INVESTIGATION: Creating OptionChainService ===")
    try:
        from ...services.upstox_auth_service import get_upstox_auth_service
        auth_service = get_upstox_auth_service()
        logger.info(f"=== INVESTIGATION: Created auth_service: {auth_service} (type: {type(auth_service)}) ===")
        service = OptionChainService(auth_service)
        logger.info(f"=== INVESTIGATION: Created service: {service} (type: {type(service)}) ===")
        return service
    except Exception as e:
        logger.error(f"=== INVESTIGATION: Error creating service: {e} ===")
        import traceback
        logger.error(f"=== INVESTIGATION: Traceback: {traceback.format_exc()} ===")
        raise

def get_smart_money_engine():
    """Dependency injection for SmartMoneyEngine"""
    return SmartMoneyEngine()

def get_smart_money_engine_v2():
    """Dependency injection for SmartMoneyEngineV2"""
    return SmartMoneyEngineV2()

def get_performance_tracking_service():
    """Dependency injection for PerformanceTrackingService"""
    return PerformanceTrackingService()

@router.get("/test/{symbol}")
async def test_route(symbol: str):
    """Test route to isolate the error"""
    logger.info(f"=== INVESTIGATION: Test route called with symbol={symbol} (type: {type(symbol)}) ===")
    return {"status": "success", "symbol": symbol, "type": str(type(symbol))}

@router.get("/contract/{symbol}", response_model=Dict[str, Any])
async def get_option_contracts(
    symbol: str,
    service: OptionChainService = Depends(get_option_chain_service),
    db: Session = Depends(get_db)
):
    """Get available option contracts/expiries for a symbol"""
    # AUDIT: Contract endpoint re-enabled for expiry metadata (cached)
    logger.info(f"=== AUDIT: Contract endpoint called for {symbol} ===")
    
    try:
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Get access token
        from ...services.upstox_auth_service import get_upstox_auth_service
        auth_service = get_upstox_auth_service()
        token = auth_service.get_valid_access_token()
        
        if not token:
            raise HTTPException(status_code=401, detail="No access token available")
        
        # Get instrument key for options contracts (use correct contract mapping)
        try:
            logger.info(f"=== AUDIT: Getting contract instrument key for {symbol} ===")
            instrument_key = await service.get_contract_instrument_key(symbol)
            logger.info(f"=== AUDIT: Got instrument key: {instrument_key} for {symbol} ===")
            logger.info(f"=== AUDIT: Service instance: {service} ===")
            logger.info(f"=== AUDIT: Service methods: {[method for method in dir(service) if not method.startswith('_')]} ===")
            logger.info(f"=== AUDIT: Service type: {type(service)} ===")
        except AttributeError as attr_error:
            logger.error(f"=== AUDIT: Method get_contract_instrument_key not found: {attr_error} ===")
            # Fallback to old method
            instrument_key = await service._get_instrument_key(symbol)
            logger.info(f"=== AUDIT: Using fallback instrument key: {instrument_key} ===")
        except Exception as e:
            logger.error(f"=== AUDIT: Error getting contract instrument key: {e} ===")
            raise HTTPException(status_code=500, detail=f"Failed to get instrument key: {e}")
        
        # Fetch option contracts using Upstox client directly
        try:
            import urllib.parse
            
            # Manually construct the URL with proper encoding
            encoded_key = urllib.parse.quote(instrument_key, safe='')
            url = f"https://api.upstox.com/v2/option/contract?instrument_key={encoded_key}"
            
            # Make request
            response = await service.client._make_request('get', url, access_token=token)
            
            if response.status_code != 200:
                logger.error(f"=== AUDIT: API returned status {response.status_code} ===")
                raise HTTPException(status_code=500, detail="Failed to fetch contracts")
            
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict) and "data" in data:
                contracts = data["data"]
            elif isinstance(data, list):
                contracts = data
            else:
                logger.error(f"=== AUDIT: Unexpected response format: {type(data)} ===")
                contracts = []
            
            # Extract unique expiry dates from the contracts we already fetched
            expiries_set = set()
            if isinstance(contracts, list):
                logger.info(f"=== AUDIT: Processing {len(contracts)} contracts for expiries ===")
                for contract in contracts:
                    if isinstance(contract, dict):
                        expiry = contract.get('expiry')
                        if expiry:
                            expiries_set.add(expiry)
            else:
                logger.error(f"=== AUDIT: Contracts is not a list: {type(contracts)} ===")
            
            expiries = sorted(list(expiries_set))
            logger.info(f"=== AUDIT: Found {len(expiries)} expiries for {symbol} ===")
            
            logger.info(f"=== AUDIT: Returning {len(expiries)} expiries for {symbol} ===")
            
            return {
                "status": "success",
                "data": expiries
            }
            
        except Exception as e:
            logger.error(f"=== AUDIT: Error fetching contracts for {symbol}: {e} ===")
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException as e:
        # Re-raise HTTPException without modification
        print(f"DEBUG: HTTPException caught in contract API: {e.status_code}")
        logger.info(f"Returning status code: {e.status_code}")
        logger.error(f"HTTPException in contract API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"DEBUG: Generic exception caught in contract API: {e}")
        logger.exception("Unexpected internal error in contract API")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/chain/{symbol}", response_model=Dict[str, Any])
async def get_option_chain(
    symbol: str,
    expiry_date: Optional[str] = Query(None, description="Expiry date (YYYY-MM-DD)"),
    service: OptionChainService = Depends(get_option_chain_service),
    db: Session = Depends(get_db)
):
    """Get option chain for a symbol"""
    try:
        logger.info(f"API request: Option chain for {symbol}, expiry: {expiry_date}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Validate expiry_date parameter
        if not expiry_date:
            raise HTTPException(status_code=400, detail="Expiry date is required")
        
        # Get option chain data
        logger.info(f"=== INVESTIGATION: About to call service.get_option_chain ===")
        chain_data = await service.get_option_chain(symbol, expiry_date)
        logger.info(f"=== INVESTIGATION: Service returned: {type(chain_data)} ===")
        logger.info(f"=== INVESTIGATION: Service response: {str(chain_data)[:200]} ===")
        
        # Prevent FastAPI 500 crash - validate data
        if not chain_data:
            raise HTTPException(
                status_code=404,
                detail="No Option Chain Found"
            )
        
        # Check if service returned an error response
        if isinstance(chain_data, dict) and "status" in chain_data and chain_data["status"] == "error":
            logger.error(f"=== INVESTIGATION: Service returned error: {chain_data} ===")
            raise HTTPException(status_code=500, detail=chain_data.get("error", "Unknown error"))
        
        # Check if analytics are disabled due to engine failures
        if isinstance(chain_data, dict) and not chain_data.get("analytics_enabled", True):
            logger.warning(f"=== INVESTIGATION: Analytics disabled in service response: {chain_data.get('engine_mode', 'UNKNOWN')} ===")
            # Return disabled state but don't fail - frontend will handle gracefully
            pass
        
        # Add total_strikes and log final response
        chain_data["total_strikes"] = len(chain_data.get("calls", []))
        logger.info(f"Final option chain response: {chain_data}")
        
        return {
            "status": "success",
            "source": "rest",
            "data": chain_data
        }
        
    except HTTPException as e:
        # Re-raise HTTPException without modification
        print(f"DEBUG: HTTPException caught in v1 options API: {e.status_code}")
        logger.info(f"Returning status code: {e.status_code}")
        logger.error(f"HTTPException in option chain API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"DEBUG: Generic exception caught in v1 options API: {e}")
        logger.exception("Unexpected internal error in option chain API")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/oi-analysis/{symbol}", response_model=Dict[str, Any])
async def get_oi_analysis(
    symbol: str,
    service: OptionChainService = Depends(get_option_chain_service),
    db: Session = Depends(get_db)
):
    """Get OI analysis for a symbol"""
    try:
        logger.info(f"API request: OI analysis for {symbol}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Get OI analysis
        analysis = await service.get_oi_analysis(symbol)
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        
        return {
            "status": "success",
            "data": analysis,
            "symbol": symbol.upper(),
            "timestamp": analysis.get("timestamp"),
            "total_strikes": analysis.get("total_strikes", 0)
        }
        
    except HTTPException as e:
        # Re-raise HTTPException without modification
        print(f"DEBUG: HTTPException caught in OI analysis API: {e.status_code}")
        logger.info(f"Returning status code: {e.status_code}")
        logger.error(f"HTTPException in OI analysis API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"DEBUG: Generic exception caught in OI analysis API: {e}")
        logger.exception("Unexpected internal error in OI analysis API")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/greeks/{symbol}", response_model=Dict[str, Any])
async def get_greeks(
    symbol: str,
    strike: float = Query(..., description="Strike price"),
    option_type: str = Query(..., description="Option type: CE or PE"),
    expiry_date: Optional[str] = Query(None, description="Expiry date (YYYY-MM-DD)"),
    service: OptionChainService = Depends(get_option_chain_service),
    db: Session = Depends(get_db)
):
    """Get Greeks for specific option"""
    try:
        logger.info(f"API request: Greeks for {symbol} {strike} {option_type}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Validate option type
        if option_type.upper() not in ["CE", "PE"]:
            raise HTTPException(status_code=400, detail="Invalid option type. Must be CE or PE")
        
        # Get option chain to find specific strike
        chain_data = await service.get_option_chain(symbol, expiry_date)
        
        if "error" in chain_data:
            raise HTTPException(status_code=500, detail=chain_data["error"])
        
        # Find specific option
        target_option = None
        for item in chain_data:
            if (item.get("strike_price") == strike and 
                item.get("option_type") == option_type.upper()):
                target_option = item
                break
        
        if not target_option:
            raise HTTPException(status_code=404, detail=f"Option not found: {strike} {option_type}")
        
        # Extract Greeks if available
        greeks = {
            "delta": target_option.get("delta"),
            "gamma": target_option.get("gamma"),
            "theta": target_option.get("theta"),
            "vega": target_option.get("vega"),
            "implied_volatility": target_option.get("iv")
        }
        
        return {
            "status": "success",
            "data": {
                "strike": strike,
                "option_type": option_type,
                "greeks": greeks,
                "ltp": target_option.get("ltp"),
                "oi": target_option.get("oi"),
                "volume": target_option.get("volume")
            },
            "symbol": symbol.upper(),
            "expiry_date": expiry_date,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException as e:
        # Re-raise HTTPException without modification
        print(f"DEBUG: HTTPException caught in Greeks API: {e.status_code}")
        logger.info(f"Returning status code: {e.status_code}")
        logger.error(f"HTTPException in Greeks API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"DEBUG: Generic exception caught in Greeks API: {e}")
        logger.exception("Unexpected internal error in Greeks API")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/smart-money/{symbol}", response_model=Dict[str, Any])
async def get_smart_money_signal(
    symbol: str,
    engine: SmartMoneyEngine = Depends(get_smart_money_engine),
    db: Session = Depends(get_db)
):
    """Get smart money directional bias signal for a symbol"""
    try:
        logger.info(f"API request: Smart money signal for {symbol}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Generate smart money signal
        signal = await engine.generate_smart_money_signal(symbol, db)
        
        return {
            "status": "success",
            "data": signal,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Validation error in smart money API: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in smart money API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/smart-money-v2/{symbol}", response_model=Dict[str, Any])
async def get_smart_money_signal_v2(
    symbol: str,
    engine: SmartMoneyEngineV2 = Depends(get_smart_money_engine_v2),
    db: Session = Depends(get_db)
):
    """Get smart money directional bias signal v2 (statistically stable)"""
    try:
        logger.info(f"API request: Smart money v2 signal for {symbol}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Generate smart money signal with v2 engine
        signal = await engine.generate_smart_money_signal(symbol, db)
        
        return {
            "status": "success",
            "data": signal,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Validation error in smart money v2 API: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in smart money v2 API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/smart-money/performance/{symbol}", response_model=Dict[str, Any])
async def get_smart_money_performance(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="Number of days for performance analysis"),
    service: PerformanceTrackingService = Depends(get_performance_tracking_service),
    db: Session = Depends(get_db)
):
    """Get smart money performance metrics for a symbol"""
    try:
        logger.info(f"API request: Smart money performance for {symbol}, days: {days}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Get performance metrics
        performance = await service.get_performance_metrics(symbol, db, days)
        
        return {
            "status": "success",
            "data": performance,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Validation error in performance API: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in performance API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-money/update-results/{symbol}", response_model=Dict[str, Any])
async def update_smart_money_results(
    symbol: str,
    lookback_minutes: int = Query(30, ge=5, le=120, description="Lookback period in minutes"),
    service: PerformanceTrackingService = Depends(get_performance_tracking_service),
    db: Session = Depends(get_db)
):
    """Update smart money prediction results based on actual market moves"""
    try:
        logger.info(f"API request: Update smart money results for {symbol}, lookback: {lookback_minutes}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Update prediction results
        result = await service.update_prediction_results(symbol, db, lookback_minutes)
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Validation error in update results API: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in update results API: {e}")
        raise HTTPException(status_code=500, detail=str(e))
