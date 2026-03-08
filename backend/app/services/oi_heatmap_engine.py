"""
OI Heatmap Engine for StrikeIQ
Calculates OI distribution and intensity for heatmap visualization
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class OIHeatmapEngine:
    """Computes OI heatmap data for option chain visualization"""
    
    def __init__(self):
        # Background task for periodic updates
        self._heatmap_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Cache for last computed heatmaps
        self.heatmap_cache: Dict[str, Dict[str, Any]] = {}
        
        # Update interval (3 seconds)
        self.update_interval = 3.0
    
    async def start(self):
        """Start the background heatmap computation task"""
        if self._running:
            return
        
        self._running = True
        self._heatmap_task = asyncio.create_task(self._heatmap_loop())
        logger.info("OI heatmap engine started")
    
    async def stop(self):
        """Stop the background task"""
        self._running = False
        if self._heatmap_task:
            self._heatmap_task.cancel()
            try:
                await self._heatmap_task
            except asyncio.CancelledError:
                pass
        logger.info("OI heatmap engine stopped")
    
    async def _heatmap_loop(self):
        """Periodic heatmap computation"""
        try:
            while self._running:
                try:
                    await asyncio.sleep(self.update_interval)
                    await self._compute_and_broadcast_heatmaps()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in heatmap loop: {e}")
        except asyncio.CancelledError:
            logger.info("Heatmap loop stopped")
            raise
    
    async def _compute_and_broadcast_heatmaps(self):
        """Compute heatmaps for all active symbols"""
        try:
            # Get option chain data
            from app.services.option_chain_builder import option_chain_builder
            
            for symbol in ["NIFTY", "BANKNIFTY"]:  # Active symbols
                chain_data = option_chain_builder.get_chain(symbol)
                if chain_data:
                    heatmap_data = self._compute_heatmap(chain_data)
                    if heatmap_data:
                        await self._broadcast_heatmap(heatmap_data)
                        
        except Exception as e:
            logger.error(f"Error computing heatmaps: {e}")
    
    def _compute_heatmap(self, chain_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Compute heatmap data from option chain"""
        try:
            symbol = chain_data["symbol"]
            spot = chain_data["spot"]
            atm_strike = chain_data["atm_strike"]
            strikes = chain_data["strikes"]
            
            if not strikes:
                return None
            
            # Calculate total OI for calls and puts
            total_call_oi = sum(strike["call_oi"] for strike in strikes)
            total_put_oi = sum(strike["put_oi"] for strike in strikes)
            
            # Calculate PCR
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
            
            # Calculate OI intensities
            heatmap_entries = []
            max_call_oi = max(strike["call_oi"] for strike in strikes) if strikes else 1
            max_put_oi = max(strike["put_oi"] for strike in strikes) if strikes else 1
            
            for strike in strikes:
                # Normalize OI intensities (0-1 range)
                call_intensity = strike["call_oi"] / max_call_oi if max_call_oi > 0 else 0
                put_intensity = strike["put_oi"] / max_put_oi if max_put_oi > 0 else 0
                
                # Calculate distance from ATM (in percentage)
                distance_from_atm = abs(strike["strike"] - atm_strike) / atm_strike * 100
                
                entry = {
                    "strike": strike["strike"],
                    "call_oi_intensity": round(call_intensity, 3),
                    "put_oi_intensity": round(put_intensity, 3),
                    "distance_from_atm": round(distance_from_atm, 2),
                    "call_oi": strike["call_oi"],
                    "put_oi": strike["put_oi"],
                    "total_oi": strike["call_oi"] + strike["put_oi"]
                }
                
                heatmap_entries.append(entry)
            
            # Sort by strike
            heatmap_entries.sort(key=lambda x: x["strike"])
            
            heatmap_data = {
                "type": "heatmap_update",
                "symbol": symbol,
                "timestamp": int(datetime.now().timestamp()),
                "data": {
                    "symbol": symbol,
                    "spot": spot,
                    "atm_strike": atm_strike,
                    "pcr": round(pcr, 3),
                    "total_call_oi": total_call_oi,
                    "total_put_oi": total_put_oi,
                    "heatmap": heatmap_entries
                }
            }
            
            # Cache the result
            self.heatmap_cache[symbol] = heatmap_data
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Error computing heatmap for {chain_data.get('symbol', 'unknown')}: {e}")
            return None
    
    async def _broadcast_heatmap(self, heatmap_data: Dict[str, Any]):
        """Broadcast heatmap to WebSocket clients"""
        try:
            from app.core.ws_manager import manager
            
            await manager.broadcast(heatmap_data)
            logger.debug(f"Broadcasted heatmap for {heatmap_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Error broadcasting heatmap: {e}")
    
    def get_cached_heatmap(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached heatmap data for a symbol"""
        return self.heatmap_cache.get(symbol)
    
    def _calculate_oi_concentration(self, strikes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate OI concentration metrics"""
        try:
            # Group strikes by distance from ATM
            atm_distances = {
                "atm": [],      # ±2% from ATM
                "near": [],     # 2-5% from ATM
                "far": []       # >5% from ATM
            }
            
            # This would need ATM strike, for now use middle strike
            if not strikes:
                return {}
            
            middle_strike = strikes[len(strikes)//2]["strike"]
            
            for strike in strikes:
                distance_pct = abs(strike["strike"] - middle_strike) / middle_strike * 100
                
                total_oi = strike["call_oi"] + strike["put_oi"]
                
                if distance_pct <= 2:
                    atm_distances["atm"].append(total_oi)
                elif distance_pct <= 5:
                    atm_distances["near"].append(total_oi)
                else:
                    atm_distances["far"].append(total_oi)
            
            # Calculate concentration percentages
            total_oi_all = sum(sum(oi_list) for oi_list in atm_distances.values())
            
            if total_oi_all > 0:
                concentration = {
                    "atm_concentration": sum(atm_distances["atm"]) / total_oi_all,
                    "near_concentration": sum(atm_distances["near"]) / total_oi_all,
                    "far_concentration": sum(atm_distances["far"]) / total_oi_all
                }
                
                return {k: round(v, 3) for k, v in concentration.items()}
            
            return {}
            
        except Exception as e:
            logger.error(f"Error calculating OI concentration: {e}")
            return {}
    
    def _identify_max_pain_levels(self, strikes: List[Dict[str, Any]]) -> List[float]:
        """Identify potential max pain levels (simplified version)"""
        try:
            # Simple heuristic: strikes with highest combined OI
            if not strikes:
                return []
            
            # Sort by total OI
            sorted_strikes = sorted(
                strikes,
                key=lambda s: s["call_oi"] + s["put_oi"],
                reverse=True
            )
            
            # Return top 3 levels
            return [strike["strike"] for strike in sorted_strikes[:3]]
            
        except Exception as e:
            logger.error(f"Error identifying max pain levels: {e}")
            return []

# Global instance
oi_heatmap_engine = OIHeatmapEngine()
