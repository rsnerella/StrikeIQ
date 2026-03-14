"""
Performance Monitor - ML Pipeline Performance Monitoring
Tracks and logs performance metrics for the ML system
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class MLInferenceMetrics:
    """ML inference performance metrics"""
    ai_inference_latency: float  # milliseconds
    prediction_accuracy: float
    feature_generation_time: float
    dataset_size: int
    model_version: str
    timestamp: datetime

@dataclass
class SystemMetrics:
    """System-level performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_io: float
    network_io: float
    active_connections: int
    timestamp: datetime

class PerformanceMonitor:
    """
    Performance Monitor for ML Pipeline
    
    Tracks:
    - AI inference latency
    - Prediction accuracy
    - Feature generation time
    - Dataset size
    - Model version
    - System resource usage
    """
    
    def __init__(self):
        # Metric storage
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Performance thresholds
        self.thresholds = {
            'ai_inference_latency': 100.0,  # ms
            'prediction_accuracy': 0.6,     # 60%
            'feature_generation_time': 50.0, # ms
            'cpu_usage': 80.0,              # 80%
            'memory_usage': 85.0            # 85%
        }
        
        # Alert tracking
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        
        logger.info("PerformanceMonitor initialized")
    
    async def record_inference_latency(
        self, 
        symbol: str, 
        latency_ms: float, 
        model_version: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record AI inference latency"""
        try:
            metric = PerformanceMetric(
                name='ai_inference_latency',
                value=latency_ms,
                unit='ms',
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'symbol': symbol,
                    'model_version': model_version,
                    **(metadata or {})
                }
            )
            
            self.metrics_history['ai_inference_latency'].append(metric)
            
            # Check threshold
            if latency_ms > self.thresholds['ai_inference_latency']:
                await self._trigger_alert('high_inference_latency', {
                    'symbol': symbol,
                    'latency_ms': latency_ms,
                    'threshold': self.thresholds['ai_inference_latency']
                })
            
            logger.debug(f"Recorded inference latency for {symbol}: {latency_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error recording inference latency: {e}")
    
    async def record_prediction_accuracy(
        self, 
        symbol: str, 
        accuracy: float,
        dataset_size: int,
        model_version: str
    ) -> None:
        """Record prediction accuracy"""
        try:
            metric = PerformanceMetric(
                name='prediction_accuracy',
                value=accuracy,
                unit='ratio',
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'symbol': symbol,
                    'dataset_size': dataset_size,
                    'model_version': model_version
                }
            )
            
            self.metrics_history['prediction_accuracy'].append(metric)
            
            # Check threshold
            if accuracy < self.thresholds['prediction_accuracy']:
                await self._trigger_alert('low_prediction_accuracy', {
                    'symbol': symbol,
                    'accuracy': accuracy,
                    'threshold': self.thresholds['prediction_accuracy']
                })
            
            logger.debug(f"Recorded prediction accuracy for {symbol}: {accuracy:.3f}")
            
        except Exception as e:
            logger.error(f"Error recording prediction accuracy: {e}")
    
    async def record_feature_generation_time(
        self, 
        symbol: str, 
        generation_time_ms: float,
        feature_count: int
    ) -> None:
        """Record feature generation time"""
        try:
            metric = PerformanceMetric(
                name='feature_generation_time',
                value=generation_time_ms,
                unit='ms',
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'symbol': symbol,
                    'feature_count': feature_count
                }
            )
            
            self.metrics_history['feature_generation_time'].append(metric)
            
            # Check threshold
            if generation_time_ms > self.thresholds['feature_generation_time']:
                await self._trigger_alert('slow_feature_generation', {
                    'symbol': symbol,
                    'generation_time_ms': generation_time_ms,
                    'threshold': self.thresholds['feature_generation_time']
                })
            
            logger.debug(f"Recorded feature generation time for {symbol}: {generation_time_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error recording feature generation time: {e}")
    
    async def record_dataset_size(self, symbol: str, dataset_size: int) -> None:
        """Record dataset size"""
        try:
            metric = PerformanceMetric(
                name='dataset_size',
                value=float(dataset_size),
                unit='samples',
                timestamp=datetime.now(timezone.utc),
                metadata={'symbol': symbol}
            )
            
            self.metrics_history['dataset_size'].append(metric)
            
            logger.debug(f"Recorded dataset size for {symbol}: {dataset_size}")
            
        except Exception as e:
            logger.error(f"Error recording dataset size: {e}")
    
    async def record_system_metrics(self, system_metrics: SystemMetrics) -> None:
        """Record system-level metrics"""
        try:
            # CPU usage
            cpu_metric = PerformanceMetric(
                name='cpu_usage',
                value=system_metrics.cpu_usage,
                unit='percent',
                timestamp=system_metrics.timestamp,
                metadata={}
            )
            self.metrics_history['cpu_usage'].append(cpu_metric)
            
            # Memory usage
            memory_metric = PerformanceMetric(
                name='memory_usage',
                value=system_metrics.memory_usage,
                unit='percent',
                timestamp=system_metrics.timestamp,
                metadata={}
            )
            self.metrics_history['memory_usage'].append(memory_metric)
            
            # Active connections
            connections_metric = PerformanceMetric(
                name='active_connections',
                value=float(system_metrics.active_connections),
                unit='count',
                timestamp=system_metrics.timestamp,
                metadata={}
            )
            self.metrics_history['active_connections'].append(connections_metric)
            
            # Check thresholds
            if system_metrics.cpu_usage > self.thresholds['cpu_usage']:
                await self._trigger_alert('high_cpu_usage', {
                    'cpu_usage': system_metrics.cpu_usage,
                    'threshold': self.thresholds['cpu_usage']
                })
            
            if system_metrics.memory_usage > self.thresholds['memory_usage']:
                await self._trigger_alert('high_memory_usage', {
                    'memory_usage': system_metrics.memory_usage,
                    'threshold': self.thresholds['memory_usage']
                })
            
            logger.debug(f"Recorded system metrics: CPU={system_metrics.cpu_usage:.1f}%, Memory={system_metrics.memory_usage:.1f}%")
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {e}")
    
    async def get_metrics_summary(
        self, 
        metric_name: str, 
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get metrics summary for a specific metric"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            
            metrics = self.metrics_history.get(metric_name, deque())
            recent_metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            if not recent_metrics:
                return {
                    'metric_name': metric_name,
                    'time_window_minutes': time_window_minutes,
                    'sample_count': 0,
                    'no_data': True
                }
            
            values = [m.value for m in recent_metrics]
            
            summary = {
                'metric_name': metric_name,
                'time_window_minutes': time_window_minutes,
                'sample_count': len(recent_metrics),
                'latest_value': values[-1],
                'min_value': min(values),
                'max_value': max(values),
                'avg_value': sum(values) / len(values),
                'latest_timestamp': recent_metrics[-1].timestamp.isoformat(),
                'unit': recent_metrics[-1].unit
            }
            
            # Add percentile calculations
            sorted_values = sorted(values)
            summary['p50'] = sorted_values[len(sorted_values) // 2]  # Median
            summary['p95'] = sorted_values[int(len(sorted_values) * 0.95)]
            summary['p99'] = sorted_values[int(len(sorted_values) * 0.99)]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting metrics summary for {metric_name}: {e}")
            return {'error': str(e)}
    
    async def get_ml_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive ML performance dashboard"""
        try:
            dashboard = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': {}
            }
            
            # ML-specific metrics
            ml_metrics = ['ai_inference_latency', 'prediction_accuracy', 'feature_generation_time', 'dataset_size']
            
            for metric_name in ml_metrics:
                summary = await self.get_metrics_summary(metric_name, 60)  # Last hour
                dashboard['metrics'][metric_name] = summary
            
            # System metrics
            system_metrics = ['cpu_usage', 'memory_usage', 'active_connections']
            
            for metric_name in system_metrics:
                summary = await self.get_metrics_summary(metric_name, 60)
                dashboard['metrics'][metric_name] = summary
            
            # Active alerts
            dashboard['active_alerts'] = self.active_alerts
            
            # Performance score
            dashboard['performance_score'] = self._calculate_performance_score(dashboard['metrics'])
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error getting ML performance dashboard: {e}")
            return {'error': str(e)}
    
    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        try:
            score = 100.0
            
            # Inference latency (lower is better)
            latency_metric = metrics.get('ai_inference_latency', {})
            if latency_metric.get('avg_value'):
                latency_ratio = latency_metric['avg_value'] / self.thresholds['ai_inference_latency']
                if latency_ratio > 1:
                    score -= min(20, (latency_ratio - 1) * 20)
            
            # Prediction accuracy (higher is better)
            accuracy_metric = metrics.get('prediction_accuracy', {})
            if accuracy_metric.get('avg_value'):
                accuracy_ratio = accuracy_metric['avg_value'] / self.thresholds['prediction_accuracy']
                if accuracy_ratio < 1:
                    score -= min(20, (1 - accuracy_ratio) * 20)
            
            # Feature generation time (lower is better)
            feature_metric = metrics.get('feature_generation_time', {})
            if feature_metric.get('avg_value'):
                feature_ratio = feature_metric['avg_value'] / self.thresholds['feature_generation_time']
                if feature_ratio > 1:
                    score -= min(15, (feature_ratio - 1) * 15)
            
            # System resources (lower is better)
            cpu_metric = metrics.get('cpu_usage', {})
            if cpu_metric.get('avg_value'):
                cpu_ratio = cpu_metric['avg_value'] / self.thresholds['cpu_usage']
                if cpu_ratio > 1:
                    score -= min(15, (cpu_ratio - 1) * 15)
            
            memory_metric = metrics.get('memory_usage', {})
            if memory_metric.get('avg_value'):
                memory_ratio = memory_metric['avg_value'] / self.thresholds['memory_usage']
                if memory_ratio > 1:
                    score -= min(15, (memory_ratio - 1) * 15)
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 50.0  # Default score
    
    async def _trigger_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> None:
        """Trigger performance alert"""
        try:
            alert_id = f"{alert_type}_{int(time.time())}"
            
            alert = {
                'id': alert_id,
                'type': alert_type,
                'severity': self._get_alert_severity(alert_type),
                'message': self._format_alert_message(alert_type, alert_data),
                'data': alert_data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'acknowledged': False
            }
            
            self.active_alerts[alert_id] = alert
            
            logger.warning(f"Performance alert triggered: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """Get alert severity level"""
        severity_map = {
            'high_inference_latency': 'warning',
            'low_prediction_accuracy': 'critical',
            'slow_feature_generation': 'warning',
            'high_cpu_usage': 'warning',
            'high_memory_usage': 'critical'
        }
        return severity_map.get(alert_type, 'info')
    
    def _format_alert_message(self, alert_type: str, alert_data: Dict[str, Any]) -> str:
        """Format alert message"""
        message_templates = {
            'high_inference_latency': "High inference latency for {symbol}: {latency_ms:.2f}ms (threshold: {threshold}ms)",
            'low_prediction_accuracy': "Low prediction accuracy for {symbol}: {accuracy:.2%} (threshold: {threshold:.2%})",
            'slow_feature_generation': "Slow feature generation for {symbol}: {generation_time_ms:.2f}ms (threshold: {threshold}ms)",
            'high_cpu_usage': "High CPU usage: {cpu_usage:.1f}% (threshold: {threshold}%)",
            'high_memory_usage': "High memory usage: {memory_usage:.1f}% (threshold: {threshold}%)"
        }
        
        template = message_templates.get(alert_type, f"Alert: {alert_type}")
        
        try:
            return template.format(**alert_data)
        except KeyError:
            return f"Alert: {alert_type} - {alert_data}"
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id]['acknowledged'] = True
                self.active_alerts[alert_id]['acknowledged_at'] = datetime.now(timezone.utc).isoformat()
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    async def clear_alert(self, alert_id: str) -> bool:
        """Clear an alert"""
        try:
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
                logger.info(f"Alert cleared: {alert_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing alert: {e}")
            return False
    
    async def export_metrics(
        self, 
        start_time: datetime, 
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Export metrics for analysis"""
        try:
            exported_metrics = []
            
            metrics_to_export = metric_names or list(self.metrics_history.keys())
            
            for metric_name in metrics_to_export:
                metrics = self.metrics_history.get(metric_name, deque())
                
                for metric in metrics:
                    if start_time <= metric.timestamp <= end_time:
                        exported_data = asdict(metric)
                        exported_metrics.append(exported_data)
            
            logger.info(f"Exported {len(exported_metrics)} metrics for analysis")
            return exported_metrics
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return []
    
    async def cleanup_old_metrics(self, days_to_keep: int = 7) -> int:
        """Clean up old metrics data"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            removed_count = 0
            
            for metric_name, metrics in self.metrics_history.items():
                original_count = len(metrics)
                
                # Filter out old metrics
                filtered_metrics = deque(
                    (m for m in metrics if m.timestamp >= cutoff_time),
                    maxlen=1000
                )
                
                self.metrics_history[metric_name] = filtered_metrics
                removed_count += original_count - len(filtered_metrics)
            
            logger.info(f"Cleaned up {removed_count} old metrics (kept last {days_to_keep} days)")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
            return 0

# Global instance
performance_monitor = PerformanceMonitor()

# Decorator for performance monitoring
def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                
                # Record the metric
                await performance_monitor.record_inference_latency(
                    symbol='unknown',
                    latency_ms=latency_ms,
                    model_version='unknown',
                    metadata={'function': func.__name__}
                )
        
        return wrapper
    return decorator
