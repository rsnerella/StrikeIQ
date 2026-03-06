"""
AI Status API endpoints for StrikeIQ frontend

Provides:
- GET /api/v1/ai/status - Overall AI system status
- GET /api/v1/ai/dashboard - Detailed dashboard data
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from ai.ai_db import ai_db
from app.services.ai_signal_engine import ai_signal_engine
from app.services.paper_trade_engine import paper_trade_engine
from app.services.ai_outcome_engine import ai_outcome_engine
from app.services.ai_learning_engine import ai_learning_engine
from ai.scheduler import ai_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai"])

@router.get("/status", summary="Get AI system status")
async def get_ai_status():
    """
    Get overall AI system status for UI display
    
    Returns:
        JSON with AI running status and key metrics
    """
    try:
        # Get active predictions count
        active_predictions_query = """
            SELECT COUNT(*) 
            FROM prediction_log 
            WHERE prediction_time >= NOW() - INTERVAL '1 hour'
            AND outcome_checked = FALSE
        """
        active_predictions_result = ai_db.fetch_one(active_predictions_query)
        active_predictions = active_predictions_result[0] if active_predictions_result else 0
        
        # Get open paper trades count
        open_trades_query = """
            SELECT COUNT(*) 
            FROM paper_trade_log 
            WHERE trade_status = 'OPEN'
        """
        open_trades_result = ai_db.fetch_one(open_trades_query)
        open_paper_trades = open_trades_result[0] if open_trades_result else 0
        
        # Get total predictions today
        today_predictions_query = """
            SELECT COUNT(*) 
            FROM prediction_log 
            WHERE DATE(prediction_time) = CURRENT_DATE
        """
        today_predictions_result = ai_db.fetch_one(today_predictions_query)
        total_predictions_today = today_predictions_result[0] if today_predictions_result else 0
        
        # Get last AI event
        last_event_query = """
            SELECT event_type, description, created_at
            FROM ai_event_log
            ORDER BY created_at DESC
            LIMIT 1
        """
        last_event_result = ai_db.fetch_one(last_event_query)
        
        if last_event_result:
            ai_last_event = {
                'type': last_event_result[0],
                'description': last_event_result[1],
                'timestamp': last_event_result[2].isoformat() if last_event_result[2] else None
            }
        else:
            ai_last_event = None
        
        # Check if scheduler is running
        scheduler_jobs = ai_scheduler.get_job_status()
        ai_running = len(scheduler_jobs) > 0
        
        return {
            "ai_running": ai_running,
            "active_predictions": active_predictions,
            "open_paper_trades": open_paper_trades,
            "total_predictions_today": total_predictions_today,
            "ai_last_event": ai_last_event,
            "scheduler_jobs": len(scheduler_jobs),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI status")

@router.get("/dashboard", summary="Get AI dashboard data")
async def get_ai_dashboard():
    """
    Get detailed dashboard data for AI analytics
    
    Returns:
        JSON with recent predictions, paper trades, and formula performance
    """
    try:
        # Get recent predictions (last 24 hours)
        recent_predictions_query = """
            SELECT p.id, p.formula_id, p.signal, p.confidence, p.nifty_spot, 
                   p.prediction_time, o.outcome, o.evaluation_time
            FROM prediction_log p
            LEFT JOIN outcome_log o ON p.id = o.prediction_id
            WHERE p.prediction_time >= NOW() - INTERVAL '24 hours'
            AND p.signal IN ('BUY', 'SELL')
            ORDER BY p.prediction_time DESC
            LIMIT 20
        """
        
        recent_predictions_results = ai_db.fetch_query(recent_predictions_query)
        recent_predictions = []
        
        for row in recent_predictions_results:
            recent_predictions.append({
                'id': row[0],
                'formula_id': row[1],
                'signal': row[2],
                'confidence': row[3],
                'nifty_spot': row[4],
                'prediction_time': row[5].isoformat() if row[5] else None,
                'outcome': row[6],
                'evaluation_time': row[7].isoformat() if row[7] else None
            })
        
        # Get recent paper trades (last 24 hours)
        recent_trades_query = """
            SELECT id, prediction_id, symbol, strike_price, option_type,
                   entry_price, exit_price, quantity, pnl, trade_status,
                   entry_time, exit_time
            FROM paper_trade_log
            WHERE entry_time >= NOW() - INTERVAL '24 hours'
            ORDER BY entry_time DESC
            LIMIT 20
        """
        
        recent_trades_results = ai_db.fetch_query(recent_trades_query)
        recent_paper_trades = []
        
        for row in recent_trades_results:
            recent_paper_trades.append({
                'id': row[0],
                'prediction_id': row[1],
                'symbol': row[2],
                'strike_price': row[3],
                'option_type': row[4],
                'entry_price': row[5],
                'exit_price': row[6],
                'quantity': row[7],
                'pnl': row[8],
                'trade_status': row[9],
                'entry_time': row[10].isoformat() if row[10] else None,
                'exit_time': row[11].isoformat() if row[11] else None
            })
        
        # Get formula performance
        formula_performance_query = """
            SELECT fm.id, fm.formula_name, fm.formula_type, fm.is_active,
                   COALESCE(fe.total_tests, 0) as total_tests,
                   COALESCE(fe.wins, 0) as wins,
                   COALESCE(fe.losses, 0) as losses,
                   COALESCE(fe.success_rate, 0.0) as success_rate,
                   COALESCE(fe.experience_adjusted_confidence, 0.0) as adjusted_confidence,
                   fe.last_updated
            FROM formula_master fm
            LEFT JOIN formula_experience fe ON fm.id = fe.formula_id
            ORDER BY fm.id
        """
        
        formula_performance_results = ai_db.fetch_query(formula_performance_query)
        formula_performance = []
        
        for row in formula_performance_results:
            formula_performance.append({
                'formula_id': row[0],
                'formula_name': row[1],
                'formula_type': row[2],
                'is_active': row[3],
                'total_tests': row[4],
                'wins': row[5],
                'losses': row[6],
                'success_rate': row[7],
                'adjusted_confidence': row[8],
                'last_updated': row[9].isoformat() if row[9] else None
            })
        
        # Get outcome statistics
        outcome_stats = ai_outcome_engine.get_outcome_statistics(days=7)
        
        # Get learning statistics
        learning_stats = ai_learning_engine.get_learning_statistics()
        
        # Get scheduler job status
        scheduler_jobs = ai_scheduler.get_job_status()
        
        return {
            "recent_predictions": recent_predictions,
            "recent_paper_trades": recent_paper_trades,
            "formula_performance": formula_performance,
            "outcome_statistics": outcome_stats,
            "learning_statistics": learning_stats,
            "scheduler_jobs": scheduler_jobs,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting AI dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI dashboard data")

@router.get("/predictions", summary="Get recent predictions")
async def get_recent_predictions(limit: int = 50, hours: int = 24):
    """
    Get recent predictions with optional filtering
    
    Args:
        limit: Maximum number of predictions to return
        hours: Number of hours to look back
    
    Returns:
        List of recent predictions
    """
    try:
        query = """
            SELECT p.id, p.formula_id, p.signal, p.confidence, p.nifty_spot, 
                   p.prediction_time, o.outcome, o.evaluation_time, o.confidence as outcome_confidence
            FROM prediction_log p
            LEFT JOIN outcome_log o ON p.id = o.prediction_id
            WHERE p.prediction_time >= NOW() - INTERVAL %s
            AND p.signal IN ('BUY', 'SELL')
            ORDER BY p.prediction_time DESC
            LIMIT %s
        """
        
        results = ai_db.fetch_query(query, (f"{hours} hours", limit))
        
        predictions = []
        for row in results:
            predictions.append({
                'id': row[0],
                'formula_id': row[1],
                'signal': row[2],
                'confidence': row[3],
                'nifty_spot': row[4],
                'prediction_time': row[5].isoformat() if row[5] else None,
                'outcome': row[6],
                'evaluation_time': row[7].isoformat() if row[7] else None,
                'outcome_confidence': row[8]
            })
        
        return {
            "predictions": predictions,
            "count": len(predictions),
            "hours": hours,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent predictions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent predictions")

@router.get("/trades", summary="Get recent paper trades")
async def get_recent_trades(limit: int = 50, hours: int = 24):
    """
    Get recent paper trades with optional filtering
    
    Args:
        limit: Maximum number of trades to return
        hours: Number of hours to look back
    
    Returns:
        List of recent paper trades
    """
    try:
        query = """
            SELECT pt.id, pt.prediction_id, pt.symbol, pt.strike_price, pt.option_type,
                   pt.entry_price, pt.exit_price, pt.quantity, pt.pnl, pt.trade_status,
                   pt.entry_time, pt.exit_time,
                   p.signal as prediction_signal, p.confidence as prediction_confidence
            FROM paper_trade_log pt
            LEFT JOIN prediction_log p ON pt.prediction_id = p.id
            WHERE pt.entry_time >= NOW() - INTERVAL %s
            ORDER BY pt.entry_time DESC
            LIMIT %s
        """
        
        results = ai_db.fetch_query(query, (f"{hours} hours", limit))
        
        trades = []
        for row in results:
            trades.append({
                'id': row[0],
                'prediction_id': row[1],
                'symbol': row[2],
                'strike_price': row[3],
                'option_type': row[4],
                'entry_price': row[5],
                'exit_price': row[6],
                'quantity': row[7],
                'pnl': row[8],
                'trade_status': row[9],
                'entry_time': row[10].isoformat() if row[10] else None,
                'exit_time': row[11].isoformat() if row[11] else None,
                'prediction_signal': row[12],
                'prediction_confidence': row[13]
            })
        
        return {
            "trades": trades,
            "count": len(trades),
            "hours": hours,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent trades")

@router.get("/events", summary="Get AI event log")
async def get_ai_events(limit: int = 100, hours: int = 24):
    """
    Get recent AI events
    
    Args:
        limit: Maximum number of events to return
        hours: Number of hours to look back
    
    Returns:
        List of recent AI events
    """
    try:
        query = """
            SELECT id, event_type, description, created_at
            FROM ai_event_log
            WHERE created_at >= NOW() - INTERVAL %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        results = ai_db.fetch_query(query, (f"{hours} hours", limit))
        
        events = []
        for row in results:
            events.append({
                'id': row[0],
                'event_type': row[1],
                'description': row[2],
                'created_at': row[3].isoformat() if row[3] else None
            })
        
        return {
            "events": events,
            "count": len(events),
            "hours": hours,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting AI events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI events")
