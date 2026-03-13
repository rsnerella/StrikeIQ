"""
Analytics Broadcaster - Unified Analytics Broadcasting System
Consolidates analytics broadcasting, caching, and infrastructure services
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import weakref

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsMessage:
    """Unified analytics message"""
    message_type: str
    symbol: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    priority: str  # low, medium, high, critical
    ttl: Optional[int] = None  # Time to live in seconds

@dataclass
class BroadcastStats:
    """Broadcasting statistics"""
    messages_sent: int = 0
    messages_failed: int = 0
    subscribers_count: int = 0
    avg_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

class AnalyticsBroadcaster:
    """
    Unified Analytics Broadcaster
    
    Consolidates:
    - Analytics broadcasting
    - Message routing
    - Caching layer
    - Performance monitoring
    
    Features:
    - Real-time message broadcasting
    - Topic-based subscriptions
    - Message caching and deduplication
    - Performance monitoring
    - Rate limiting
    - Message prioritization
    """
    
    def __init__(self):
        # Subscriber management
        self.subscribers: Dict[str, Set[Callable]] = defaultdict(set)  # topic -> subscribers
        self.all_subscribers: Set[Callable] = set()  # All messages
        
        # Message queue and caching
        self.message_queue: deque = deque(maxlen=10000)
        self.message_cache: Dict[str, AnalyticsMessage] = {}
        self.cache_max_size = 1000
        self.cache_ttl = 300  # 5 minutes
        
        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, int]] = defaultdict(dict)  # topic -> {window: count}
        self.rate_limit_windows = [1, 10, 60]  # 1s, 10s, 1min windows
        self.rate_limits_config = {
            "default": {1: 10, 10: 50, 60: 200},  # Default limits
            "market_data": {1: 100, 10: 500, 60: 2000},  # High frequency data
            "alerts": {1: 5, 10: 20, 60: 100},  # Low frequency alerts
        }
        
        # Performance tracking
        self.stats = BroadcastStats()
        self.latency_samples: deque = deque(maxlen=1000)
        self.start_time = datetime.now(timezone.utc)
        
        # Message processing
        self.processing = False
        self.batch_size = 100
        self.batch_timeout = 0.1  # 100ms
        
        logger.info("AnalyticsBroadcaster initialized - Unified analytics broadcasting")
    
    def subscribe(self, topic: str, callback: Callable[[AnalyticsMessage], None]) -> None:
        """Subscribe to specific topic"""
        try:
            # Use weak reference to avoid memory leaks
            if hasattr(callback, '__self__'):
                # Method reference - use weak reference
                weak_ref = weakref.WeakMethod(callback)
                self.subscribers[topic].add(weak_ref)
            else:
                # Function reference - store directly (functions don't create cycles)
                self.subscribers[topic].add(callback)
            
            self.stats.subscribers_count = len(self.subscribers) + len(self.all_subscribers)
            logger.info(f"Subscribed to topic: {topic} (total subscribers: {self.stats.subscribers_count})")
            
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")
    
    def subscribe_all(self, callback: Callable[[AnalyticsMessage], None]) -> None:
        """Subscribe to all messages"""
        try:
            if hasattr(callback, '__self__'):
                weak_ref = weakref.WeakMethod(callback)
                self.all_subscribers.add(weak_ref)
            else:
                self.all_subscribers.add(callback)
            
            self.stats.subscribers_count = len(self.subscribers) + len(self.all_subscribers)
            logger.info(f"Subscribed to all topics (total subscribers: {self.stats.subscribers_count})")
            
        except Exception as e:
            logger.error(f"Error subscribing to all topics: {e}")
    
    def unsubscribe(self, topic: str, callback: Callable[[AnalyticsMessage], None]) -> None:
        """Unsubscribe from topic"""
        try:
            # Remove from topic subscribers
            if topic in self.subscribers:
                self.subscribers[topic].discard(callback)
                if not self.subscribers[topic]:
                    del self.subscribers[topic]
            
            # Remove from all subscribers
            self.all_subscribers.discard(callback)
            
            self.stats.subscribers_count = len(self.subscribers) + len(self.all_subscribers)
            logger.info(f"Unsubscribed from topic: {topic}")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from topic {topic}: {e}")
    
    async def broadcast(self, message: AnalyticsMessage) -> bool:
        """Broadcast message to subscribers"""
        try:
            start_time = datetime.now(timezone.utc)
            
            # Check rate limits
            if not self._check_rate_limit(message.message_type):
                logger.warning(f"Rate limit exceeded for topic: {message.message_type}")
                return False
            
            # Check for duplicates
            message_key = self._generate_message_key(message)
            if message_key in self.message_cache:
                # Update cached message if newer
                cached = self.message_cache[message_key]
                if message.timestamp > cached.timestamp:
                    self.message_cache[message_key] = message
                self.stats.cache_hits += 1
                return True
            else:
                self.stats.cache_misses += 1
            
            # Add to cache
            self.message_cache[message_key] = message
            self._cleanup_cache()
            
            # Add to queue
            self.message_queue.append(message)
            
            # Process immediately if not already processing
            if not self.processing:
                asyncio.create_task(self._process_message_queue())
            
            # Update stats
            self.stats.messages_sent += 1
            
            # Track latency
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self.latency_samples.append(latency)
            self.stats.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
            
            return True
            
        except Exception as e:
            self.stats.messages_failed += 1
            logger.error(f"Error broadcasting message: {e}")
            return False
    
    async def _process_message_queue(self) -> None:
        """Process message queue"""
        if self.processing:
            return
        
        self.processing = True
        
        try:
            while self.message_queue:
                # Process batch of messages
                batch = []
                for _ in range(self.batch_size):
                    if not self.message_queue:
                        break
                    batch.append(self.message_queue.popleft())
                
                if not batch:
                    break
                
                # Process batch
                await self._process_message_batch(batch)
                
                # Small delay to prevent blocking
                await asyncio.sleep(0.001)
                
        except Exception as e:
            logger.error(f"Error processing message queue: {e}")
        finally:
            self.processing = False
    
    async def _process_message_batch(self, messages: List[AnalyticsMessage]) -> None:
        """Process batch of messages"""
        try:
            # Group messages by topic
            topic_groups = defaultdict(list)
            for message in messages:
                topic_groups[message.message_type].append(message)
            
            # Process each topic group
            for topic, topic_messages in topic_groups.items():
                await self._deliver_messages(topic, topic_messages)
                
        except Exception as e:
            logger.error(f"Error processing message batch: {e}")
    
    async def _deliver_messages(self, topic: str, messages: List[AnalyticsMessage]) -> None:
        """Deliver messages to topic subscribers"""
        try:
            # Get subscribers for topic
            topic_subscribers = self.subscribers.get(topic, set())
            
            # Clean up weak references
            alive_subscribers = set()
            for sub in topic_subscribers:
                if isinstance(sub, weakref.WeakMethod):
                    if sub() is not None:
                        alive_subscribers.add(sub())
                else:
                    alive_subscribers.add(sub)
            
            # Update subscribers list
            self.subscribers[topic] = alive_subscribers
            
            # Add all subscribers
            all_subscribers = set()
            for sub in self.all_subscribers:
                if isinstance(sub, weakref.WeakMethod):
                    if sub() is not None:
                        all_subscribers.add(sub())
                else:
                    all_subscribers.add(sub)
            
            self.all_subscribers = all_subscribers
            
            # Combine subscribers
            combined_subscribers = alive_subscribers | all_subscribers
            
            # Deliver messages
            if combined_subscribers:
                for message in messages:
                    await self._deliver_to_subscribers(message, combined_subscribers)
                    
        except Exception as e:
            logger.error(f"Error delivering messages for topic {topic}: {e}")
    
    async def _deliver_to_subscribers(self, message: AnalyticsMessage, subscribers: Set[Callable]) -> None:
        """Deliver message to subscribers"""
        try:
            # Convert weak references back to callables
            alive_subscribers = []
            for sub in subscribers:
                if isinstance(sub, weakref.WeakMethod):
                    callback = sub()
                    if callback is not None:
                        alive_subscribers.append(callback)
                else:
                    alive_subscribers.append(sub)
            
            # Deliver to each subscriber
            for callback in alive_subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error delivering message to subscribers: {e}")
    
    def _check_rate_limit(self, topic: str) -> bool:
        """Check if rate limit allows message"""
        try:
            now = datetime.now(timezone.utc)
            limits = self.rate_limits_config.get(topic, self.rate_limits_config["default"])
            
            for window in self.rate_limit_windows:
                if window not in limits:
                    continue
                
                # Clean old entries
                cutoff_time = now - timedelta(seconds=window)
                self.rate_limits[topic] = {
                    k: v for k, v in self.rate_limits[topic].items()
                    if k > cutoff_time
                }
                
                # Count messages in window
                count = len(self.rate_limits[topic])
                if count >= limits[window]:
                    return False
                
                # Add current message
                self.rate_limits[topic][now] = True
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def _generate_message_key(self, message: AnalyticsMessage) -> str:
        """Generate unique key for message"""
        return f"{message.message_type}:{message.symbol}:{hash(json.dumps(message.data, sort_keys=True))}"
    
    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries"""
        try:
            now = datetime.now(timezone.utc)
            expired_keys = []
            
            for key, message in self.message_cache.items():
                if message.ttl and (now - message.timestamp).total_seconds() > message.ttl:
                    expired_keys.append(key)
                elif (now - message.timestamp).total_seconds() > self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.message_cache[key]
            
            # Limit cache size
            if len(self.message_cache) > self.cache_max_size:
                # Remove oldest entries
                items = sorted(self.message_cache.items(), key=lambda x: x[1].timestamp)
                for key, _ in items[:len(self.message_cache) - self.cache_max_size]:
                    del self.message_cache[key]
                    
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    async def broadcast_market_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """Convenience method for market data broadcasting"""
        message = AnalyticsMessage(
            message_type="market_data",
            symbol=symbol,
            data=data,
            timestamp=datetime.now(timezone.utc),
            source="market_feed",
            priority="medium",
            ttl=30  # 30 seconds TTL
        )
        return await self.broadcast(message)
    
    async def broadcast_signal(self, symbol: str, signal_data: Dict[str, Any]) -> bool:
        """Convenience method for signal broadcasting"""
        message = AnalyticsMessage(
            message_type="signal",
            symbol=symbol,
            data=signal_data,
            timestamp=datetime.now(timezone.utc),
            source="strategy_engine",
            priority="high",
            ttl=300  # 5 minutes TTL
        )
        return await self.broadcast(message)
    
    async def broadcast_alert(self, symbol: str, alert_data: Dict[str, Any], priority: str = "high") -> bool:
        """Convenience method for alert broadcasting"""
        message = AnalyticsMessage(
            message_type="alert",
            symbol=symbol,
            data=alert_data,
            timestamp=datetime.now(timezone.utc),
            source="risk_engine",
            priority=priority,
            ttl=600  # 10 minutes TTL
        )
        return await self.broadcast(message)
    
    async def broadcast_analysis(self, symbol: str, analysis_data: Dict[str, Any]) -> bool:
        """Convenience method for analysis broadcasting"""
        message = AnalyticsMessage(
            message_type="analysis",
            symbol=symbol,
            data=analysis_data,
            timestamp=datetime.now(timezone.utc),
            source="ai_engine",
            priority="medium",
            ttl=180  # 3 minutes TTL
        )
        return await self.broadcast(message)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get broadcasting statistics"""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        return {
            "messages_sent": self.stats.messages_sent,
            "messages_failed": self.stats.messages_failed,
            "success_rate": self.stats.messages_sent / max(self.stats.messages_sent + self.stats.messages_failed, 1),
            "subscribers_count": self.stats.subscribers_count,
            "avg_latency_ms": self.stats.avg_latency_ms,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "cache_hit_rate": self.stats.cache_hits / max(self.stats.cache_hits + self.stats.cache_misses, 1),
            "queue_size": len(self.message_queue),
            "cache_size": len(self.message_cache),
            "uptime_seconds": uptime,
            "messages_per_second": self.stats.messages_sent / max(uptime, 1),
            "topics": list(self.subscribers.keys()),
            "rate_limits": {topic: dict(limits) for topic, limits in self.rate_limits.items()}
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queue_size": len(self.message_queue),
            "processing": self.processing,
            "cache_size": len(self.message_cache),
            "cache_max_size": self.cache_max_size,
            "subscribers": {
                "total": self.stats.subscribers_count,
                "by_topic": {topic: len(subs) for topic, subs in self.subscribers.items()}
            }
        }
    
    def clear_cache(self) -> None:
        """Clear message cache"""
        self.message_cache.clear()
        logger.info("Cleared message cache")
    
    def clear_queue(self) -> None:
        """Clear message queue"""
        self.message_queue.clear()
        logger.info("Cleared message queue")
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down AnalyticsBroadcaster")
        
        # Clear all data
        self.clear_cache()
        self.clear_queue()
        self.subscribers.clear()
        self.all_subscribers.clear()
        self.rate_limits.clear()
        
        # Wait for processing to complete
        while self.processing:
            await asyncio.sleep(0.1)
        
        logger.info("AnalyticsBroadcaster shutdown complete")
