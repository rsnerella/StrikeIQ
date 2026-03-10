"""
AI Debug API Endpoint for StrikeIQ
Provides debugging and validation endpoints for AI engines and analytics modules
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from app.core.diagnostics import diag
from app.core.ai_diagnostics import run_comprehensive_validation
from app.services.option_chain_builder import option_chain_builder
from app.services.ai_signal_engine import AISignalEngine
from app.services.expected_move_engine import ExpectedMoveEngine
from app.services.gamma_pressure_map import GammaPressureMapEngine
from app.services.market_data.smart_money_engine import SmartMoneyEngine
from app.services.advanced_strategies_engine import run_advanced_strategies

router = APIRouter()

@router.get("/debug/ai")
async def debug_ai():
    """
    Basic AI diagnostics endpoint
    Returns status of all AI components
    """
    try:
        diag("AI_TEST", "Running AI diagnostics")
        
        # Test option chain builder
        chain_status = "active" if option_chain_builder.chains else "empty"
        
        return {
            "status": "AI diagnostics active",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "option_chain_builder": chain_status,
                "ai_signal_engine": "available",
                "expected_move_engine": "available",
                "gamma_pressure_map": "available",
                "smart_money_engine": "available",
                "advanced_strategies": "available"
            }
        }
    except Exception as e:
        diag("AI_TEST", f"AI diagnostics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/ai/validate")
async def debug_ai_validation():
    """
    Run comprehensive AI validation
    Tests all AI components with current data
    """
    try:
        diag("AI_TEST", "Running comprehensive AI validation")
        
        # Get current option chain data
        test_data = {}
        
        # Test with NIFTY data if available
        if "NIFTY" in option_chain_builder.chains:
            nifty_chain = option_chain_builder.get_chain("NIFTY")
            if nifty_chain:
                test_data["option_chain"] = nifty_chain
        
        # Run validation
        validation_results = run_comprehensive_validation(test_data)
        
        return {
            "status": "validation_complete",
            "timestamp": datetime.now().isoformat(),
            "validation_results": validation_results,
            "summary": {
                "total_checks": len(validation_results),
                "passed": sum(1 for result in validation_results.values() if result),
                "failed": sum(1 for result in validation_results.values() if not result)
            }
        }
    except Exception as e:
        diag("AI_TEST", f"AI validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/ai/engines")
async def debug_ai_engines():
    """
    Test individual AI engines
    Returns test results from each engine
    """
    try:
        diag("AI_TEST", "Testing individual AI engines")
        
        results = {}
        
        # Test Expected Move Engine
        try:
            move_engine = ExpectedMoveEngine()
            test_data = {
                "symbol": "NIFTY",
                "spot": 20000,
                "calls": [{"strike": 20000, "ltp": 150, "oi": 1000}],
                "puts": [{"strike": 20000, "ltp": 140, "oi": 1200}]
            }
            move_result = move_engine.compute(test_data)
            results["expected_move"] = {
                "status": "success",
                "expected_move_1sd": move_result.expected_move_1sd,
                "implied_volatility": move_result.implied_volatility
            }
        except Exception as e:
            results["expected_move"] = {"status": "error", "error": str(e)}
        
        # Test Gamma Pressure Map
        try:
            gamma_engine = GammaPressureMapEngine()
            test_data = {
                "spot": 20000,
                "strikes": {
                    20000: {
                        "call": {"gamma": 0.02, "oi": 1000},
                        "put": {"gamma": 0.018, "oi": 1200}
                    }
                }
            }
            gamma_result = gamma_engine.compute_pressure_map("NIFTY", test_data)
            results["gamma_pressure"] = {
                "status": "success",
                "net_gamma": gamma_result.net_gamma,
                "total_call_gex": gamma_result.total_call_gex,
                "total_put_gex": gamma_result.total_put_gex
            }
        except Exception as e:
            results["gamma_pressure"] = {"status": "error", "error": str(e)}
        
        # Test Advanced Strategies
        try:
            test_chain = {
                "spot": 20000,
                "strikes": [
                    {"strike": 20000, "call_oi": 1000, "put_oi": 1200, "call_ltp": 150, "put_ltp": 140}
                ]
            }
            adv_result = run_advanced_strategies("NIFTY", test_chain)
            results["advanced_strategies"] = {
                "status": "success",
                "smc_detected": bool(adv_result.get("smc", {}).get("detected")),
                "ict_detected": bool(adv_result.get("ict", {}).get("detected")),
                "crt_detected": bool(adv_result.get("crt", {}).get("detected")),
                "msnr_detected": bool(adv_result.get("msnr", {}).get("signal"))
            }
        except Exception as e:
            results["advanced_strategies"] = {"status": "error", "error": str(e)}
        
        return {
            "status": "engines_tested",
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
    except Exception as e:
        diag("AI_TEST", f"AI engines test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/ai/signal")
async def debug_ai_signal():
    """
    Test AI signal generation
    Attempts to generate signals from current data
    """
    try:
        diag("AI_TEST", "Testing AI signal generation")
        
        ai_engine = AISignalEngine()
        
        # Get market snapshot
        market_data = ai_engine.get_latest_market_snapshot()
        
        if not market_data:
            return {
                "status": "no_data",
                "message": "No market data available for signal generation",
                "timestamp": datetime.now().isoformat()
            }
        
        # Generate signals
        signals_count = ai_engine.generate_signals()
        
        return {
            "status": "signals_generated",
            "timestamp": datetime.now().isoformat(),
            "market_data": {
                "symbol": market_data.get("symbol"),
                "spot_price": market_data.get("spot_price"),
                "pcr": market_data.get("pcr"),
                "total_call_oi": market_data.get("total_call_oi"),
                "total_put_oi": market_data.get("total_put_oi")
            },
            "signals_generated": signals_count
        }
    except Exception as e:
        diag("AI_TEST", f"AI signal test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/ai/health")
async def debug_ai_health():
    """
    AI system health check
    Returns overall system health status
    """
    try:
        diag("AI_TEST", "Running AI system health check")
        
        from app.core.ai_health_state import get_health
        
        health_status = get_health()
        
        return {
            "status": "health_check_complete",
            "timestamp": datetime.now().isoformat(),
            "ai_health": health_status,
            "summary": {
                "total_components": len(health_status),
                "healthy_components": sum(1 for healthy in health_status.values() if healthy),
                "unhealthy_components": sum(1 for healthy in health_status.values() if not healthy)
            }
        }
    except Exception as e:
        diag("AI_TEST", f"AI health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/ai/health/simple")
async def ai_health():
    """
    Simple AI health endpoint
    Returns just the AI health state
    """
    try:
        from app.core.ai_health_state import get_health
        return get_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
