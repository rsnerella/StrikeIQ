import logging
from typing import Dict, Any, List, Optional
from ..ai.probability_engine import ProbabilityEngine
from ..exceptions.data_unavailable_error import DataUnavailableError

logger = logging.getLogger(__name__)

class IntelligenceAggregator:
    
    @staticmethod
    def aggregate_intelligence(
        raw_analytics: Dict[str, Any],
        market_data: Dict[str, Any],
        calls: List[Dict[str, Any]],
        puts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate all intelligence layers into unified MarketIntelligence object.
        
        Args:
            raw_analytics: Raw analytics from option chain
            market_data: Market data with spot price
            calls: Call option contracts
            puts: Put option contracts
            
        Returns:
            Unified MarketIntelligence object with fail-safe handling
        """
        try:
            logger.info(f"[INTELLIGENCE DEBUG] Starting aggregation - analytics: {raw_analytics}")
            logger.info(f"[INTELLIGENCE DEBUG] Market data: {market_data}")
            
            # Validate inputs
            if not raw_analytics or not market_data:
                raise DataUnavailableError("Invalid inputs for intelligence aggregation")
            
            # Compute bias intelligence
            bias = IntelligenceAggregator._compute_bias(raw_analytics)
            logger.info(f"[INTELLIGENCE DEBUG] Computed bias: {bias}")
            
            # Compute volatility regime
            volatility = IntelligenceAggregator._compute_volatility_regime(raw_analytics)
            logger.info(f"[INTELLIGENCE DEBUG] Computed volatility: {volatility}")
            
            # Compute liquidity intelligence
            liquidity = IntelligenceAggregator._compute_liquidity(raw_analytics)
            logger.info(f"[INTELLIGENCE DEBUG] Computed liquidity: {liquidity}")
            
            # Compute probability intelligence
            probability = IntelligenceAggregator._compute_probability(
                market_data, calls, puts, volatility, bias
            )
            logger.info(f"[INTELLIGENCE DEBUG] Computed probability: {probability}")
            
            # Overall confidence
            confidence = min(bias['confidence'] + 0.1, 1.0)
            
            intelligence = {
                "bias": bias,
                "volatility": volatility,
                "liquidity": liquidity,
                "probability": probability,
                "timestamp": market_data.get("timestamp", ""),
                "confidence": confidence,
                "analytics_enabled": True
            }
            
            logger.info(f"[INTELLIGENCE DEBUG] Final intelligence object: {intelligence}")
            return intelligence
            
        except DataUnavailableError as e:
            # Engine failed - return disabled state
            logger.warning(f"[INTELLIGENCE] Engine failed, disabling analytics: {e}")
            return {
                "bias": {"score": 0, "label": "NEUTRAL", "confidence": 0.0},
                "volatility": {"current": "normal", "risk": "medium"},
                "liquidity": {"total_oi": 0},
                "probability": {
                    "expected_move": 0,
                    "upper_1sd": 0,
                    "lower_1sd": 0,
                    "upper_2sd": 0,
                    "lower_2sd": 0,
                    "breach_probability": 0,
                    "range_hold_probability": 0,
                    "volatility_state": "unknown"
                },
                "timestamp": market_data.get("timestamp", ""),
                "confidence": 0.0,
                "analytics_enabled": False,
                "engine_mode": "DISABLED",
                "reason": str(e)
            }
            
        except Exception as e:
            # Never crash - return minimal safe structure
            logger.error(f"[INTELLIGENCE DEBUG] Exception in aggregation: {e}")
            return {
                "bias": {"score": 0, "label": "NEUTRAL", "confidence": 0.0},
                "volatility": {"current": "normal", "risk": "medium"},
                "liquidity": {"total_oi": 0},
                "probability": {
                    "expected_move": 0,
                    "upper_1sd": 0,
                    "lower_1sd": 0,
                    "upper_2sd": 0,
                    "lower_2sd": 0,
                    "breach_probability": 0,
                    "range_hold_probability": 0,
                    "volatility_state": "unknown"
                },
                "timestamp": market_data.get("timestamp", ""),
                "confidence": 0.0,
                "analytics_enabled": False,
                "engine_mode": "DISABLED",
                "reason": f"Unexpected error: {e}"
            }
    
    @staticmethod
    def _compute_bias(raw_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute bias intelligence from raw analytics."""
        score = raw_analytics.get("bias_score", 0)
        label = raw_analytics.get("bias_label", "NEUTRAL")
        
        direction = "bullish" if "BULL" in label else "bearish" if "BEAR" in label else "neutral"
        strength = score / 100
        confidence = min(score + 10, 100) / 100
        
        signal = "strong" if score >= 70 else "moderate" if score >= 55 else "weak"
        
        return {
            "score": score,
            "label": label,
            "strength": strength,
            "direction": direction,
            "confidence": confidence,
            "signal": signal
        }
    
    @staticmethod
    def _compute_volatility_regime(raw_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute volatility regime (placeholder for now)."""
        # Placeholder: Would use IV data in real implementation
        percentile = 50  # Mock percentile
        trend = "stable"  # Mock trend
        
        if percentile < 25:
            current = "low"
            risk = "low"
        elif percentile < 50:
            current = "normal"
            risk = "medium"
        elif percentile < 75:
            current = "elevated"
            risk = "high"
        else:
            current = "extreme"
            risk = "extreme"
        
        # Determine market environment
        if current == "low" and trend == "stable":
            environment = "accumulation"
        elif current == "extreme" and trend == "rising":
            environment = "expansion"
        elif current == "elevated" and trend == "falling":
            environment = "distribution"
        else:
            environment = "compression"
        
        return {
            "current": current,
            "percentile": percentile,
            "trend": trend,
            "risk": risk,
            "environment": environment
        }
    
    @staticmethod
    def _compute_liquidity(raw_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute liquidity intelligence."""
        total_oi = raw_analytics.get("total_call_oi", 0) + raw_analytics.get("total_put_oi", 0)
        concentration = abs(raw_analytics.get("oi_dominance", 0))
        
        # Mock flow direction
        flow_direction = "inflow" if concentration > 0.1 else "balanced"
        
        return {
            "total_oi": total_oi,
            "oi_change_24h": 0,  # Would need historical data
            "concentration": concentration,
            "depth_score": min(total_oi / 1000000, 100),
            "flow_direction": flow_direction
        }
    
    @staticmethod
    def _compute_probability(
        market_data: Dict[str, Any],
        calls: List[Dict[str, Any]],
        puts: List[Dict[str, Any]],
        volatility: Dict[str, Any],
        bias: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Compute probability intelligence using ProbabilityEngine."""
        try:
            # Extract spot price safely
            spot_price = market_data.get("spot_price")
            
            # Handle missing spot price gracefully
            if spot_price is None:
                logger.warning("[PROBABILITY DEBUG] No spot price provided, using fallback")
                return {
                    "expected_move": 0,
                    "upper_1sd": 0,
                    "lower_1sd": 0,
                    "upper_2sd": 0,
                    "lower_2sd": 0,
                    "breach_probability": 0,
                    "range_hold_probability": 100,
                    "volatility_state": "unknown"
                }
            
            # Validate spot price is positive
            if not isinstance(spot_price, (int, float)) or spot_price <= 0:
                logger.error(f"[PROBABILITY DEBUG] Invalid spot price: {spot_price}")
                return {
                    "expected_move": 0,
                    "upper_1sd": 0,
                    "lower_1sd": 0,
                    "upper_2sd": 0,
                    "lower_2sd": 0,
                    "breach_probability": 0,
                    "range_hold_probability": 100,
                    "volatility_state": "unknown"
                }
            
            logger.info(f"[PROBABILITY DEBUG] Spot: {spot_price}")
            logger.info(f"[PROBABILITY DEBUG] Calls: {len(calls)}")
            logger.info(f"[PROBABILITY DEBUG] Puts: {len(puts)}")
            
            result = ProbabilityEngine.compute_expected_move(
                spot_price=spot_price,
                calls=calls,
                puts=puts,
                volatility_context=volatility,
                bias_score=bias.get("score", 0)
            )
            
            logger.info(f"[PROBABILITY DEBUG] ProbabilityEngine result: {result}")
            
            # Always return a probability object, even if engine returns None
            if result is None:
                logger.warning("[PROBABILITY DEBUG] Engine returned None, using fallback")
                return {
                    "expected_move": 0,
                    "upper_1sd": spot_price,
                    "lower_1sd": spot_price,
                    "upper_2sd": spot_price,
                    "lower_2sd": spot_price,
                    "breach_probability": 0,
                    "range_hold_probability": 100,
                    "volatility_state": "unknown"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Probability Engine Error: {e}")
            return {
                "expected_move": 0,
                "upper_1sd": market_data.get("spot_price", 0),
                "lower_1sd": market_data.get("spot_price", 0),
                "upper_2sd": market_data.get("spot_price", 0),
                "lower_2sd": market_data.get("spot_price", 0),
                "breach_probability": 0,
                "range_hold_probability": 100,
                "volatility_state": "unknown"
            }
