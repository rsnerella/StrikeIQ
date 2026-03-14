"""
Monitoring API Endpoints - ML Pipeline Performance Monitoring
Provides API endpoints for accessing performance metrics and alerts
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel

from app.monitoring.performance_monitor import performance_monitor

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

class MetricsSummaryResponse(BaseModel):
    metric_name: str
    time_window_minutes: int
    sample_count: int
    latest_value: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    p50: Optional[float]
    p95: Optional[float]
    p99: Optional[float]
    unit: Optional[str]
    latest_timestamp: Optional[str]
    no_data: Optional[bool] = False

class AlertResponse(BaseModel):
    id: str
    type: str
    severity: str
    message: str
    timestamp: str
    acknowledged: bool
    acknowledged_at: Optional[str] = None
    data: Dict[str, Any]

class PerformanceDashboardResponse(BaseModel):
    timestamp: str
    metrics: Dict[str, MetricsSummaryResponse]
    active_alerts: Dict[str, AlertResponse]
    performance_score: float

@router.get("/dashboard", response_model=PerformanceDashboardResponse)
async def get_performance_dashboard():
    """Get comprehensive ML performance dashboard"""
    try:
        dashboard = await performance_monitor.get_ml_performance_dashboard()
        
        if 'error' in dashboard:
            raise HTTPException(status_code=500, detail=dashboard['error'])
        
        return dashboard
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance dashboard: {str(e)}")

@router.get("/metrics/{metric_name}", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    metric_name: str,
    time_window_minutes: int = Query(default=60, ge=1, le=1440, description="Time window in minutes (1-1440)")
):
    """Get metrics summary for a specific metric"""
    try:
        summary = await performance_monitor.get_metrics_summary(metric_name, time_window_minutes)
        
        if 'error' in summary:
            raise HTTPException(status_code=404, detail=summary['error'])
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics summary: {str(e)}")

@router.get("/metrics")
async def list_available_metrics():
    """List all available metrics"""
    try:
        available_metrics = list(performance_monitor.metrics_history.keys())
        
        return {
            "available_metrics": available_metrics,
            "thresholds": performance_monitor.thresholds
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing metrics: {str(e)}")

@router.get("/alerts")
async def get_active_alerts():
    """Get all active alerts"""
    try:
        return {
            "active_alerts": performance_monitor.active_alerts,
            "alert_count": len(performance_monitor.active_alerts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    try:
        success = await performance_monitor.acknowledge_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"message": f"Alert {alert_id} acknowledged"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

@router.post("/alerts/{alert_id}/clear")
async def clear_alert(alert_id: str):
    """Clear an alert"""
    try:
        success = await performance_monitor.clear_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"message": f"Alert {alert_id} cleared"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing alert: {str(e)}")

@router.post("/metrics/cleanup")
async def cleanup_old_metrics(days_to_keep: int = Query(default=7, ge=1, le=30)):
    """Clean up old metrics data"""
    try:
        removed_count = await performance_monitor.cleanup_old_metrics(days_to_keep)
        
        return {
            "message": f"Cleaned up {removed_count} old metrics",
            "days_kept": days_to_keep
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up metrics: {str(e)}")

@router.get("/export")
async def export_metrics(
    start_time: str = Query(..., description="Start time in ISO format"),
    end_time: str = Query(..., description="End time in ISO format"),
    metric_names: Optional[str] = Query(None, description="Comma-separated list of metric names")
):
    """Export metrics for analysis"""
    try:
        # Parse timestamps
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Parse metric names
        metrics_list = None
        if metric_names:
            metrics_list = [name.strip() for name in metric_names.split(',')]
        
        # Export metrics
        exported_metrics = await performance_monitor.export_metrics(start_dt, end_dt, metrics_list)
        
        return {
            "start_time": start_time,
            "end_time": end_time,
            "metric_names": metrics_list,
            "exported_count": len(exported_metrics),
            "metrics": exported_metrics
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting metrics: {str(e)}")

@router.get("/health")
async def monitoring_health():
    """Health check for monitoring system"""
    try:
        # Check if monitoring system is working
        dashboard = await performance_monitor.get_ml_performance_dashboard()
        
        health_status = {
            "status": "healthy" if 'error' not in dashboard else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics_count": len(performance_monitor.metrics_history),
            "active_alerts_count": len(performance_monitor.active_alerts),
            "performance_score": dashboard.get('performance_score', 0)
        }
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }
