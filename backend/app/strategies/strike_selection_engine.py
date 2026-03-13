"""
Strike Selection Engine - Selects optimal option strikes
Lightweight, optimized for Intel i5 CPU, 8GB RAM
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import math

logger = logging.getLogger(__name__)

@dataclass
class StrikeSelection:
    """Optimal strike selection result"""
    best_strike: float
    option_type: str  # CE / PE
    confidence: float
    reasoning: str
    liquidity_score: float
    gamma_score: float
    oi_concentration: float

class StrikeSelectionEngine:
    """
    Selects optimal option strikes based on market conditions
    Considers ATM/ITM/OTM selection, liquidity, OI concentration, gamma proximity
    """
    
    def __init__(self):
        # Strike selection parameters
        self.strike_rounding = 50  # Round strikes to nearest 50
        self.min_oi_threshold = 10000  # Minimum OI for liquidity
        self.liquidity_weight = 0.4
        self.gamma_weight = 0.3
        self.oi_weight = 0.3
        
        # Strike type preferences based on market conditions
        self.strike_preferences = {
            'bullish_trend': {'primary': 'OTM', 'secondary': 'ATM'},
            'bearish_trend': {'primary': 'OTM', 'secondary': 'ATM'},
            'range_bound': {'primary': 'ATM', 'secondary': 'OTM'},
            'breakout': {'primary': 'OTM', 'secondary': 'ATM'},
            'mean_reversion': {'primary': 'ATM', 'secondary': 'ITM'},
            'high_volatility': {'primary': 'ATM', 'secondary': 'OTM'},
            'low_volatility': {'primary': 'OTM', 'secondary': 'ATM'}
        }
    
    def select_strike(self, metrics, market_bias: str, regime: str) -> StrikeSelection:
        """
        Select optimal strike based on market conditions
        """
        try:
            spot = metrics.spot
            
            # Determine option type based on market bias
            option_type = self._determine_option_type(market_bias, regime)
            
            # Calculate strike candidates
            strike_candidates = self._generate_strike_candidates(spot, option_type, regime)
            
            # Evaluate each candidate
            evaluated_strikes = []
            for strike in strike_candidates:
                evaluation = self._evaluate_strike(strike, option_type, metrics)
                evaluated_strikes.append((strike, evaluation))
            
            # Select best strike
            if evaluated_strikes:
                best_strike, best_evaluation = max(evaluated_strikes, key=lambda x: x[1]['overall_score'])
                
                return StrikeSelection(
                    best_strike=best_strike,
                    option_type=option_type,
                    confidence=best_evaluation['overall_score'],
                    reasoning=best_evaluation['reasoning'],
                    liquidity_score=best_evaluation['liquidity_score'],
                    gamma_score=best_evaluation['gamma_score'],
                    oi_concentration=best_evaluation['oi_score']
                )
            else:
                # Fallback to ATM
                atm_strike = self._round_to_strike(spot)
                return StrikeSelection(
                    best_strike=atm_strike,
                    option_type=option_type,
                    confidence=0.5,
                    reasoning="Fallback to ATM strike due to insufficient data",
                    liquidity_score=0.5,
                    gamma_score=0.5,
                    oi_concentration=0.5
                )
                
        except Exception as e:
            logger.error(f"Strike selection error: {e}")
            # Safe fallback
            return StrikeSelection(
                best_strike=self._round_to_strike(metrics.spot),
                option_type="CE",
                confidence=0.3,
                reason="Error in strike selection, using ATM fallback",
                liquidity_score=0.3,
                gamma_score=0.3,
                oi_concentration=0.3
            )
    
    def _determine_option_type(self, market_bias: str, regime: str) -> str:
        """Determine option type based on market bias and regime"""
        if market_bias == "bullish":
            return "CE"
        elif market_bias == "bearish":
            return "PE"
        else:
            # For neutral/biased regimes, choose based on regime characteristics
            if regime in ["HIGH_VOLATILITY", "BREAKOUT"]:
                # For high volatility/breakout, prefer straddles/strangles
                # Return CE for simplicity, but in practice would consider both
                return "CE"
            elif regime == "MEAN_REVERSION":
                # For mean reversion, might consider both directions
                # Return CE for simplicity
                return "CE"
            else:
                # Default to CE for range/low volatility
                return "CE"
    
    def _generate_strike_candidates(self, spot: float, option_type: str, regime: str) -> List[float]:
        """Generate list of potential strike candidates"""
        try:
            candidates = []
            
            # Get preference for this regime
            regime_key = self._get_regime_key(regime)
            preferences = self.strike_preferences.get(regime_key, {'primary': 'ATM', 'secondary': 'OTM'})
            
            # Generate strikes based on preferences
            if preferences['primary'] == 'ATM':
                candidates.extend(self._get_atm_strikes(spot))
            elif preferences['primary'] == 'OTM':
                candidates.extend(self._get_otm_strikes(spot, option_type))
            elif preferences['primary'] == 'ITM':
                candidates.extend(self._get_itm_strikes(spot, option_type))
            
            # Add secondary preference candidates
            if preferences['secondary'] == 'ATM':
                candidates.extend(self._get_atm_strikes(spot))
            elif preferences['secondary'] == 'OTM':
                candidates.extend(self._get_otm_strikes(spot, option_type))
            elif preferences['secondary'] == 'ITM':
                candidates.extend(self._get_itm_strikes(spot, option_type))
            
            # Remove duplicates and sort
            candidates = list(set(candidates))
            candidates.sort()
            
            return candidates[:10]  # Limit to top 10 candidates
            
        except Exception as e:
            logger.error(f"Strike candidate generation error: {e}")
            return [self._round_to_strike(spot)]
    
    def _get_regime_key(self, regime: str) -> str:
        """Map regime to preference key"""
        regime_mapping = {
            'TREND': 'bullish_trend',  # Will be adjusted based on bias
            'RANGE': 'range_bound',
            'BREAKOUT': 'breakout',
            'MEAN_REVERSION': 'mean_reversion',
            'HIGH_VOLATILITY': 'high_volatility',
            'LOW_VOLATILITY': 'low_volatility'
        }
        return regime_mapping.get(regime, 'range_bound')
    
    def _get_atm_strikes(self, spot: float) -> List[float]:
        """Get at-the-money strikes"""
        atm_strike = self._round_to_strike(spot)
        return [atm_strike]
    
    def _get_otm_strikes(self, spot: float, option_type: str) -> List[float]:
        """Get out-of-the-money strikes"""
        strikes = []
        
        if option_type == "CE":
            # OTM calls are above spot
            for offset in [0.01, 0.02, 0.03, 0.04]:  # 1%, 2%, 3%, 4% OTM
                strike = spot * (1 + offset)
                strikes.append(self._round_to_strike(strike))
        else:
            # OTM puts are below spot
            for offset in [0.01, 0.02, 0.03, 0.04]:
                strike = spot * (1 - offset)
                strikes.append(self._round_to_strike(strike))
        
        return strikes
    
    def _get_itm_strikes(self, spot: float, option_type: str) -> List[float]:
        """Get in-the-money strikes"""
        strikes = []
        
        if option_type == "CE":
            # ITM calls are below spot
            for offset in [0.01, 0.02]:  # 1%, 2% ITM
                strike = spot * (1 - offset)
                strikes.append(self._round_to_strike(strike))
        else:
            # ITM puts are above spot
            for offset in [0.01, 0.02]:
                strike = spot * (1 + offset)
                strikes.append(self._round_to_strike(strike))
        
        return strikes
    
    def _round_to_strike(self, price: float) -> float:
        """Round price to nearest valid strike"""
        return round(price / self.strike_rounding) * self.strike_rounding
    
    def _evaluate_strike(self, strike: float, option_type: str, metrics) -> Dict[str, Any]:
        """Evaluate a strike based on multiple factors"""
        try:
            # Liquidity score (based on distance from spot and expected OI)
            liquidity_score = self._calculate_liquidity_score(strike, option_type, metrics)
            
            # Gamma score (based on gamma proximity)
            gamma_score = self._calculate_gamma_score(strike, metrics)
            
            # OI concentration score
            oi_score = self._calculate_oi_score(strike, option_type, metrics)
            
            # Overall weighted score
            overall_score = (
                liquidity_score * self.liquidity_weight +
                gamma_score * self.gamma_weight +
                oi_score * self.oi_weight
            )
            
            # Generate reasoning
            reasoning = self._generate_strike_reasoning(
                strike, option_type, liquidity_score, gamma_score, oi_score, metrics
            )
            
            return {
                'overall_score': overall_score,
                'liquidity_score': liquidity_score,
                'gamma_score': gamma_score,
                'oi_score': oi_score,
                'reasoning': reasoning
            }
            
        except Exception as e:
            logger.error(f"Strike evaluation error: {e}")
            return {
                'overall_score': 0.3,
                'liquidity_score': 0.3,
                'gamma_score': 0.3,
                'oi_score': 0.3,
                'reasoning': "Error in strike evaluation"
            }
    
    def _calculate_liquidity_score(self, strike: float, option_type: str, metrics) -> float:
        """Calculate liquidity score for a strike"""
        try:
            spot = metrics.spot
            
            # Distance from spot affects liquidity
            distance_pct = abs(strike - spot) / spot
            
            # ATM strikes have highest liquidity
            if distance_pct < 0.005:  # Within 0.5%
                base_liquidity = 1.0
            elif distance_pct < 0.02:  # Within 2%
                base_liquidity = 0.8
            elif distance_pct < 0.04:  # Within 4%
                base_liquidity = 0.6
            else:
                base_liquidity = 0.4
            
            # Adjust for total OI (proxy for overall liquidity)
            total_oi = getattr(metrics, 'total_oi', 0)
            if total_oi > 1000000:
                oi_multiplier = 1.0
            elif total_oi > 500000:
                oi_multiplier = 0.8
            else:
                oi_multiplier = 0.6
            
            return base_liquidity * oi_multiplier
            
        except Exception as e:
            logger.error(f"Liquidity score calculation error: {e}")
            return 0.5
    
    def _calculate_gamma_score(self, strike: float, metrics) -> float:
        """Calculate gamma score based on gamma flip proximity"""
        try:
            gamma_flip_level = getattr(metrics, 'gamma_flip_level', None)
            distance_from_flip = getattr(metrics, 'distance_from_flip', None)
            
            if gamma_flip_level is None or distance_from_flip is None:
                return 0.5  # Default if no gamma data
            
            # Calculate distance from strike to gamma flip level
            strike_distance = abs(strike - gamma_flip_level)
            spot = getattr(metrics, 'spot', 1)
            
            if spot > 0:
                strike_distance_pct = strike_distance / spot
                
                # Strikes near gamma flip level have higher gamma relevance
                if strike_distance_pct < 0.01:  # Within 1%
                    return 1.0
                elif strike_distance_pct < 0.02:  # Within 2%
                    return 0.8
                elif strike_distance_pct < 0.04:  # Within 4%
                    return 0.6
                else:
                    return 0.4
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Gamma score calculation error: {e}")
            return 0.5
    
    def _calculate_oi_score(self, strike: float, option_type: str, metrics) -> float:
        """Calculate OI concentration score"""
        try:
            # Since we don't have strike-by-strike OI data in LiveMetrics,
            # use proxy calculations based on overall OI characteristics
            
            total_oi = getattr(metrics, 'total_oi', 0)
            pcr = getattr(metrics, 'pcr', 1.0)
            
            # Estimate OI distribution based on PCR and option type
            if option_type == "CE":
                # Call OI estimate
                call_oi_ratio = 1.0 / (1.0 + pcr)
                estimated_oi = total_oi * call_oi_ratio
            else:
                # Put OI estimate
                put_oi_ratio = pcr / (1.0 + pcr)
                estimated_oi = total_oi * put_oi_ratio
            
            # Normalize OI score
            if estimated_oi > 500000:
                return 1.0
            elif estimated_oi > 200000:
                return 0.8
            elif estimated_oi > 100000:
                return 0.6
            elif estimated_oi > 50000:
                return 0.4
            else:
                return 0.2
                
        except Exception as e:
            logger.error(f"OI score calculation error: {e}")
            return 0.5
    
    def _generate_strike_reasoning(self, strike: float, option_type: str, 
                                 liquidity_score: float, gamma_score: float, 
                                 oi_score: float, metrics) -> str:
        """Generate reasoning for strike selection"""
        try:
            spot = metrics.spot
            distance_pct = abs(strike - spot) / spot
            
            reasoning_parts = []
            
            # Strike type description
            if distance_pct < 0.005:
                reasoning_parts.append("ATM strike")
            elif distance_pct < 0.02:
                reasoning_parts.append("Near-OTM strike")
            else:
                reasoning_parts.append("OTM strike")
            
            # Liquidity description
            if liquidity_score > 0.8:
                reasoning_parts.append("High liquidity")
            elif liquidity_score > 0.6:
                reasoning_parts.append("Good liquidity")
            else:
                reasoning_parts.append("Moderate liquidity")
            
            # Gamma description
            if gamma_score > 0.8:
                reasoning_parts.append("Near gamma flip level")
            elif gamma_score > 0.6:
                reasoning_parts.append("Moderate gamma exposure")
            else:
                reasoning_parts.append("Low gamma relevance")
            
            # OI description
            if oi_score > 0.8:
                reasoning_parts.append("High OI concentration")
            elif oi_score > 0.6:
                reasoning_parts.append("Moderate OI")
            else:
                reasoning_parts.append("Low OI")
            
            return "; ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Strike reasoning generation error: {e}")
            return f"Strike {strike} selected with overall score"
