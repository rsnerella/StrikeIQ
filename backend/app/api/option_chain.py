from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ..services.market_data.option_chain_service import OptionChainService
from ..services.upstox_auth_service import get_upstox_auth_service
from ..models.database import get_db
from ..core.config import settings
import logging
from datetime import datetime

router = APIRouter(tags=["option-chain"])
logger = logging.getLogger(__name__)

# Global instances to ensure singleton behavior
_auth_service = None
_option_chain_service = None

def get_option_chain_service():
    """Dependency injection for OptionChainService"""
    global _auth_service, _option_chain_service
    
    if _auth_service is None:
        _auth_service = get_upstox_auth_service()
        logger.info("=== INVESTIGATION: Created global auth service ===")
    
    if _option_chain_service is None:
        _option_chain_service = OptionChainService(_auth_service)
        logger.info("=== INVESTIGATION: Created global option chain service ===")
    
    return _option_chain_service

@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_option_chain(
    symbol: str,
    expiry_date: Optional[str] = None,
    service: OptionChainService = Depends(get_option_chain_service),
    db: Session = Depends(get_db)
):
    """Get option chain for a symbol"""
    try:
        logger.info(f"API request: Option chain for {symbol}, expiry: {expiry_date}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Get option chain data (service will handle expiry resolution)
        print(f"🔍 DEBUG: API endpoint about to call service for {symbol}")
        chain_data = await service.get_option_chain(symbol, expiry_date)
        print(f"🔍 DEBUG: Service returned successfully to API endpoint")
        
        # Service already handles HTTPException properly, no need to check for "error"
        option_chain = chain_data
        
        logger.info(
            f"OPTION_CHAIN_API_RESPONSE strikes={len(option_chain.get('strikes', []))} "
            f"spot={option_chain.get('spot')}"
        )
        
        return {
            "status": "success",
            "data": chain_data,
            "symbol": symbol.upper(),
            "expiry_date": expiry_date,
            "timestamp": chain_data.get("timestamp") if isinstance(chain_data, dict) else datetime.now().isoformat(),
            "total_strikes": len(chain_data.get("calls", [])) + len(chain_data.get("puts", [])) if isinstance(chain_data, dict) else 0
        }
        
    except HTTPException as e:
        # Re-raise HTTPException without modification
        print(f"🔍 DEBUG: HTTPException caught in API endpoint: {e.status_code}")
        logger.info(f"Returning status code: {e.status_code}")
        logger.error(f"HTTPException in option chain API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"🔍 DEBUG: Generic exception caught in API endpoint: {e}")
        logger.error(f"Unexpected error in option chain API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/oi-analysis", response_model=Dict[str, Any])
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
        
        # Service already handles HTTPException properly, no need to check for "error"
        return {
            "status": "success",
            "data": analysis,
            "symbol": symbol.upper(),
            "timestamp": analysis.get("timestamp"),
            "total_strikes": analysis.get("total_strikes", 0)
        }
        
    except HTTPException as e:
        # Re-raise HTTPException without modification
        logger.error(f"HTTPException in OI analysis API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in OI analysis API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/greeks", response_model=Dict[str, Any])
async def get_greeks(
    symbol: str,
    strike: float,
    option_type: str,
    expiry_date: str = None,
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
        
        # Service already handles HTTPException properly, no need to check for "error"
        
        # Find the specific option
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
        logger.error(f"HTTPException in Greeks API: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in Greeks API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
