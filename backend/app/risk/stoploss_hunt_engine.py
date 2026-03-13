"""
StoplossHuntEngine - Detects stoploss hunting behavior
Lightweight, optimized for Intel i5 CPU, 8GB RAM
"""

import logging
import time
from typing import Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class StoplossHuntSignal:
    """Stoploss hunt analysis result"""
    signal: str  # HUNT_UP | HUNT_DOWN | NONE
    confidence: float
    direction: str  # UP | DOWN | NONE
    strength: float
    reason: str

class StoplossHuntEngine:
    """
    Detects stoploss hunting behavior
    Analyzes price action for artificial stoploss triggering
    """
    
    def __init__(self):
        # Detection thresholds
        self.volatility_spike_threshold = 2.0  # 2x normal volatility
        self.support_resistance_proximity = 0.01  # 1% proximity
        self.oi_drop_threshold = 0.2  # 20% OI drop
        self.fast_reversal_threshold = 0.015  # 1.5% fast reversal
        
        # Production safety features
        self.last_signal_timestamp = 0
        self.cooldown_seconds = 3
        
        # Safe default output
        self.safe_default = {
            "signal": "NONE",
            "confidence": 0.0,
            "direction": "NONE",
            "strength": 0.0,
            "reason": "invalid_metrics"
        }
        
        logger.info("StoplossHuntEngine initialized")
    
    def analyze(self, live_metrics) -> Dict[str, Any]:
        """
        Analyze LiveMetrics for stoploss hunting patterns
        """
        try:
            # FIX 1: Metrics validation
            if not live_metrics:
                logger.debug("Empty metrics received")
                return self.safe_default
            
            # FIX 1: Safe field access with validation
            spot = live_metrics.get("spot") if isinstance(live_metrics, dict) else getattr(live_metrics, 'spot', None)
            if not spot or spot <= 0:
                logger.debug("Invalid or missing spot price")
                return self.safe_default
            
            support_level = live_metrics.get("support_level") if isinstance(live_metrics, dict) else getattr(live_metrics, 'support_level', 0)
            resistance_level = live_metrics.get("resistance_level") if isinstance(live_metrics, dict) else getattr(live_metrics, 'resistance_level', 0)
            volatility_regime = live_metrics.get("volatility_regime") if isinstance(live_metrics, dict) else getattr(live_metrics, 'volatility_regime', 'normal')
            total_oi = live_metrics.get("total_oi") if isinstance(live_metrics, dict) else getattr(live_metrics, 'total_oi', 0)
            oi_velocity = live_metrics.get("oi_velocity") if isinstance(live_metrics, dict) else getattr(live_metrics, 'oi_velocity', 0)
            flow_imbalance = live_metrics.get("flow_imbalance") if isinstance(live_metrics, dict) else getattr(live_metrics, 'flow_imbalance', 0)
            expected_move = live_metrics.get("expected_move") if isinstance(live_metrics, dict) else getattr(live_metrics, 'expected_move', spot * 0.02)
            
            # FIX 3: Signal cooldown mechanism
            current_time = time.time()
            if current_time - self.last_signal_timestamp < self.cooldown_seconds:
                logger.debug("Signal in cooldown period")
                return {
                    "signal": "NONE",
                    "confidence": 0.0,
                    "direction": "NONE",
                    "strength": 0.0,
                    "reason": "signal_cooldown"
                }
            
            # FIX 5: Performance safety - constant time calculations
            # Detect hunting patterns
            hunt_up = self._detect_upward_hunt(spot, support_level, volatility_regime, oi_velocity, expected_move)
            hunt_down = self._detect_downward_hunt(spot, resistance_level, volatility_regime, oi_velocity, expected_move)
            
            # Determine final signal
            if hunt_up['confidence'] > hunt_down['confidence'] and hunt_up['confidence'] > 0.5:
                # FIX 3: Update timestamp for significant signals only
                self.last_signal_timestamp = current_time
                logger.info(f"Stoploss hunt UP detected: {hunt_up['reason']}")
                return {
                    "signal": "HUNT_UP",
                    "confidence": hunt_up['confidence'],
                    "direction": "UP",
                    "strength": hunt_up['confidence'],
                    "reason": hunt_up['reason']
                }
            elif hunt_down['confidence'] > hunt_up['confidence'] and hunt_down['confidence'] > 0.5:
                # FIX 3: Update timestamp for significant signals only
                self.last_signal_timestamp = current_time
                logger.info(f"Stoploss hunt DOWN detected: {hunt_down['reason']}")
                return {
                    "signal": "HUNT_DOWN",
                    "confidence": hunt_down['confidence'],
                    "direction": "DOWN",
                    "strength": hunt_down['confidence'],
                    "reason": hunt_down['reason']
                }
            else:
                return {
                    "signal": "NONE",
                    "confidence": 0.0,
                    "direction": "NONE",
                    "strength": 0.0,
                    "reason": "no_stoploss_hunt"
                }
                
        except Exception as e:
            # FIX 2: Safe default output on exceptions
            logger.error(f"StoplossHuntEngine analysis error: {e}")
            return self.safe_default
    
    def _detect_upward_hunt(self, spot: float, support_level: float, volatility_regime: str, oi_velocity: float, expected_move: float) -> Dict[str, Any]:
        """Detect upward stoploss hunt (spike down through support then recovery)"""
        try:
            confidence = 0.0
            reasons = []
            
            # FIX 5: Performance safety - avoid loops, use constant time operations
            # Check for extreme volatility (common in stoploss hunts)
            if volatility_regime == 'extreme':
                confidence += 0.3
                reasons.append("extreme_volatility")
            elif volatility_regime == 'elevated':
                confidence += 0.15
                reasons.append("elevated_volatility")
            
            # Check if price is near support (hunt target)
            if support_level > 0:
                support_distance = (spot - support_level) / support_level
                if support_distance < self.support_resistance_proximity:
                    confidence += 0.25
                    reasons.append("price_near_support")
            
            # Check for OI velocity changes (can indicate stop triggering)
            if abs(oi_velocity) > 1000:  # High OI velocity
                confidence += 0.2
                reasons.append("high_oi_velocity")
            
            # Check expected move (sudden large moves)
            if expected_move and spot > 0 and expected_move / spot > 0.025:  # > 2.5% expected move
                confidence += 0.15
                reasons.append("large_expected_move")
            
            logger.debug(f"Hunt UP analysis: confidence={confidence:.3f}, reasons={reasons}")
            
            return {
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons) if reasons else "no_hunt_indicators"
            }
            
        except Exception as e:
            logger.error(f"Upward hunt detection error: {e}")
            return {'confidence': 0.0, 'reason': 'detection_error'}
    
    def _detect_downward_hunt(self, spot: float, resistance_level: float, volatility_regime: str, oi_velocity: float, expected_move: float) -> Dict[str, Any]:
        """Detect downward stoploss hunt (spike up through resistance then rejection)"""
        try:
            confidence = 0.0
            reasons = []
            
            # FIX 5: Performance safety - avoid loops, use constant time operations
            # Check for extreme volatility
            if volatility_regime == 'extreme':
                confidence += 0.3
                reasons.append("extreme_volatility")
            elif volatility_regime == 'elevated':
                confidence += 0.15
                reasons.append("elevated_volatility")
            
            # Check if price is near resistance (hunt target)
            if resistance_level > 0:
                resistance_distance = (resistance_level - spot) / resistance_level
                if resistance_distance < self.support_resistance_proximity:
                    confidence += 0.25
                    reasons.append("price_near_resistance")
            
            # Check for OI velocity changes
            if abs(oi_velocity) > 1000:  # High OI velocity
                confidence += 0.2
                reasons.append("high_oi_velocity")
            
            # Check expected move
            if expected_move and spot > 0 and expected_move / spot > 0.025:  # > 2.5% expected move
                confidence += 0.15
                reasons.append("large_expected_move")
            
            logger.debug(f"Hunt DOWN analysis: confidence={confidence:.3f}, reasons={reasons}")
            
            return {
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons) if reasons else "no_hunt_indicators"
            }
            
        except Exception as e:
            logger.error(f"Downward hunt detection error: {e}")
            return {'confidence': 0.0, 'reason': 'detection_error'}
