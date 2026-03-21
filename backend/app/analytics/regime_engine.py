"""
Regime Engine - Unified Market Regime Analysis
Consolidates regime_engine.py and regime_confidence_engine.py
Provides comprehensive regime detection with dynamics and confidence scoring
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class RegimeType(Enum):
    RANGE = "range"
    TREND = "trend"
    BREAKOUT = "breakout"
    PIN_RISK = "pin_risk"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    UNKNOWN = "unknown"

@dataclass
class RegimeDetection:
    """Basic regime detection result"""
    regime: str
    confidence: float
    reasoning: str
    indicators: Dict[str, float]

@dataclass
class RegimeHistory:
    """Historical regime data point"""
    regime: RegimeType
    timestamp: datetime
    confidence: float
    metrics: Dict[str, Any]

@dataclass
class RegimeDynamics:
    """Enhanced regime analysis with dynamics"""
    regime: RegimeType
    confidence: float
    stability_score: float  # How long regime persisted (0-100)
    acceleration_index: float  # Is regime strengthening? (-100 to +100)
    transition_probability: float  # Probability of regime change
    regime_duration: float  # Duration in minutes
    historical_consistency: float  # How consistent has this regime been
    momentum_score: float  # Current momentum of regime characteristics
    reasoning: str
    indicators: Dict[str, float]

class RegimeEngine:
    """
    Unified Regime Engine
    
    Combines:
    - Basic regime detection (from ai/regime_engine.py)
    - Enhanced dynamics analysis (from services/regime_confidence_engine.py)
    
    Features:
    - Real-time regime detection
    - Historical pattern analysis
    - Stability and acceleration metrics
    - Transition probability calculation
    - Confidence scoring with dynamics
    """
    
    def __init__(self):
        # Basic detection thresholds (from regime_engine.py)
        self.thresholds = {
            'trend_strength': 0.6,
            'range_bound': 0.4,
            'breakout_momentum': 0.7,
            'mean_reversion_strength': 0.65,
            'high_volatility_threshold': 25,
            'low_volatility_threshold': 12
        }
        
        # Regime weights for calculation
        self.regime_weights = {
            'TREND': {
                'gamma_regime': 0.3,
                'flow_direction': 0.25,
                'intent_score': 0.2,
                'pcr_trend': 0.15,
                'breach_probability': 0.1
            },
            'RANGE': {
                'breach_probability': 0.3,
                'expected_move_ratio': 0.25,
                'gamma_regime': 0.2,
                'flow_balance': 0.15,
                'volatility_regime': 0.1
            },
            'BREAKOUT': {
                'breach_probability': 0.3,
                'volume_spike': 0.25,
                'volatility_expansion': 0.2,
                'flow_intensity': 0.15,
                'expected_move_expansion': 0.1
            },
            'MEAN_REVERSION': {
                'gamma_regime': 0.35,
                'extreme_pcr': 0.25,
                'volatility_contraction': 0.2,
                'support_resistance_proximity': 0.15,
                'flow_exhaustion': 0.05
            },
            'HIGH_VOLATILITY': {
                'volatility_regime': 0.4,
                'expected_move_expansion': 0.3,
                'volume_intensity': 0.2,
                'gamma_instability': 0.1
            },
            'LOW_VOLATILITY': {
                'volatility_regime': 0.4,
                'expected_move_contraction': 0.3,
                'volume_suppression': 0.2,
                'gamma_stability': 0.1
            }
        }
        
        # Enhanced analysis parameters (from regime_confidence_engine.py)
        self.regime_history: Dict[str, List[RegimeHistory]] = {}
        self.regime_start_times: Dict[str, datetime] = {}
        self.previous_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Analysis parameters
        self.MIN_HISTORY_POINTS = 5
        self.MAX_HISTORY_POINTS = 100
        self.STABILITY_TIME_WEIGHT = 0.6
        self.CONSISTENCY_WEIGHT = 0.4
        
        logger.info("RegimeEngine initialized - Unified regime analysis")
    
    def detect_regime(self, metrics) -> RegimeDetection:
        """
        Basic regime detection from LiveMetrics
        Original logic from ai/regime_engine.py
        """
        try:
            # Extract key indicators
            indicators = self._extract_indicators(metrics)
            
            # Calculate regime scores
            regime_scores = {}
            
            for regime_name, weights in self.regime_weights.items():
                score = self._calculate_regime_score(regime_name, indicators, weights)
                regime_scores[regime_name] = score
            
            # Find best regime
            best_regime = max(regime_scores.items(), key=lambda x: x[1])
            regime_name = best_regime[0]
            confidence = best_regime[1]
            
            # Generate reasoning
            reasoning = self._generate_regime_reasoning(regime_name, indicators, confidence)
            
            # Apply minimum confidence threshold
            if confidence < 0.35:
                confidence = 0.35
            
            return RegimeDetection(
                regime=regime_name,
                confidence=confidence,
                reasoning=reasoning,
                indicators=indicators
            )
            
        except Exception as e:
            logger.error(f"Regime detection error: {e}")
            return RegimeDetection(
                regime="RANGE",
                confidence=0.5,
                reasoning="Regime detection error, defaulting to range",
                indicators={}
            )
    
    async def analyze_regime_dynamics(self, symbol: str, current_metrics: Dict[str, Any]) -> RegimeDynamics:
        """
        Enhanced regime dynamics analysis
        Original logic from services/regime_confidence_engine.py
        """
        try:
            # Extract current regime
            current_regime_str = current_metrics.get("structural_regime", "unknown")
            current_regime = RegimeType(current_regime_str)
            current_confidence = current_metrics.get("regime_confidence", 50)
            
            # Get previous metrics for acceleration calculation
            previous_metrics = self.previous_metrics.get(symbol, {})
            
            # Update history
            await self._update_regime_history(symbol, current_regime, current_confidence, current_metrics)
            
            # Calculate dynamics
            stability_score = self._calculate_stability_score(symbol)
            acceleration_index = self._calculate_acceleration_index(symbol, current_metrics, previous_metrics)
            transition_probability = self._calculate_transition_probability(symbol)
            regime_duration = self._calculate_regime_duration(symbol)
            historical_consistency = self._calculate_historical_consistency(symbol)
            momentum_score = self._calculate_momentum_score(symbol, current_metrics, previous_metrics)
            
            # Generate enhanced reasoning
            reasoning = self._generate_dynamics_reasoning(current_regime, stability_score, acceleration_index, transition_probability)
            
            # Store current metrics for next iteration
            self.previous_metrics[symbol] = current_metrics.copy()
            
            return RegimeDynamics(
                regime=current_regime,
                confidence=current_confidence,
                stability_score=stability_score,
                acceleration_index=acceleration_index,
                transition_probability=transition_probability,
                regime_duration=regime_duration,
                historical_consistency=historical_consistency,
                momentum_score=momentum_score,
                reasoning=reasoning,
                indicators=current_metrics
            )
            
        except Exception as e:
            logger.error(f"Error analyzing regime dynamics for {symbol}: {e}")
            return self._create_default_dynamics(symbol)
    
    def _extract_indicators(self, metrics) -> Dict[str, float]:
        """Extract and normalize key indicators from LiveMetrics"""
        try:
            indicators = {}
            
            # Gamma regime indicator
            gamma_regime = getattr(metrics, 'gamma_regime', 'neutral')
            indicators['gamma_regime'] = {
                'positive': 0.8,
                'negative': -0.8,
                'neutral': 0.0
            }.get(gamma_regime, 0.0)
            
            # PCR indicator
            pcr = getattr(metrics, 'pcr', 1.0)
            indicators['pcr_value'] = pcr
            indicators['pcr_trend'] = (pcr - 1.0) / 1.0
            
            # Expected move indicator
            expected_move = getattr(metrics, 'expected_move', 0)
            spot = getattr(metrics, 'spot', 1)
            if spot > 0:
                expected_move_ratio = expected_move / spot
                indicators['expected_move_ratio'] = min(expected_move_ratio / 0.03, 1.0)
            else:
                indicators['expected_move_ratio'] = 0.5
            
            # Flow imbalance indicator
            flow_imbalance = getattr(metrics, 'flow_imbalance', 0)
            indicators['flow_imbalance'] = abs(flow_imbalance)
            
            flow_direction = getattr(metrics, 'flow_direction', 'neutral')
            indicators['flow_direction'] = {
                'call': 0.8,
                'put': -0.8,
                'neutral': 0.0
            }.get(flow_direction, 0.0)
            
            # Intent score indicator
            intent_score = getattr(metrics, 'intent_score', 50)
            indicators['intent_score'] = intent_score / 100.0
            
            # Breach probability indicator
            breach_probability = getattr(metrics, 'breach_probability', 37)
            indicators['breach_probability'] = breach_probability / 100.0
            
            # Volatility regime indicator
            volatility_regime = getattr(metrics, 'volatility_regime', 'normal')
            volatility_map = {
                'low': 0.2,
                'normal': 0.5,
                'elevated': 0.75,
                'extreme': 0.95
            }
            indicators['volatility_regime'] = volatility_map.get(volatility_regime, 0.5)
            
            # Distance from flip indicator
            distance_from_flip = getattr(metrics, 'distance_from_flip', 0)
            spot = getattr(metrics, 'spot', 1)
            if spot > 0 and distance_from_flip is not None:
                indicators['gamma_flip_proximity'] = 1.0 - min(abs(distance_from_flip) / spot / 0.02, 1.0)
            else:
                indicators['gamma_flip_proximity'] = 0.5
            
            # Support/Resistance proximity
            support_level = getattr(metrics, 'support_level', 0)
            resistance_level = getattr(metrics, 'resistance_level', 0)
            if support_level > 0 and resistance_level > 0 and spot > 0:
                support_distance = abs(spot - support_level) / spot
                resistance_distance = abs(resistance_level - spot) / spot
                indicators['support_resistance_proximity'] = 1.0 - min((support_distance + resistance_distance) / 2 / 0.03, 1.0)
            else:
                indicators['support_resistance_proximity'] = 0.5
            
            # Volume and flow indicators
            indicators['volume_intensity'] = indicators['intent_score']
            indicators['flow_balance'] = 1.0 - indicators['flow_imbalance']
            indicators['flow_intensity'] = indicators['flow_imbalance']
            indicators['gamma_stability'] = 1.0 - indicators['gamma_flip_proximity']
            indicators['gamma_instability'] = indicators['gamma_flip_proximity']
            
            return indicators
            
        except Exception as e:
            logger.error(f"Indicator extraction error: {e}")
            return {}
    
    def _calculate_regime_score(self, regime_name: str, indicators: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate regime score based on weighted indicators"""
        try:
            score = 0.0
            total_weight = 0.0
            
            for indicator_name, weight in weights.items():
                if indicator_name in indicators:
                    indicator_value = indicators[indicator_name]
                    
                    # Apply regime-specific logic
                    if regime_name == "TREND":
                        if indicator_name == 'gamma_regime':
                            score += weight * max(0, indicator_value)
                        elif indicator_name == 'flow_direction':
                            score += weight * abs(indicator_value)
                        elif indicator_name == 'intent_score':
                            score += weight * indicator_value
                        elif indicator_name == 'pcr_trend':
                            score += weight * abs(indicator_value)
                        elif indicator_name == 'breach_probability':
                            score += weight * indicator_value
                    
                    elif regime_name == "RANGE":
                        if indicator_name == 'breach_probability':
                            score += weight * (1.0 - indicator_value)
                        elif indicator_name == 'expected_move_ratio':
                            score += weight * (1.0 - indicator_value)
                        elif indicator_name == 'gamma_regime':
                            score += weight * (1.0 - abs(indicator_value))
                        elif indicator_name == 'flow_balance':
                            score += weight * indicator_value
                        elif indicator_name == 'volatility_regime':
                            score += weight * (1.0 - abs(indicator_value - 0.5))
                    
                    elif regime_name == "BREAKOUT":
                        if indicator_name == 'breach_probability':
                            score += weight * indicator_value
                        elif indicator_name == 'volume_intensity':
                            score += weight * indicator_value
                        elif indicator_name == 'volatility_regime':
                            score += weight * indicator_value
                        elif indicator_name == 'flow_intensity':
                            score += weight * indicator_value
                        elif indicator_name == 'expected_move_ratio':
                            score += weight * indicator_value
                    
                    elif regime_name == "MEAN_REVERSION":
                        if indicator_name == 'gamma_regime':
                            score += weight * max(0, indicator_value)
                        elif indicator_name == 'pcr_trend':
                            score += weight * abs(indicator_value)
                        elif indicator_name == 'volatility_regime':
                            score += weight * (1.0 - indicator_value)
                        elif indicator_name == 'support_resistance_proximity':
                            score += weight * indicator_value
                        elif indicator_name == 'flow_intensity':
                            score += weight * (1.0 - indicator_value)
                    
                    elif regime_name == "HIGH_VOLATILITY":
                        if indicator_name == 'volatility_regime':
                            score += weight * indicator_value
                        elif indicator_name == 'expected_move_ratio':
                            score += weight * indicator_value
                        elif indicator_name == 'volume_intensity':
                            score += weight * indicator_value
                        elif indicator_name == 'gamma_instability':
                            score += weight * indicator_value
                    
                    elif regime_name == "LOW_VOLATILITY":
                        if indicator_name == 'volatility_regime':
                            score += weight * (1.0 - indicator_value)
                        elif indicator_name == 'expected_move_ratio':
                            score += weight * (1.0 - indicator_value)
                        elif indicator_name == 'volume_intensity':
                            score += weight * (1.0 - indicator_value)
                        elif indicator_name == 'gamma_stability':
                            score += weight * indicator_value
                    
                    total_weight += weight
            
            if total_weight > 0:
                return score / total_weight
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Regime score calculation error: {e}")
            return 0.5
    
    def _generate_regime_reasoning(self, regime_name: str, indicators: Dict[str, float], confidence: float) -> str:
        """Generate human-readable reasoning for regime detection"""
        try:
            reasoning_parts = []
            
            if regime_name == "TREND":
                if indicators.get('gamma_regime', 0) > 0.5:
                    reasoning_parts.append("Positive gamma indicates trend persistence")
                if indicators.get('flow_direction', 0) > 0.5:
                    reasoning_parts.append("Strong call flow supports uptrend")
                elif indicators.get('flow_direction', 0) < -0.5:
                    reasoning_parts.append("Strong put flow supports downtrend")
                if indicators.get('intent_score', 0) > 0.7:
                    reasoning_parts.append("High institutional intent confirms trend")
            
            elif regime_name == "RANGE":
                if indicators.get('breach_probability', 0.5) < 0.3:
                    reasoning_parts.append("Low breach probability suggests range-bound")
                if indicators.get('expected_move_ratio', 0.5) < 0.5:
                    reasoning_parts.append("Modest expected move supports range")
                if abs(indicators.get('gamma_regime', 0)) < 0.3:
                    reasoning_parts.append("Neutral gamma indicates range")
            
            elif regime_name == "BREAKOUT":
                if indicators.get('breach_probability', 0.5) > 0.6:
                    reasoning_parts.append("High breakout probability detected")
                if indicators.get('volume_intensity', 0.5) > 0.7:
                    reasoning_parts.append("Volume surge supports breakout")
                if indicators.get('volatility_regime', 0.5) > 0.7:
                    reasoning_parts.append("Elevated volatility precedes breakout")
            
            elif regime_name == "MEAN_REVERSION":
                if indicators.get('gamma_regime', 0) > 0.5:
                    reasoning_parts.append("Positive gamma suggests mean reversion")
                if abs(indicators.get('pcr_trend', 0)) > 0.3:
                    reasoning_parts.append("Extreme PCR indicates reversal potential")
                if indicators.get('support_resistance_proximity', 0.5) > 0.6:
                    reasoning_parts.append("Near key support/resistance levels")
            
            elif regime_name == "HIGH_VOLATILITY":
                if indicators.get('volatility_regime', 0.5) > 0.8:
                    reasoning_parts.append("Extreme volatility regime detected")
                if indicators.get('expected_move_ratio', 0.5) > 0.7:
                    reasoning_parts.append("Expanding expected move")
                if indicators.get('volume_intensity', 0.5) > 0.7:
                    reasoning_parts.append("High volume activity")
            
            elif regime_name == "LOW_VOLATILITY":
                if indicators.get('volatility_regime', 0.5) < 0.3:
                    reasoning_parts.append("Low volatility environment")
                if indicators.get('expected_move_ratio', 0.5) < 0.3:
                    reasoning_parts.append("Contracted expected move")
                if indicators.get('volume_intensity', 0.5) < 0.3:
                    reasoning_parts.append("Suppressed volume activity")
            
            # Add confidence level
            reasoning_parts.append(f"Confidence: {confidence:.1%}")
            
            return "; ".join(reasoning_parts) if reasoning_parts else f"Regime: {regime_name} with {confidence:.1%} confidence"
            
        except Exception as e:
            logger.error(f"Regime reasoning generation error: {e}")
            return f"Regime: {regime_name} with {confidence:.1%} confidence"
    
    async def _update_regime_history(self, symbol: str, regime: RegimeType, confidence: float, metrics: Dict[str, Any]) -> None:
        """Update regime history for analysis"""
        if symbol not in self.regime_history:
            self.regime_history[symbol] = []
        
        # Add new history point
        history_point = RegimeHistory(
            regime=regime,
            timestamp=datetime.now(timezone.utc),
            confidence=confidence,
            metrics=metrics.copy()
        )
        
        self.regime_history[symbol].append(history_point)
        
        # Limit history size
        if len(self.regime_history[symbol]) > self.MAX_HISTORY_POINTS:
            self.regime_history[symbol] = self.regime_history[symbol][-self.MAX_HISTORY_POINTS:]
        
        # Update regime start time if changed
        if len(self.regime_history[symbol]) >= 2:
            previous_regime = self.regime_history[symbol][-2].regime
            if previous_regime != regime:
                self.regime_start_times[symbol] = datetime.now(timezone.utc)
        elif symbol not in self.regime_start_times:
            self.regime_start_times[symbol] = datetime.now(timezone.utc)
    
    def _calculate_stability_score(self, symbol: str) -> float:
        """Calculate regime stability score (0-100)"""
        try:
            if symbol not in self.regime_start_times:
                return 50
            
            # Time-based stability
            start_time = self.regime_start_times[symbol]
            duration_minutes = (datetime.now(timezone.utc) - start_time).total_seconds() / 60
            
            # More time = more stable (up to a point)
            time_stability = min(100, duration_minutes / 2)
            
            # Consistency-based stability
            consistency_stability = self._calculate_historical_consistency(symbol)
            
            # Weighted combination
            stability_score = (time_stability * self.STABILITY_TIME_WEIGHT + 
                            consistency_stability * self.CONSISTENCY_WEIGHT)
            
            return min(100, max(0, stability_score))
            
        except Exception as e:
            logger.error(f"Error calculating stability score: {e}")
            return 50
    
    def _calculate_acceleration_index(self, symbol: str, current_metrics: Dict[str, Any], previous_metrics: Dict[str, Any]) -> float:
        """Calculate acceleration index (-100 to +100)"""
        try:
            if not previous_metrics:
                return 0
            
            acceleration_factors = []
            
            # Confidence acceleration
            current_confidence = current_metrics.get("regime_confidence", 50)
            previous_confidence = previous_metrics.get("regime_confidence", 50)
            confidence_change = current_confidence - previous_confidence
            acceleration_factors.append(confidence_change)
            
            # Net gamma acceleration
            current_gamma = current_metrics.get("net_gamma", 0)
            previous_gamma = previous_metrics.get("net_gamma", 0)
            
            if previous_gamma != 0:
                gamma_change_pct = ((current_gamma - previous_gamma) / abs(previous_gamma)) * 100
                gamma_acceleration = np.clip(gamma_change_pct / 2, -100, 100)
                acceleration_factors.append(gamma_acceleration)
            
            # Flow imbalance acceleration
            current_flow = current_metrics.get("flow_imbalance", 0)
            previous_flow = previous_metrics.get("flow_imbalance", 0)
            flow_change = abs(current_flow) - abs(previous_flow)
            flow_acceleration = np.clip(flow_change * 100, -100, 100)
            acceleration_factors.append(flow_acceleration)
            
            # Expected move acceleration
            current_expected = current_metrics.get("expected_move", 0)
            previous_expected = previous_metrics.get("expected_move", 0)
            
            if previous_expected > 0:
                expected_change_pct = ((current_expected - previous_expected) / previous_expected) * 100
                expected_acceleration = np.clip(expected_change_pct, -100, 100)
                acceleration_factors.append(expected_acceleration)
            
            # Calculate weighted average
            if acceleration_factors:
                acceleration_index = np.mean(acceleration_factors)
                return np.clip(acceleration_index, -100, 100)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating acceleration index: {e}")
            return 0
    
    def _calculate_transition_probability(self, symbol: str) -> float:
        """Calculate probability of regime change (0-100)"""
        try:
            if symbol not in self.regime_history or len(self.regime_history[symbol]) < self.MIN_HISTORY_POINTS:
                return 50
            
            history = self.regime_history[symbol]
            
            # Historical transition frequency
            transitions = 0
            for i in range(1, len(history)):
                if history[i].regime != history[i-1].regime:
                    transitions += 1
            
            total_periods = len(history) - 1
            if total_periods > 0:
                historical_transition_rate = transitions / total_periods
            else:
                historical_transition_rate = 0.1
            
            # Current stability factor
            stability_score = self._calculate_stability_score(symbol)
            stability_factor = (100 - stability_score) / 100
            
            # Acceleration factor
            current_metrics = history[-1].metrics if history else {}
            acceleration_index = current_metrics.get("acceleration_index", 0)
            acceleration_factor = abs(acceleration_index) / 100
            
            # Combine factors
            transition_probability = (
                historical_transition_rate * 40 +
                stability_factor * 30 +
                acceleration_factor * 30
            )
            
            return min(100, max(0, transition_probability * 100))
            
        except Exception as e:
            logger.error(f"Error calculating transition probability: {e}")
            return 50
    
    def _calculate_regime_duration(self, symbol: str) -> float:
        """Calculate current regime duration in minutes"""
        try:
            if symbol not in self.regime_start_times:
                return 0
            
            start_time = self.regime_start_times[symbol]
            duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            return duration_seconds / 60
            
        except Exception as e:
            logger.error(f"Error calculating regime duration: {e}")
            return 0
    
    def _calculate_historical_consistency(self, symbol: str) -> float:
        """Calculate how consistent the current regime has been historically"""
        try:
            if symbol not in self.regime_history or len(self.regime_history[symbol]) < self.MIN_HISTORY_POINTS:
                return 50
            
            history = self.regime_history[symbol]
            current_regime = history[-1].regime
            
            # Count occurrences of current regime in recent history
            recent_history = history[-20:]
            regime_count = sum(1 for h in recent_history if h.regime == current_regime)
            
            consistency = (regime_count / len(recent_history)) * 100
            return min(100, max(0, consistency))
            
        except Exception as e:
            logger.error(f"Error calculating historical consistency: {e}")
            return 50
    
    def _calculate_momentum_score(self, symbol: str, current_metrics: Dict[str, Any], previous_metrics: Dict[str, Any]) -> float:
        """Calculate momentum score for current regime characteristics (0-100)"""
        try:
            momentum_factors = []
            
            # Confidence momentum
            current_confidence = current_metrics.get("regime_confidence", 50)
            if current_confidence > 70:
                momentum_factors.append(current_confidence - 50)
            
            # Flow momentum
            flow_imbalance = abs(current_metrics.get("flow_imbalance", 0))
            if flow_imbalance > 0.3:
                momentum_factors.append(flow_imbalance * 50)
            
            # Gamma momentum
            net_gamma = abs(current_metrics.get("net_gamma", 0))
            if net_gamma > 1000000:
                gamma_momentum = min(50, net_gamma / 1000000 * 10)
                momentum_factors.append(gamma_momentum)
            
            # Expected move momentum
            expected_move = current_metrics.get("expected_move", 0)
            spot = current_metrics.get("spot", 1)
            if spot > 0:
                expected_move_pct = (expected_move / spot) * 100
                if expected_move_pct > 1:
                    momentum_factors.append(min(50, expected_move_pct * 10))
            
            if momentum_factors:
                momentum_score = np.mean(momentum_factors)
                return min(100, max(0, momentum_score))
            
            return 25
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return 25
    
    def _generate_dynamics_reasoning(self, regime: RegimeType, stability: float, acceleration: float, transition_prob: float) -> str:
        """Generate enhanced reasoning for regime dynamics"""
        try:
            reasoning_parts = [f"Regime: {regime.value}"]
            
            # Stability interpretation
            if stability >= 80:
                reasoning_parts.append("Very stable regime")
            elif stability >= 60:
                reasoning_parts.append("Stable regime")
            elif stability >= 40:
                reasoning_parts.append("Moderately stable regime")
            else:
                reasoning_parts.append("Unstable regime")
            
            # Acceleration interpretation
            if acceleration > 30:
                reasoning_parts.append("Strengthening rapidly")
            elif acceleration > 10:
                reasoning_parts.append("Strengthening")
            elif acceleration > -10:
                reasoning_parts.append("Stable")
            elif acceleration > -30:
                reasoning_parts.append("Weakening")
            else:
                reasoning_parts.append("Weakening rapidly")
            
            # Transition risk interpretation
            if transition_prob >= 70:
                reasoning_parts.append("High transition risk")
            elif transition_prob >= 40:
                reasoning_parts.append("Moderate transition risk")
            else:
                reasoning_parts.append("Low transition risk")
            
            return "; ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Error generating dynamics reasoning: {e}")
            return f"Regime: {regime.value} analysis"
    
    def _create_default_dynamics(self, symbol: str) -> RegimeDynamics:
        """Create default regime dynamics for error cases"""
        return RegimeDynamics(
            regime=RegimeType.UNKNOWN,
            confidence=50,
            stability_score=50,
            acceleration_index=0,
            transition_probability=50,
            regime_duration=0,
            historical_consistency=50,
            momentum_score=25,
            reasoning="Error in regime analysis",
            indicators={}
        )
    
    def format_for_frontend(self, dynamics: RegimeDynamics) -> Dict[str, Any]:
        """Format regime dynamics for frontend consumption"""
        return {
            "regime": dynamics.regime.value,
            "confidence": dynamics.confidence,
            "stability_score": dynamics.stability_score,
            "acceleration_index": dynamics.acceleration_index,
            "transition_probability": dynamics.transition_probability,
            "regime_duration_minutes": dynamics.regime_duration,
            "historical_consistency": dynamics.historical_consistency,
            "momentum_score": dynamics.momentum_score,
            "reasoning": dynamics.reasoning,
            "interpretation": {
                "stability_level": self._interpret_stability(dynamics.stability_score),
                "acceleration_trend": self._interpret_acceleration(dynamics.acceleration_index),
                "transition_risk": self._interpret_transition_risk(dynamics.transition_probability),
                "momentum_strength": self._interpret_momentum(dynamics.momentum_score)
            },
            "alerts": self._generate_regime_alerts(dynamics)
        }
    
    def _interpret_stability(self, stability_score: float) -> str:
        """Interpret stability score"""
        if stability_score >= 80:
            return "very_stable"
        elif stability_score >= 60:
            return "stable"
        elif stability_score >= 40:
            return "moderately_stable"
        else:
            return "unstable"
    
    def _interpret_acceleration(self, acceleration_index: float) -> str:
        """Interpret acceleration index"""
        if acceleration_index > 30:
            return "strengthening_rapidly"
        elif acceleration_index > 10:
            return "strengthening"
        elif acceleration_index > -10:
            return "stable"
        elif acceleration_index > -30:
            return "weakening"
        else:
            return "weakening_rapidly"
    
    def _interpret_transition_risk(self, transition_probability: float) -> str:
        """Interpret transition probability"""
        if transition_probability >= 70:
            return "high_risk"
        elif transition_probability >= 40:
            return "moderate_risk"
        else:
            return "low_risk"
    
    def _interpret_momentum(self, momentum_score: float) -> str:
        """Interpret momentum score"""
        if momentum_score >= 70:
            return "strong_momentum"
        elif momentum_score >= 40:
            return "moderate_momentum"
        else:
            return "weak_momentum"
    
    def _generate_regime_alerts(self, dynamics: RegimeDynamics) -> List[Dict[str, Any]]:
        """Generate alerts based on regime dynamics"""
        alerts = []
        
        # High transition risk alert
        if dynamics.transition_probability >= 70:
            alerts.append({
                "type": "transition_risk",
                "severity": "high",
                "message": f"High regime change risk ({dynamics.transition_probability:.0f}% probability)"
            })
        
        # Regime weakening alert
        if dynamics.acceleration_index < -30:
            alerts.append({
                "type": "regime_weakening",
                "severity": "medium",
                "message": f"Current regime weakening rapidly (acceleration: {dynamics.acceleration_index:.0f})"
            })
        
        # Low stability alert
        if dynamics.stability_score < 30:
            alerts.append({
                "type": "low_stability",
                "severity": "medium",
                "message": f"Regime stability low ({dynamics.stability_score:.0f}/100)"
            })
        
        # High momentum alert
        if dynamics.momentum_score >= 80:
            alerts.append({
                "type": "high_momentum",
                "severity": "low",
                "message": f"Strong regime momentum detected ({dynamics.momentum_score:.0f}/100)"
            })
        
        return alerts
