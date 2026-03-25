"""
OI Heatmap Engine for StrikeIQ
Handles OI heatmap visualization and calculations
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OIHeatmapEngine:
    """OI Heatmap Engine for visualizing options interest"""
    
    def __init__(self):
        self.running = False
        self.task = None
        
    async def start(self):
        """Start the OI heatmap engine"""
        if self.running:
            return
            
        self.running = True
        logger.info("OI Heatmap Engine started")
        
    async def stop(self):
        """Stop the OI heatmap engine"""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("OI Heatmap Engine stopped")
        
    async def calculate_heatmap_data(self, symbol: str, option_chain: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate heatmap data from option chain"""
        try:
            heatmap_data = {
                "symbol": symbol,
                "timestamp": asyncio.get_event_loop().time(),
                "call_oi_heatmap": {},
                "put_oi_heatmap": {},
                "total_oi": 0
            }
            
            # Process option chain data
            if "strikes" in option_chain:
                for strike_data in option_chain["strikes"]:
                    if isinstance(strike_data, dict):
                        strike = strike_data.get("strike")
                        if strike:
                            # Call OI
                            call_oi = strike_data.get("CE", {}).get("oi", 0)
                            if call_oi > 0:
                                heatmap_data["call_oi_heatmap"][str(strike)] = call_oi
                                heatmap_data["total_oi"] += call_oi
                            
                            # Put OI
                            put_oi = strike_data.get("PE", {}).get("oi", 0)
                            if put_oi > 0:
                                heatmap_data["put_oi_heatmap"][str(strike)] = put_oi
                                heatmap_data["total_oi"] += put_oi
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Heatmap calculation failed: {e}")
            return {}
            
    async def get_heatmap_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current heatmap snapshot for symbol"""
        try:
            # This would typically fetch from cache or calculate fresh data
            return await self.calculate_heatmap_data(symbol, {})
        except Exception as e:
            logger.error(f"Failed to get heatmap snapshot: {e}")
            return None

# Global instance
oi_heatmap_engine = OIHeatmapEngine()
