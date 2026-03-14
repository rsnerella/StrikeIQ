"""
Options Data Enricher
Combines WebSocket LTP data with REST API data for complete options information
"""

import asyncio
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.token_manager import token_manager

logger = logging.getLogger(__name__)

class OptionsDataEnricher:
    """Enriches options data by combining WebSocket LTP with REST API data"""
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.cache: Dict[str, Dict] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.cache_ttl = 30.0  # 30 seconds cache to make system slower but more reliable
        self.last_api_call = 0.0
        self.api_call_interval = 1.0  # 1 second between API calls to avoid rate limiting
        
    async def get_session(self):
        """Get HTTP session for API calls"""
        if self.session is None or self.session.is_closed:
            self.session = httpx.AsyncClient(timeout=10.0)
        return self.session
    
    async def enrich_option_data(self, instrument_key: str, ltp: float) -> Dict[str, Any]:
        """
        Enrich option data using ONLY WebSocket data - API calls disabled
        Prioritizes WebSocket data completely to avoid any API dependency
        """
        now = datetime.now().timestamp()
        
        # Check cache first (but cache only WebSocket data)
        if (instrument_key in self.cache and 
            instrument_key in self.cache_expiry and 
            now - self.cache_expiry[instrument_key] < self.cache_ttl):
            
            cached_data = self.cache[instrument_key].copy()
            cached_data['ltp'] = ltp  # Update with latest WebSocket LTP (more recent)
            return cached_data
        
        # NO API CALLS - Use WebSocket-only data
        logger.info(f"Using WebSocket-only data for {instrument_key}")
        
        # WebSocket-only enriched data
        enriched_data = {
            "ltp": float(ltp),        # ✅ Real-time from WebSocket
            "bid": 0.0,              # ❌ Not available from WebSocket
            "ask": 0.0,              # ❌ Not available from WebSocket
            "bid_qty": 0,            # ❌ Not available from WebSocket
            "ask_qty": 0,            # ❌ Not available from WebSocket
            "oi": 0,                # ❌ Not available from WebSocket
            "oi_change": 0,          # ❌ Not available from WebSocket
            "volume": 0,            # ❌ Not available from WebSocket
            "iv": 0.0,              # ❌ Not available from WebSocket
            "delta": 0.0,           # ❌ Not available from WebSocket
            "theta": 0.0,           # ❌ Not available from WebSocket
            "gamma": 0.0,           # ❌ Not available from WebSocket
            "vega": 0.0,            # ❌ Not available from WebSocket
            "timestamp": datetime.now().timestamp(),
            "source": "websocket"   # ✅ WebSocket-only data
        }
        
        # Cache the WebSocket data
        self.cache[instrument_key] = enriched_data
        self.cache_expiry[instrument_key] = now
        
        logger.info(f"WebSocket-only enriched data for {instrument_key}: ltp={enriched_data['ltp']} (WebSocket)")
        return enriched_data
    
    def _websocket_fallback_data(self, ltp: float) -> Dict[str, Any]:
        """Fallback using WebSocket LTP when API is unavailable"""
        return {
            "ltp": float(ltp),
            "bid": 0.0,
            "ask": 0.0,
            "bid_qty": 0,
            "ask_qty": 0,
            "oi": 0,
            "oi_change": 0,
            "volume": 0,
            "iv": 0.0,
            "delta": 0.0,
            "theta": 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "timestamp": datetime.now().timestamp(),
            "source": "websocket"
        }
    
    def _fallback_data(self, ltp: float) -> Dict[str, Any]:
        """Fallback data when API call fails"""
        return {
            "ltp": float(ltp),
            "bid": 0.0,
            "ask": 0.0,
            "bid_qty": 0,
            "ask_qty": 0,
            "oi": 0,
            "oi_change": 0,
            "volume": 0,
            "iv": 0.0,
            "delta": 0.0,
            "theta": 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "timestamp": datetime.now().timestamp()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session and not self.session.is_closed:
            await self.session.aclose()

# Global instance
options_enricher = OptionsDataEnricher()
