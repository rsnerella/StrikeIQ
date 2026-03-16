"""
Options Integrator - Options Microstructure Analysis for Chart Intelligence
Integrates options data (call walls, put walls, PCR, GEX) with price action patterns.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class OptionsMicrostructure:
    """Options microstructure analysis"""
    call_wall: float
    put_wall: float
    pcr_ratio: float
    gex_flip_level: float
    net_gamma: float
    call_oi: float
    put_oi: float
    total_oi: float
    max_pain: float
    implied_volatility: float

@dataclass
class OptionsLevel:
    """Significant options level"""
    price: float
    level_type: str  # "CALL_WALL", "PUT_WALL", "GEX_FLIP", "MAX_PAIN"
    strength: float
    distance_from_spot: float
    oi_concentration: float

class OptionsIntegrator:
    """
    Integrates options microstructure data with chart intelligence.
    Provides context for price action patterns based on options positioning.
    """
    
    def __init__(self):
        self.oi_threshold = 0.15  # 15% of total OI to consider significant
        self.gex_flip_tolerance = 0.02  # 2% tolerance for GEX flip level
        
    def analyze_options_microstructure(self, options_data: Dict[str, Any], 
                                     spot_price: float) -> OptionsMicrostructure:
        """
        Analyze options microstructure from raw options data.
        
        Args:
            options_data: Raw options data from option chain
            spot_price: Current spot price
            
        Returns:
            OptionsMicrostructure object
        """
        # Extract key metrics
        call_wall = options_data.get('call_wall', spot_price * 1.02)
        put_wall = options_data.get('put_wall', spot_price * 0.98)
        pcr_ratio = options_data.get('pcr_ratio', 1.0)
        gex_flip_level = options_data.get('gex_flip_level', spot_price)
        net_gamma = options_data.get('net_gamma', 0)
        
        # Calculate OI metrics
        call_oi = options_data.get('total_call_oi', 0)
        put_oi = options_data.get('total_put_oi', 0)
        total_oi = call_oi + put_oi
        
        # Calculate max pain (simplified)
        max_pain = options_data.get('max_pain', spot_price)
        
        # Get implied volatility
        implied_volatility = options_data.get('iv_atm', 0.20)
        
        return OptionsMicrostructure(
            call_wall=call_wall,
            put_wall=put_wall,
            pcr_ratio=pcr_ratio,
            gex_flip_level=gex_flip_level,
            net_gamma=net_gamma,
            call_oi=call_oi,
            put_oi=put_oi,
            total_oi=total_oi,
            max_pain=max_pain,
            implied_volatility=implied_volatility
        )
    
    def get_significant_levels(self, microstructure: OptionsMicrostructure, 
                              spot_price: float) -> List[OptionsLevel]:
        """
        Identify significant options levels for chart overlay.
        
        Args:
            microstructure: OptionsMicrostructure object
            spot_price: Current spot price
            
        Returns:
            List of OptionsLevel objects
        """
        levels = []
        
        # Call Wall
        if microstructure.call_wall > 0:
            call_wall_strength = self._calculate_level_strength(
                microstructure.call_wall, spot_price, microstructure, "CALL_WALL"
            )
            levels.append(OptionsLevel(
                price=microstructure.call_wall,
                level_type="CALL_WALL",
                strength=call_wall_strength,
                distance_from_spot=abs(microstructure.call_wall - spot_price) / spot_price,
                oi_concentration=self._estimate_oi_concentration(microstructure, "CALL_WALL")
            ))
        
        # Put Wall
        if microstructure.put_wall > 0:
            put_wall_strength = self._calculate_level_strength(
                microstructure.put_wall, spot_price, microstructure, "PUT_WALL"
            )
            levels.append(OptionsLevel(
                price=microstructure.put_wall,
                level_type="PUT_WALL",
                strength=put_wall_strength,
                distance_from_spot=abs(microstructure.put_wall - spot_price) / spot_price,
                oi_concentration=self._estimate_oi_concentration(microstructure, "PUT_WALL")
            ))
        
        # GEX Flip Level
        if abs(microstructure.gex_flip_level - spot_price) / spot_price < 0.05:  # Within 5%
            gex_strength = self._calculate_level_strength(
                microstructure.gex_flip_level, spot_price, microstructure, "GEX_FLIP"
            )
            levels.append(OptionsLevel(
                price=microstructure.gex_flip_level,
                level_type="GEX_FLIP",
                strength=gex_strength,
                distance_from_spot=abs(microstructure.gex_flip_level - spot_price) / spot_price,
                oi_concentration=self._estimate_oi_concentration(microstructure, "GEX_FLIP")
            ))
        
        # Max Pain
        if abs(microstructure.max_pain - spot_price) / spot_price < 0.03:  # Within 3%
            max_pain_strength = self._calculate_level_strength(
                microstructure.max_pain, spot_price, microstructure, "MAX_PAIN"
            )
            levels.append(OptionsLevel(
                price=microstructure.max_pain,
                level_type="MAX_PAIN",
                strength=max_pain_strength,
                distance_from_spot=abs(microstructure.max_pain - spot_price) / spot_price,
                oi_concentration=self._estimate_oi_concentration(microstructure, "MAX_PAIN")
            ))
        
        # Sort by strength
        levels.sort(key=lambda x: x.strength, reverse=True)
        
        return levels
    
    def assess_gamma_regime(self, microstructure: OptionsMicrostructure, 
                           spot_price: float) -> Dict[str, Any]:
        """
        Assess the gamma regime and its implications for price action.
        
        Args:
            microstructure: OptionsMicrostructure object
            spot_price: Current spot price
            
        Returns:
            Gamma regime analysis
        """
        # Determine gamma regime
        if microstructure.net_gamma > 0:
            if abs(microstructure.gex_flip_level - spot_price) / spot_price < self.gex_flip_tolerance:
                regime = "CALL_GAMMA_DOMINANT"
                implication = "Positive gamma may suppress volatility, magnet to flip level"
                bias = "BULLISH"
            else:
                regime = "MODERATE_CALL_GAMMA"
                implication = "Generally supportive of upside, reduced volatility"
                bias = "SLIGHTLY_BULLISH"
        elif microstructure.net_gamma < 0:
            if abs(microstructure.gex_flip_level - spot_price) / spot_price < self.gex_flip_tolerance:
                regime = "PUT_GAMMA_DOMINANT"
                implication = "Negative gamma may amplify volatility, magnet to flip level"
                bias = "BEARISH"
            else:
                regime = "MODERATE_PUT_GAMMA"
                implication = "Generally supportive of downside, increased volatility"
                bias = "SLIGHTLY_BEARISH"
        else:
            regime = "GAMMA_NEUTRAL"
            implication = "Balanced gamma positioning, normal volatility expected"
            bias = "NEUTRAL"
        
        # Calculate pressure metrics
        distance_to_flip = abs(microstructure.gex_flip_level - spot_price) / spot_price
        flip_pressure = max(0, 1.0 - distance_to_flip / 0.05)  # Pressure increases as we get closer
        
        # PCR analysis
        if microstructure.pcr_ratio > 1.3:
            pcr_signal = "PUT_HEAVY"
            pcr_implication = "High put buying may indicate downside protection or bearish sentiment"
        elif microstructure.pcr_ratio < 0.7:
            pcr_signal = "CALL_HEAVY"
            pcr_implication = "High call buying may indicate upside speculation or bullish sentiment"
        else:
            pcr_signal = "BALANCED"
            pcr_implication = "Balanced put/call positioning"
        
        return {
            "regime": regime,
            "bias": bias,
            "implication": implication,
            "flip_pressure": flip_pressure,
            "distance_to_flip": distance_to_flip,
            "pcr_signal": pcr_signal,
            "pcr_implication": pcr_implication,
            "net_gamma": microstructure.net_gamma,
            "iv_level": "HIGH" if microstructure.implied_volatility > 0.25 else "NORMAL" if microstructure.implied_volatility > 0.15 else "LOW"
        }
    
    def validate_pattern_with_options(self, pattern_price: float, pattern_type: str,
                                     microstructure: OptionsMicrostructure, 
                                     spot_price: float) -> Dict[str, Any]:
        """
        Validate a price action pattern against options microstructure.
        
        Args:
            pattern_price: Price level of the pattern
            pattern_type: Type of pattern (RESISTANCE, SUPPORT, BREAKOUT, etc.)
            pattern_type: str
            microstructure: OptionsMicrostructure object
            spot_price: Current spot price
            
        Returns:
            Pattern validation analysis
        """
        validation = {
            "confluence": False,
            "confluence_level": None,
            "strength_multiplier": 1.0,
            "options_context": "",
            "risk_factors": []
        }
        
        # Check for confluence with options levels
        significant_levels = self.get_significant_levels(microstructure, spot_price)
        
        for level in significant_levels:
            if abs(pattern_price - level.price) / pattern_price < 0.01:  # Within 1%
                validation["confluence"] = True
                validation["confluence_level"] = level.level_type
                validation["strength_multiplier"] = 1.0 + (level.strength * 0.5)
                
                # Add context based on level type
                if level.level_type == "CALL_WALL":
                    validation["options_context"] = "Confluence with call wall - strong resistance"
                    validation["risk_factors"].append("Call wall may reject breakout attempts")
                elif level.level_type == "PUT_WALL":
                    validation["options_context"] = "Confluence with put wall - strong support"
                    validation["risk_factors"].append("Put wall may provide strong support")
                elif level.level_type == "GEX_FLIP":
                    validation["options_context"] = "Confluence with GEX flip - gamma magnet"
                    validation["risk_factors"].append("Price may be attracted to flip level")
                elif level.level_type == "MAX_PAIN":
                    validation["options_context"] = "Confluence with max pain - pinning risk"
                    validation["risk_factors"].append("Price may pin to max pain at expiry")
        
        # Assess gamma regime impact
        gamma_regime = self.assess_gamma_regime(microstructure, spot_price)
        validation["gamma_regime"] = gamma_regime
        
        # Adjust expectations based on IV
        if microstructure.implied_volatility > 0.25:
            validation["volatility_adjustment"] = "HIGH_IV_PATTERNS_MAY_FAIL_MORE_OFTEN"
        elif microstructure.implied_volatility < 0.15:
            validation["volatility_adjustment"] = "LOW_IV_PATTERNS_MORE_RELIABLE"
        else:
            validation["volatility_adjustment"] = "NORMAL_IV_EXPECTATIONS"
        
        return validation
    
    def _calculate_level_strength(self, level_price: float, spot_price: float,
                                microstructure: OptionsMicrostructure, level_type: str) -> float:
        """Calculate strength of an options level"""
        base_strength = 0.5
        
        # Distance from spot (closer = stronger)
        distance = abs(level_price - spot_price) / spot_price
        distance_strength = max(0, 1.0 - distance / 0.05)  # Normalize to 5% max distance
        
        # OI concentration (higher = stronger)
        oi_strength = self._estimate_oi_concentration(microstructure, level_type)
        
        # PCR alignment
        if level_type == "CALL_WALL" and microstructure.pcr_ratio < 0.8:
            pcr_strength = 0.2  # Call-heavy market supports call wall
        elif level_type == "PUT_WALL" and microstructure.pcr_ratio > 1.2:
            pcr_strength = 0.2  # Put-heavy market supports put wall
        else:
            pcr_strength = 0.0
        
        # Gamma alignment
        if level_type == "GEX_FLIP":
            gamma_strength = min(0.3, abs(microstructure.net_gamma) / 1000000)
        else:
            gamma_strength = 0.0
        
        total_strength = base_strength + (distance_strength * 0.3) + (oi_strength * 0.3) + pcr_strength + gamma_strength
        
        return min(1.0, total_strength)
    
    def _estimate_oi_concentration(self, microstructure: OptionsMicrostructure, 
                                 level_type: str) -> float:
        """Estimate OI concentration at a level"""
        if microstructure.total_oi == 0:
            return 0.0
        
        if level_type == "CALL_WALL":
            # Estimate call wall OI concentration
            estimated_call_wall_oi = microstructure.call_oi * 0.3  # Assume 30% at call wall
            return estimated_call_wall_oi / microstructure.total_oi
        
        elif level_type == "PUT_WALL":
            # Estimate put wall OI concentration
            estimated_put_wall_oi = microstructure.put_oi * 0.3  # Assume 30% at put wall
            return estimated_put_wall_oi / microstructure.total_oi
        
        elif level_type == "GEX_FLIP":
            # GEX flip typically has balanced OI
            return 0.2
        
        elif level_type == "MAX_PAIN":
            # Max pain often has high OI concentration
            return 0.25
        
        return 0.1
