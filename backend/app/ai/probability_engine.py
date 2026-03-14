import logging
import asyncio
from typing import Dict, List, Any, Optional
import math
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from app.exceptions.data_unavailable_error import DataUnavailableError, MissingPremiumError
from app.ai.ml_training_engine import MLTrainingEngine

logger = logging.getLogger(__name__)

class ProbabilityEngine:
    """
    Enhanced Probability Engine with ML Model Integration
    
    Features:
    - Loads trained ML model at startup
    - Provides inference for trade success probability
    - Combines ML predictions with traditional probability calculations
    - Falls back to traditional calculations if model unavailable
    """
    
    def __init__(self, db_session=None):
        self.ml_engine = MLTrainingEngine(db_session)
        self.model_data = None
        self.model_loaded = False
        self.confidence_threshold = 0.6
        
        # Load model at startup
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load ML model at startup"""
        try:
            self.model_data = asyncio.run(self.ml_engine.load_model())
            if self.model_data:
                self.model_loaded = True
                self.model_version = self.model_data.get('model_version', 'unknown')
                self.feature_columns = self.model_data.get('feature_columns', [])
                logger.info(f"ProbabilityEngine: ML model loaded (version: {self.model_version})")
                return True
            else:
                logger.warning("ProbabilityEngine: No ML model found, using traditional calculations only")
                return False
        except Exception as e:
            logger.error(f"ProbabilityEngine: Error loading ML model: {e}")
            return False
    
    def _get_safe_default_result(self) -> Dict[str, Any]:
        """Return safe default result for error conditions"""
        return {
            'expected_move': 0.0,
            'upper_1sd': 0.0,
            'lower_1sd': 0.0,
            'upper_2sd': 0.0,
            'lower_2sd': 0.0,
            'breach_probability': 50.0,
            'range_hold_probability': 50.0,
            'volatility_state': 'fair',
            'implied_volatility': 0.0,
            'days_to_expiry': 0.0,
            'buy_probability': 0.5,
            'sell_probability': 0.5,
            'confidence_score': 0.0,
            'ml_enabled': self.model_loaded
        }
    
    async def predict(self, symbol: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make ML prediction for trade success probability
        
        Args:
            symbol: Trading symbol
            features: Feature dictionary from FeatureBuilder
            
        Returns:
            Prediction results with probabilities and confidence
        """
        try:
            if not self.model_loaded:
                logger.warning("ProbabilityEngine: ML model not loaded, returning default probabilities")
                return self._get_default_ml_result()
            
            # Convert features to DataFrame
            feature_df = self._prepare_features_for_prediction(features)
            
            if feature_df.empty:
                logger.warning("ProbabilityEngine: Empty features for prediction")
                return self._get_default_ml_result()
            
            # Make prediction using ML engine
            prediction_results = await self.ml_engine.predict(feature_df)
            
            if not prediction_results:
                logger.warning("ProbabilityEngine: ML prediction failed, returning default")
                return self._get_default_ml_result()
            
            # Prepare result
            result = {
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'buy_probability': prediction_results.get('buy_probability', 0.5),
                'sell_probability': prediction_results.get('sell_probability', 0.5),
                'confidence_score': prediction_results.get('confidence_score', 0.0),
                'model_version': prediction_results.get('model_version', 'unknown'),
                'feature_importance': prediction_results.get('feature_importance', {}),
                'ml_enabled': True,
                'prediction_successful': True
            }
            
            logger.info(f"ProbabilityEngine: ML prediction for {symbol} - Buy: {result['buy_probability']:.3f}, Confidence: {result['confidence_score']:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"ProbabilityEngine: Error in ML prediction: {e}")
            return self._get_default_ml_result()
    
    def _prepare_features_for_prediction(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Prepare features for ML prediction"""
        try:
            # Extract key features expected by the model
            feature_mapping = {
                'pcr': features.get('options_features', {}).get('pcr', 0),
                'gamma_exposure': features.get('options_features', {}).get('net_gamma', 0),
                'oi_velocity': features.get('options_features', {}).get('oi_change', 0),
                'volatility': features.get('volatility_features', {}).get('volatility_20', 0),
                'trend_strength': features.get('momentum_features', {}).get('trend_strength', 0),
                'liquidity_score': features.get('volume_features', {}).get('volume_trend', 0),
                'market_regime': features.get('regime_features', {}).get('regime_score', 0)
            }
            
            # Handle categorical encoding for market regime
            regime_value = feature_mapping.get('market_regime', 0)
            if isinstance(regime_value, str):
                # Simple encoding for regime strings
                regime_encoding = {
                    'trend': 1, 'range': 0, 'breakout': 2, 
                    'mean_reversion': -1, 'high_volatility': 3, 'low_volatility': -2
                }
                feature_mapping['market_regime'] = regime_encoding.get(regime_value.lower(), 0)
            
            # Create DataFrame
            df = pd.DataFrame([feature_mapping])
            
            # Ensure all required columns exist
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0  # Default value for missing features
            
            # Select and order columns according to model expectations
            df = df[self.feature_columns]
            
            return df
            
        except Exception as e:
            logger.error(f"Error preparing features for prediction: {e}")
            return pd.DataFrame()
    
    def _get_default_ml_result(self) -> Dict[str, Any]:
        """Return default ML result when model unavailable"""
        return {
            'symbol': 'unknown',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'buy_probability': 0.5,
            'sell_probability': 0.5,
            'confidence_score': 0.0,
            'model_version': 'none',
            'feature_importance': {},
            'ml_enabled': False,
            'prediction_successful': False
        }
    
    def calculate(self, option_chain):
        """
        Safe probability calculation with error handling
        """
        try:
            # For now, use static compute method
            # In future, this would call self.model.predict(option_chain)
            if not option_chain:
                logger.warning("ProbabilityEngine: Empty option_chain received")
                return self._get_safe_default_result()
                
            # Extract required data from option_chain
            spot_price = option_chain.get('spot', 0)
            calls = option_chain.get('calls', [])
            puts = option_chain.get('puts', [])
            volatility_context = option_chain.get('volatility_context', {})
            bias_score = option_chain.get('bias_score', 50)
            
            # FIX 10: Add validation for critical data
            if not spot_price or spot_price <= 0:
                logger.warning(f"ProbabilityEngine: Invalid spot_price {spot_price}")
                return self._get_safe_default_result()
            
            if not calls or not puts:
                logger.warning("ProbabilityEngine: Empty calls or puts data")
                return self._get_safe_default_result()
            
            if not isinstance(calls, list) or not isinstance(puts, list):
                logger.warning("ProbabilityEngine: Invalid calls/puts data type")
                return self._get_safe_default_result()
            
            result = self.compute_expected_move(
                spot_price, calls, puts, volatility_context, bias_score
            )
            
            logger.info(f"ProbabilityEngine: Calculation successful")
            return result
            
        except Exception as e:
            logger.error(f"ProbabilityEngine Error: {str(e)}")
            return self._get_safe_default_result()
    
    @staticmethod
    def compute_expected_move(
        spot_price: float,
        calls: List[Dict[str, Any]],
        puts: List[Dict[str, Any]],
        volatility_context: Dict[str, Any],
        bias_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Compute expected move using production-grade formula: Expected Move = Spot × IV × sqrt(T)
        
        Args:
            spot_price: Current spot price
            calls: List of call option contracts
            puts: List of put option contracts
            volatility_context: Volatility regime information
            bias_score: Current bias score (0-100)
            
        Returns:
            Structured probability output with expected move calculations
        """
        try:
            # Validation Layer - Fail-Safe Mode
            if not spot_price or not calls or not puts:
                logger.error(f"[PROBABILITY] Invalid inputs - spot: {spot_price}, calls: {len(calls)}, puts: {len(puts)}")
                raise DataUnavailableError("Invalid inputs for probability calculation")
            
            if spot_price <= 0:
                raise DataUnavailableError("Invalid spot price for probability calculation")
                
            # Calculate days to expiry from option chain data
            days_to_expiry = ProbabilityEngine._calculate_days_to_expiry(calls, puts)
            if days_to_expiry <= 0:
                days_to_expiry = 7  # Default to 1 week
            
            logger.info(f"[PROBABILITY] Days to expiry: {days_to_expiry}")
            
            # Calculate implied volatility from ATM options
            implied_volatility = ProbabilityEngine._calculate_implied_volatility(
                spot_price, calls, puts
            )
            
            logger.info(f"[PROBABILITY] Implied volatility: {implied_volatility}")
            
            # Production-grade expected move formula: Expected Move = Spot × IV × sqrt(T)
            time_fraction = days_to_expiry / 365.25  # Convert days to years
            expected_move = spot_price * implied_volatility * math.sqrt(time_fraction)
            
            logger.info(f"[PROBABILITY] Expected move: {expected_move} (spot: {spot_price}, iv: {implied_volatility}, time: {time_fraction})")
            
            # Compute standard deviation ranges
            ranges = ProbabilityEngine._compute_ranges(spot_price, expected_move)
            
            # Compute probabilities with regime adjustment
            probabilities = ProbabilityEngine._compute_probabilities(
                volatility_context, bias_score
            )
            
            # Determine volatility pricing state
            volatility_state = ProbabilityEngine._determine_volatility_state(volatility_context)
            
            return {
                "expected_move": round(expected_move, 2),
                "upper_1sd": round(ranges["upper_1sd"], 2),
                "lower_1sd": round(ranges["lower_1sd"], 2),
                "upper_2sd": round(ranges["upper_2sd"], 2),
                "lower_2sd": round(ranges["lower_2sd"], 2),
                "breach_probability": probabilities["breach"] * 100,
                "range_hold_probability": probabilities["range_hold"] * 100,
                "volatility_state": volatility_state,
                "implied_volatility": round(implied_volatility, 4),
                "days_to_expiry": days_to_expiry
            }
            
        except Exception as e:
            # Engine never crashes - raise proper error on any error
            logger.error(f"[PROBABILITY] Calculation failed: {e}")
            raise DataUnavailableError(f"Probability calculation failed: {e}")
    
    @staticmethod
    def _calculate_days_to_expiry(calls: List[Dict], puts: List[Dict]) -> int:
        """Calculate days to expiry from option chain data."""
        try:
            # Extract expiry date from first available option
            expiry_date = None
            for option in calls + puts:
                expiry = option.get('expiry_date')
                if expiry:
                    expiry_date = expiry
                    break
            
            if not expiry_date:
                logger.warning("[PROBABILITY] No expiry date found, using default 7 days")
                return 7  # Default to 1 week
            
            logger.info(f"[PROBABILITY] Found expiry date: {expiry_date}")
            
            # Parse expiry date and calculate days remaining
            from datetime import datetime
            try:
                expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
            except ValueError:
                # Try other date formats
                try:
                    expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.error(f"[PROBABILITY] Cannot parse expiry date: {expiry_date}")
                    return 7
            
            current_dt = datetime.now()
            days_remaining = (expiry_dt - current_dt).days
            
            logger.info(f"[PROBABILITY] Days remaining: {days_remaining}")
            
            return max(1, days_remaining)  # Ensure at least 1 day
            
        except Exception as e:
            logger.error(f"[PROBABILITY] Error calculating days to expiry: {e}")
            return 7  # Default fallback
    
    @staticmethod
    def _calculate_implied_volatility(spot_price: float, calls: List[Dict], puts: List[Dict]) -> float:
        """
        Calculate implied volatility using improved approximation.
        This is still an approximation but better than straddle method.
        """
        try:
            # Find ATM strike
            atm_strike = None
            min_distance = float('inf')
            
            for option in calls + puts:
                strike = option.get('strike', 0)
                if strike > 0:
                    distance = abs(strike - spot_price)
                    if distance < min_distance:
                        min_distance = distance
                        atm_strike = strike
            
            logger.info(f"[PROBABILITY] ATM strike: {atm_strike} (spot: {spot_price})")
            
            if not atm_strike:
                logger.warning("[PROBABILITY] No ATM strike found, using default IV 0.20")
                return 0.20  # Default 20% IV
            
            # Get ATM option premiums
            atm_call_premium = None
            atm_put_premium = None
            
            for call in calls:
                if call.get('strike') == atm_strike:
                    premium = call.get('ltp', 0) or call.get('premium', 0)
                    logger.info(f"[PROBABILITY] ATM call premium: {premium}")
                    if premium > 0:
                        atm_call_premium = premium
                    break
            
            for put in puts:
                if put.get('strike') == atm_strike:
                    premium = put.get('ltp', 0) or put.get('premium', 0)
                    logger.info(f"[PROBABILITY] ATM put premium: {premium}")
                    if premium > 0:
                        atm_put_premium = premium
                    break
            
            # Calculate straddle price
            straddle_price = (atm_call_premium or 0) + (atm_put_premium or 0)
            logger.info(f"[PROBABILITY] Straddle price: {straddle_price}")
            
            if straddle_price <= 0:
                logger.warning("[PROBABILITY] No valid premiums, using default IV 0.20")
                return 0.20  # Default IV if no premium data
            
            # Improved IV approximation using straddle as percentage of spot
            # This is better than the previous fixed multiplier
            straddle_percentage = straddle_price / spot_price
            
            # Convert to annualized IV (rough approximation)
            # For ATM options, IV ≈ straddle_price / (spot * sqrt(T/365)) * sqrt(π/2)
            # Simplified for short-term options
            days_to_expiry = 7  # Default assumption
            time_fraction = days_to_expiry / 365.25
            
            # Better approximation accounting for time decay
            iv_approximation = (straddle_percentage / math.sqrt(time_fraction)) * 0.8
            
            logger.info(f"[PROBABILITY] IV approximation: {iv_approximation}")
            
            # Normalize to reasonable IV range (10% - 100%)
            iv_approximation = max(0.10, min(1.0, iv_approximation))
            
            logger.info(f"[PROBABILITY] Final IV: {iv_approximation}")
            
            return iv_approximation
            
        except Exception as e:
            logger.error(f"Error calculating implied volatility: {e}")
            return 0.20  # Default fallback
    
    @staticmethod
    def _compute_ranges(spot_price: float, expected_move: float) -> Dict[str, float]:
        """
        Compute 1SD and 2SD ranges.
        """
        return {
            "upper_1sd": spot_price + expected_move,
            "lower_1sd": spot_price - expected_move,
            "upper_2sd": spot_price + (2 * expected_move),
            "lower_2sd": spot_price - (2 * expected_move)
        }
    
    @staticmethod
    def _compute_probabilities(volatility_context: Dict[str, Any], bias_score: float) -> Dict[str, float]:
        """
        Compute breach and range hold probabilities with regime adjustment.
        """
        # Base probabilities (normal distribution)
        base_range_hold = 0.68  # 1SD contains ~68%
        base_breach = 0.32      # Complement
        
        # Regime adjustment
        adjustment = 0.0
        
        # Increase breach probability in extreme volatility or strong bias
        if (volatility_context.get('current') == 'extreme' or 
            bias_score > 75 or 
            bias_score < 25):
            adjustment = 0.05
        
        # Apply adjustment
        breach_probability = base_breach + adjustment
        range_hold_probability = base_range_hold - adjustment
        
        # Clamp probabilities
        breach_probability = max(0.05, min(0.75, breach_probability))
        range_hold_probability = max(0.25, min(0.95, range_hold_probability))
        
        return {
            "breach": breach_probability,
            "range_hold": range_hold_probability
        }
    
    @staticmethod
    def _determine_volatility_state(volatility_context: Dict[str, Any]) -> str:
        """
        Determine volatility pricing state based on percentile.
        """
        percentile = volatility_context.get('percentile', 50)
        
        if percentile > 80:
            return "overpriced"
        elif percentile < 20:
            return "underpriced"
        else:
            return "fair"
