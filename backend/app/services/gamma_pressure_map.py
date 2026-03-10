"""
Gamma Pressure Map
Computes strike-level gamma analysis for magnets and cliffs
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from app.core.diagnostics import diag
from app.core.ai_health_state import mark_health

logger = logging.getLogger(__name__)

@dataclass
class GammaPressurePoint:
    """Individual strike gamma analysis"""
    strike: float
    call_gex: float
    put_gex: float
    net_gex: float
    distance_from_spot: float
    pressure_type: str  # "magnet" or "cliff"
    pressure_strength: float  # 0-100 strength rating

@dataclass
class GammaPressureMap:
    """Complete gamma pressure analysis"""
    symbol: str
    spot: float
    total_call_gex: float
    total_put_gex: float
    net_gamma: float
    
    # Top pressure points
    top_magnets: List[GammaPressurePoint]
    top_cliffs: List[GammaPressurePoint]
    
    # Key levels
    strongest_magnet: Optional[GammaPressurePoint]
    strongest_cliff: Optional[GammaPressurePoint]
    gamma_flip_zone: Tuple[float, float]  # (lower_bound, upper_bound)
    
    # Pressure distribution
    pressure_distribution: Dict[str, float]  # magnet vs cliff balance

class GammaPressureMapEngine:
    """
    Computes gamma pressure maps for trading intelligence
    """
    
    def __init__(self):
        self.CONTRACT_MULTIPLIER = 75  # NFO options contract multiplier
        
    def compute_pressure_map(self, symbol: str, frontend_data: Dict[str, Any]) -> GammaPressureMap:
        """
        Compute complete gamma pressure map
        """
        try:
            spot = frontend_data.get("spot", 0)
            strikes = frontend_data.get("strikes", {})
            
            if not spot or not strikes:
                return self._create_empty_map(symbol, spot)
            
            # Calculate GEX for each strike
            pressure_points = []
            total_call_gex = 0
            total_put_gex = 0
            
            for strike, strike_data in strikes.items():
                call_data = strike_data.get("call", {})
                put_data = strike_data.get("put", {})
                
                # Calculate GEX for this strike
                call_gex = 0
                put_gex = 0
                
                if call_data.get("gamma") and call_data.get("oi"):
                    call_gex = call_data["gamma"] * call_data["oi"] * self.CONTRACT_MULTIPLIER
                
                if put_data.get("gamma") and put_data.get("oi"):
                    put_gex = put_data["gamma"] * put_data["oi"] * self.CONTRACT_MULTIPLIER
                
                net_gex = call_gex - put_gex
                distance_from_spot = abs(strike - spot)
                
                # Classify pressure type
                pressure_type, pressure_strength = self._classify_pressure(
                    net_gex, distance_from_spot, spot
                )
                
                pressure_point = GammaPressurePoint(
                    strike=strike,
                    call_gex=call_gex,
                    put_gex=put_gex,
                    net_gex=net_gex,
                    distance_from_spot=distance_from_spot,
                    pressure_type=pressure_type,
                    pressure_strength=pressure_strength
                )
                
                pressure_points.append(pressure_point)
                total_call_gex += call_gex
                total_put_gex += put_gex
            
            # Analyze pressure points
            magnets = [p for p in pressure_points if p.pressure_type == "magnet"]
            cliffs = [p for p in pressure_points if p.pressure_type == "cliff"]
            
            # Sort by strength
            magnets.sort(key=lambda x: x.pressure_strength, reverse=True)
            cliffs.sort(key=lambda x: x.pressure_strength, reverse=True)
            
            # Get top 5 of each
            top_magnets = magnets[:5]
            top_cliffs = cliffs[:5]
            
            # Find strongest
            strongest_magnet = magnets[0] if magnets else None
            strongest_cliff = cliffs[0] if cliffs else None
            
            # Calculate gamma flip zone
            gamma_flip_zone = self._calculate_gamma_flip_zone(pressure_points, spot)
            
            # Calculate pressure distribution
            pressure_distribution = self._calculate_pressure_distribution(
                total_call_gex, total_put_gex
            )
            
            return GammaPressureMap(
                symbol=symbol,
                spot=spot,
                total_call_gex=total_call_gex,
                total_put_gex=total_put_gex,
                net_gamma=total_call_gex - total_put_gex,
                top_magnets=top_magnets,
                top_cliffs=top_cliffs,
                strongest_magnet=strongest_magnet,
                strongest_cliff=strongest_cliff,
                gamma_flip_zone=gamma_flip_zone,
                pressure_distribution=pressure_distribution
            )
            
            # Add diagnostic logging for gamma calculation
            diag("AI_TEST", f"Gamma calculated: {total_call_gex - total_put_gex}")
            
            # Mark gamma engine as healthy
            mark_health("gamma")
            
        except Exception as e:
            logger.error(f"Error computing pressure map for {symbol}: {e}")
            return self._create_empty_map(symbol, frontend_data.get("spot", 0))
    
    def _classify_pressure(self, net_gex: float, distance_from_spot: float, spot: float) -> Tuple[str, float]:
        """
        Classify pressure type and strength
        """
        try:
            # Base strength from GEX magnitude
            gex_strength = abs(net_gex) / 1000000  # Normalize to millions
            
            # Distance decay factor (closer = stronger)
            distance_factor = max(0.1, 1 - (distance_from_spot / (spot * 0.05)))  # 5% of spot as reference
            
            # Combined strength
            strength = min(100, gex_strength * distance_factor * 10)
            
            # Classify type
            if net_gex > 0:
                return "magnet", strength  # Positive GEX attracts price
            else:
                return "cliff", strength   # Negative GEX repels price
                
        except Exception as e:
            logger.error(f"Error classifying pressure: {e}")
            return "neutral", 0
    
    def _calculate_gamma_flip_zone(self, pressure_points: List[GammaPressurePoint], spot: float) -> Tuple[float, float]:
        """
        Calculate the gamma flip zone (where pressure changes)
        """
        try:
            if not pressure_points:
                return (0, 0)
            
            # Sort by strike
            sorted_points = sorted(pressure_points, key=lambda x: x.strike)
            
            # Find cumulative GEX crossing point
            cumulative_gex = 0
            flip_strikes = []
            
            for point in sorted_points:
                cumulative_gex += point.net_gex
                
                # Check for sign change around zero
                if abs(cumulative_gex) < 1000000:  # Within 1M of zero
                    flip_strikes.append(point.strike)
            
            if flip_strikes:
                # Calculate zone bounds
                min_flip = min(flip_strikes)
                max_flip = max(flip_strikes)
                zone_width = max_flip - min_flip
                
                # Expand zone slightly for buffer
                buffer = max(25, zone_width * 0.2)
                return (min_flip - buffer, max_flip + buffer)
            else:
                # No clear flip zone, return spot ± 50
                return (spot - 50, spot + 50)
                
        except Exception as e:
            logger.error(f"Error calculating gamma flip zone: {e}")
            return (0, 0)
    
    def _calculate_pressure_distribution(self, total_call_gex: float, total_put_gex: float) -> Dict[str, float]:
        """
        Calculate pressure distribution balance
        """
        try:
            total_gex = abs(total_call_gex) + abs(total_put_gex)
            
            if total_gex == 0:
                return {"call_pressure": 50, "put_pressure": 50, "balance": "neutral"}
            
            call_pressure_pct = (abs(total_call_gex) / total_gex) * 100
            put_pressure_pct = (abs(total_put_gex) / total_gex) * 100
            
            # Determine balance
            if abs(call_pressure_pct - put_pressure_pct) < 10:
                balance = "balanced"
            elif call_pressure_pct > put_pressure_pct:
                balance = "call_dominant"
            else:
                balance = "put_dominant"
            
            return {
                "call_pressure": call_pressure_pct,
                "put_pressure": put_pressure_pct,
                "balance": balance
            }
            
        except Exception as e:
            logger.error(f"Error calculating pressure distribution: {e}")
            return {"call_pressure": 50, "put_pressure": 50, "balance": "neutral"}
    
    def _create_empty_map(self, symbol: str, spot: float) -> GammaPressureMap:
        """Create empty pressure map for error cases"""
        return GammaPressureMap(
            symbol=symbol,
            spot=spot,
            total_call_gex=0,
            total_put_gex=0,
            net_gamma=0,
            top_magnets=[],
            top_cliffs=[],
            strongest_magnet=None,
            strongest_cliff=None,
            gamma_flip_zone=(spot - 50, spot + 50),
            pressure_distribution={"call_pressure": 50, "put_pressure": 50, "balance": "neutral"}
        )
    
    def format_for_frontend(self, pressure_map: GammaPressureMap) -> Dict[str, Any]:
        """
        Format pressure map for frontend consumption
        """
        try:
            # Format top magnets
            magnets = []
            for magnet in pressure_map.top_magnets:
                magnets.append({
                    "strike": magnet.strike,
                    "strength": magnet.pressure_strength,
                    "distance_from_spot": magnet.distance_from_spot,
                    "net_gex": magnet.net_gex
                })
            
            # Format top cliffs
            cliffs = []
            for cliff in pressure_map.top_cliffs:
                cliffs.append({
                    "strike": cliff.strike,
                    "strength": cliff.pressure_strength,
                    "distance_from_spot": cliff.distance_from_spot,
                    "net_gex": cliff.net_gex
                })
            
            # Format strongest points
            strongest_magnet = None
            if pressure_map.strongest_magnet:
                strongest_magnet = {
                    "strike": pressure_map.strongest_magnet.strike,
                    "strength": pressure_map.strongest_magnet.pressure_strength,
                    "message": f"🧲 Strongest Gamma Magnet: {pressure_map.strongest_magnet.strike:.0f}"
                }
            
            strongest_cliff = None
            if pressure_map.strongest_cliff:
                strongest_cliff = {
                    "strike": pressure_map.strongest_cliff.strike,
                    "strength": pressure_map.strongest_cliff.pressure_strength,
                    "message": f"🧨 Gamma Cliff Below: {pressure_map.strongest_cliff.strike:.0f}"
                }
            
            return {
                "symbol": pressure_map.symbol,
                "spot": pressure_map.spot,
                "net_gamma": pressure_map.net_gamma,
                "total_call_gex": pressure_map.total_call_gex,
                "total_put_gex": pressure_map.total_put_gex,
                "top_magnets": magnets,
                "top_cliffs": cliffs,
                "strongest_magnet": strongest_magnet,
                "strongest_cliff": strongest_cliff,
                "gamma_flip_zone": {
                    "lower_bound": pressure_map.gamma_flip_zone[0],
                    "upper_bound": pressure_map.gamma_flip_zone[1],
                    "width": pressure_map.gamma_flip_zone[1] - pressure_map.gamma_flip_zone[0]
                },
                "pressure_distribution": pressure_map.pressure_distribution,
                "summary": {
                    "magnet_count": len(magnets),
                    "cliff_count": len(cliffs),
                    "dominant_pressure": pressure_map.pressure_distribution["balance"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting pressure map for frontend: {e}")
            return {}
