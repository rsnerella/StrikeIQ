"""
Feature Builder - Unified Feature Engineering for ML/AI
Consolidates feature_builder.py, dataset_builder.py, and related feature engineering
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json
from sqlalchemy.orm import Session
from app.models.ai_features import AIFeature

logger = logging.getLogger(__name__)

@dataclass
class MarketFeatures:
    """Unified market features representation"""
    symbol: str
    timestamp: datetime
    price_features: Dict[str, float]
    volume_features: Dict[str, float]
    volatility_features: Dict[str, float]
    momentum_features: Dict[str, float]
    technical_features: Dict[str, float]
    options_features: Dict[str, float]
    sentiment_features: Dict[str, float]
    regime_features: Dict[str, float]

@dataclass
class FeatureDataset:
    """Dataset of features for ML training"""
    symbol: str
    features: List[MarketFeatures]
    target_variables: Dict[str, List[float]]
    metadata: Dict[str, Any]

class FeatureBuilder:
    """
    Unified Feature Builder
    
    Consolidates:
    - Feature engineering (from services/feature_builder.py)
    - Dataset building (from services/training_dataset_builder.py)
    - ML feature preparation
    
    Features:
    - Price-based features (returns, ratios, etc.)
    - Volume-based features (volume profiles, flow analysis)
    - Volatility features (ATR, implied vol, etc.)
    - Momentum features (RSI, MACD, etc.)
    - Technical indicators (moving averages, etc.)
    - Options features (PCR, greeks, etc.)
    - Market sentiment features
    - Regime classification features
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        # Database session for feature persistence
        self.db_session = db_session
        
        # Feature calculation parameters
        self.price_window_sizes = [5, 10, 20, 50]  # For moving averages, etc.
        self.volume_window_sizes = [5, 10, 20]
        self.volatility_window_sizes = [10, 20, 50]
        
        # Technical indicator parameters
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bollinger_period = 20
        self.bollinger_std = 2
        
        # Feature storage
        self.feature_history: Dict[str, List[MarketFeatures]] = defaultdict(list)
        self.max_history_size = 1000
        
        # Dataset building parameters
        self.target_horizons = [1, 5, 10, 20]  # Future periods to predict
        self.min_samples_for_training = 100
        
        logger.info("FeatureBuilder initialized - Unified feature engineering")
    
    async def build_features(
        self, 
        symbol: str,
        price_data: List[Dict[str, Any]],
        volume_data: List[Dict[str, Any]],
        options_data: Optional[Dict[str, Any]] = None,
        market_metrics: Optional[Dict[str, Any]] = None
    ) -> MarketFeatures:
        """
        Build comprehensive features for a symbol
        """
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Convert to DataFrames for easier processing
            price_df = pd.DataFrame(price_data)
            volume_df = pd.DataFrame(volume_data)
            
            # Build feature groups
            price_features = self._build_price_features(price_df)
            volume_features = self._build_volume_features(volume_df)
            volatility_features = self._build_volatility_features(price_df)
            momentum_features = self._build_momentum_features(price_df)
            technical_features = self._build_technical_features(price_df)
            options_features = self._build_options_features(options_data)
            sentiment_features = self._build_sentiment_features(market_metrics)
            regime_features = self._build_regime_features(market_metrics)
            
            # Create unified features
            features = MarketFeatures(
                symbol=symbol,
                timestamp=timestamp,
                price_features=price_features,
                volume_features=volume_features,
                volatility_features=volatility_features,
                momentum_features=momentum_features,
                technical_features=technical_features,
                options_features=options_features,
                sentiment_features=sentiment_features,
                regime_features=regime_features
            )
            
            # Store in history
            self._store_features(symbol, features)
            
            # Store features in database
            if self.db_session:
                await self._persist_features_to_db(symbol, features)
            
            logger.debug(f"Built features for {symbol}: {len(price_features)} price, {len(volume_features)} volume features")
            return features
            
        except Exception as e:
            logger.error(f"Error building features for {symbol}: {e}")
            return self._create_default_features(symbol)
    
    def _build_price_features(self, price_df: pd.DataFrame) -> Dict[str, float]:
        """Build price-based features"""
        try:
            if price_df.empty or len(price_df) < 2:
                return {}
            
            features = {}
            
            # Basic price statistics
            current_price = price_df.iloc[-1]['close']
            features['current_price'] = current_price
            features['price_change'] = current_price - price_df.iloc[-2]['close']
            features['price_change_pct'] = (features['price_change'] / price_df.iloc[-2]['close']) * 100
            
            # High/Low statistics
            features['current_high'] = price_df.iloc[-1]['high']
            features['current_low'] = price_df.iloc[-1]['low']
            features['current_range'] = features['current_high'] - features['current_low']
            features['range_pct'] = (features['current_range'] / current_price) * 100
            
            # Moving averages
            for window in self.price_window_sizes:
                if len(price_df) >= window:
                    ma = price_df['close'].rolling(window).iloc[-1]
                    features[f'ma_{window}'] = ma
                    features[f'price_above_ma_{window}'] = (current_price - ma) / ma * 100
                    features[f'ma_slope_{window}'] = self._calculate_slope(price_df['close'], window)
            
            # Price position relative to recent ranges
            for window in [10, 20, 50]:
                if len(price_df) >= window:
                    recent_high = price_df['high'].tail(window).max()
                    recent_low = price_df['low'].tail(window).min()
                    features[f'position_{window}'] = (current_price - recent_low) / (recent_high - recent_low)
            
            return features
            
        except Exception as e:
            logger.error(f"Error building price features: {e}")
            return {}
    
    def _build_volume_features(self, volume_df: pd.DataFrame) -> Dict[str, float]:
        """Build volume-based features"""
        try:
            if volume_df.empty or len(volume_df) < 2:
                return {}
            
            features = {}
            
            # Basic volume statistics
            current_volume = volume_df.iloc[-1]['volume']
            features['current_volume'] = current_volume
            features['volume_change'] = current_volume - volume_df.iloc[-2]['volume']
            features['volume_change_pct'] = (features['volume_change'] / max(volume_df.iloc[-2]['volume'], 1)) * 100
            
            # Volume moving averages
            for window in self.volume_window_sizes:
                if len(volume_df) >= window:
                    vol_ma = volume_df['volume'].rolling(window).iloc[-1]
                    features[f'volume_ma_{window}'] = vol_ma
                    features[f'volume_above_ma_{window}'] = (current_volume - vol_ma) / max(vol_ma, 1) * 100
            
            # Volume profile features
            if len(volume_df) >= 20:
                volume_std = volume_df['volume'].tail(20).std()
                features['volume_volatility'] = volume_std / max(current_volume, 1)
                features['volume_trend'] = self._calculate_slope(volume_df['volume'], 10)
            
            # Volume-price relationship
            if len(volume_df) >= 10:
                price_change = volume_df['close'].pct_change().tail(10)
                volume_change = volume_df['volume'].pct_change().tail(10)
                correlation = price_change.corr(volume_change)
                features['price_volume_correlation'] = correlation if not pd.isna(correlation) else 0
            
            return features
            
        except Exception as e:
            logger.error(f"Error building volume features: {e}")
            return {}
    
    def _build_volatility_features(self, price_df: pd.DataFrame) -> Dict[str, float]:
        """Build volatility features"""
        try:
            if price_df.empty or len(price_df) < 2:
                return {}
            
            features = {}
            
            # Price volatility (standard deviation of returns)
            returns = price_df['close'].pct_change().dropna()
            
            for window in self.volatility_window_sizes:
                if len(returns) >= window:
                    vol = returns.tail(window).std()
                    features[f'volatility_{window}'] = vol
                    features[f'volatility_{window}_annualized'] = vol * np.sqrt(252)  # Annualized
            
            # ATR (Average True Range)
            if len(price_df) >= 14:
                tr = self._calculate_true_range(price_df)
                atr = tr.rolling(14).mean().iloc[-1]
                features['atr'] = atr
                features['atr_pct'] = (atr / price_df.iloc[-1]['close']) * 100
            
            # Bollinger Bands
            if len(price_df) >= self.bollinger_period:
                bb_ma = price_df['close'].rolling(self.bollinger_period).mean()
                bb_std = price_df['close'].rolling(self.bollinger_period).std()
                
                current_price = price_df.iloc[-1]['close']
                upper_band = bb_ma.iloc[-1] + (bb_std.iloc[-1] * self.bollinger_std)
                lower_band = bb_ma.iloc[-1] - (bb_std.iloc[-1] * self.bollinger_std)
                
                features['bb_upper'] = upper_band
                features['bb_lower'] = lower_band
                features['bb_width'] = (upper_band - lower_band) / current_price * 100
                features['bb_position'] = (current_price - lower_band) / (upper_band - lower_band)
            
            # Volatility regime
            if len(returns) >= 50:
                recent_vol = returns.tail(20).std()
                historical_vol = returns.tail(50).std()
                features['volatility_regime'] = recent_vol / historical_vol
            
            return features
            
        except Exception as e:
            logger.error(f"Error building volatility features: {e}")
            return {}
    
    def _build_momentum_features(self, price_df: pd.DataFrame) -> Dict[str, float]:
        """Build momentum indicators"""
        try:
            if price_df.empty or len(price_df) < 2:
                return {}
            
            features = {}
            returns = price_df['close'].pct_change().dropna()
            
            # RSI (Relative Strength Index)
            if len(returns) >= self.rsi_period + 1:
                rsi = self._calculate_rsi(price_df['close'], self.rsi_period)
                features['rsi'] = rsi
                features['rsi_overbought'] = 1 if rsi > 70 else 0
                features['rsi_oversold'] = 1 if rsi < 30 else 0
            
            # MACD (Moving Average Convergence Divergence)
            if len(price_df) >= self.macd_slow:
                macd_line, signal_line, histogram = self._calculate_macd(price_df['close'])
                features['macd'] = macd_line
                features['macd_signal'] = signal_line
                features['macd_histogram'] = histogram
                features['macd_bullish'] = 1 if macd_line > signal_line else 0
            
            # Rate of Change (ROC)
            for period in [5, 10, 20]:
                if len(price_df) > period:
                    roc = ((price_df['close'].iloc[-1] - price_df['close'].iloc[-period-1]) / 
                          price_df['close'].iloc[-period-1]) * 100
                    features[f'roc_{period}'] = roc
            
            # Momentum score
            if len(returns) >= 10:
                momentum = returns.tail(10).mean() / returns.tail(10).std()
                features['momentum_score'] = momentum
            
            return features
            
        except Exception as e:
            logger.error(f"Error building momentum features: {e}")
            return {}
    
    def _build_technical_features(self, price_df: pd.DataFrame) -> Dict[str, float]:
        """Build technical analysis features"""
        try:
            if price_df.empty or len(price_df) < 2:
                return {}
            
            features = {}
            
            # Support/Resistance levels
            if len(price_df) >= 20:
                recent_highs = price_df['high'].tail(20).nlargest(5)
                recent_lows = price_df['low'].tail(20).nsmallest(5)
                
                current_price = price_df.iloc[-1]['close']
                
                # Distance to nearest resistance
                resistance_levels = recent_highs[recent_highs > current_price]
                if not resistance_levels.empty:
                    nearest_resistance = resistance_levels.min()
                    features['distance_to_resistance'] = (nearest_resistance - current_price) / current_price * 100
                else:
                    features['distance_to_resistance'] = 0
                
                # Distance to nearest support
                support_levels = recent_lows[recent_lows < current_price]
                if not support_levels.empty:
                    nearest_support = support_levels.max()
                    features['distance_to_support'] = (current_price - nearest_support) / current_price * 100
                else:
                    features['distance_to_support'] = 0
            
            # Trend strength
            for window in [10, 20]:
                if len(price_df) >= window:
                    trend = self._calculate_trend_strength(price_df['close'], window)
                    features[f'trend_strength_{window}'] = trend
            
            # Price patterns
            if len(price_df) >= 5:
                # Higher highs, higher lows (uptrend)
                highs = price_df['high'].tail(5)
                lows = price_df['low'].tail(5)
                
                hh = (highs.iloc[-1] > highs.iloc[-2]) and (highs.iloc[-2] > highs.iloc[-3])
                hl = (lows.iloc[-1] > lows.iloc[-2]) and (lows.iloc[-2] > lows.iloc[-3])
                
                features['uptrend_pattern'] = 1 if (hh and hl) else 0
                
                # Lower highs, lower lows (downtrend)
                lh = (highs.iloc[-1] < highs.iloc[-2]) and (highs.iloc[-2] < highs.iloc[-3])
                ll = (lows.iloc[-1] < lows.iloc[-2]) and (lows.iloc[-2] < lows.iloc[-3])
                
                features['downtrend_pattern'] = 1 if (lh and ll) else 0
            
            return features
            
        except Exception as e:
            logger.error(f"Error building technical features: {e}")
            return {}
    
    def _build_options_features(self, options_data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Build options-related features"""
        try:
            if not options_data:
                return {}
            
            features = {}
            
            # Put-Call Ratio (PCR)
            total_call_oi = options_data.get('total_call_oi', 0)
            total_put_oi = options_data.get('total_put_oi', 0)
            
            if total_call_oi > 0:
                features['pcr'] = total_put_oi / total_call_oi
                features['pcr_high'] = 1 if features['pcr'] > 1.3 else 0
                features['pcr_low'] = 1 if features['pcr'] < 0.7 else 0
            
            # Options volume
            total_call_volume = options_data.get('total_call_volume', 0)
            total_put_volume = options_data.get('total_put_volume', 0)
            
            features['total_options_volume'] = total_call_volume + total_put_volume
            if total_put_volume > 0:
                features['put_call_volume_ratio'] = total_put_volume / total_call_volume
            
            # Implied volatility
            iv = options_data.get('average_iv', 0)
            features['implied_volatility'] = iv
            
            # ATM straddle
            atm_straddle = options_data.get('atm_straddle', 0)
            spot_price = options_data.get('spot_price', 1)
            if spot_price > 0:
                features['straddle_pct'] = (atm_straddle / spot_price) * 100
                features['expected_move'] = features['straddle_pct'] / 2  # Rough estimate
            
            # Open interest changes
            oi_change = options_data.get('total_oi_change', 0)
            features['oi_change'] = oi_change
            
            # Gamma exposure
            gamma = options_data.get('net_gamma', 0)
            features['net_gamma'] = gamma
            features['gamma_exposure'] = abs(gamma) / spot_price if spot_price > 0 else 0
            
            return features
            
        except Exception as e:
            logger.error(f"Error building options features: {e}")
            return {}
    
    def _build_sentiment_features(self, market_metrics: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Build market sentiment features"""
        try:
            if not market_metrics:
                return {}
            
            features = {}
            
            # Flow imbalance
            flow_imbalance = market_metrics.get('flow_imbalance', 0)
            features['flow_imbalance'] = abs(flow_imbalance)
            features['flow_direction_bullish'] = 1 if market_metrics.get('flow_direction') == 'call' else 0
            
            # Intent score
            intent_score = market_metrics.get('intent_score', 50)
            features['intent_score'] = intent_score
            features['high_intent'] = 1 if intent_score > 70 else 0
            
            # Breach probability
            breach_prob = market_metrics.get('breach_probability', 37)
            features['breach_probability'] = breach_prob / 100  # Normalize to 0-1
            
            # Volatility regime
            vol_regime = market_metrics.get('volatility_regime', 'normal')
            vol_map = {'low': 0.25, 'normal': 0.5, 'elevated': 0.75, 'extreme': 1.0}
            features['volatility_regime_score'] = vol_map.get(vol_regime, 0.5)
            
            # Market bias
            market_bias = market_metrics.get('market_bias', 'neutral')
            bias_map = {'bullish': 1, 'neutral': 0, 'bearish': -1}
            features['market_bias_score'] = bias_map.get(market_bias, 0)
            
            return features
            
        except Exception as e:
            logger.error(f"Error building sentiment features: {e}")
            return {}
    
    def _build_regime_features(self, market_metrics: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Build regime classification features"""
        try:
            if not market_metrics:
                return {}
            
            features = {}
            
            # Regime type
            regime = market_metrics.get('regime', 'unknown')
            regime_map = {
                'trend': 1, 'range': 0, 'breakout': 2, 
                'mean_reversion': -1, 'high_volatility': 3, 'low_volatility': -2
            }
            features['regime_score'] = regime_map.get(regime, 0)
            
            # Regime confidence
            confidence = market_metrics.get('regime_confidence', 50)
            features['regime_confidence'] = confidence / 100  # Normalize to 0-1
            
            # Stability indicators
            stability = market_metrics.get('stability_score', 50)
            features['regime_stability'] = stability / 100
            
            # Transition probability
            transition_prob = market_metrics.get('transition_probability', 50)
            features['transition_risk'] = transition_prob / 100
            
            # Acceleration
            acceleration = market_metrics.get('acceleration_index', 0)
            features['regime_acceleration'] = acceleration / 100  # Normalize to -1 to 1
            
            return features
            
        except Exception as e:
            logger.error(f"Error building regime features: {e}")
            return {}
    
    async def build_training_dataset(
        self, 
        symbol: str,
        historical_data: List[Dict[str, Any]],
        target_variable: str = 'price_change',
        prediction_horizon: int = 5
    ) -> FeatureDataset:
        """
        Build training dataset from historical data
        """
        try:
            if len(historical_data) < self.min_samples_for_training:
                logger.warning(f"Insufficient data for training dataset for {symbol}")
                return self._create_empty_dataset(symbol)
            
            # Build features for each time point
            all_features = []
            targets = {target_variable: []}
            
            for i in range(len(historical_data) - prediction_horizon):
                # Get data up to current point
                current_data = historical_data[:i+1]
                
                # Extract price and volume data
                price_data = [
                    {
                        'close': d['close'],
                        'high': d['high'],
                        'low': d['low'],
                        'timestamp': d['timestamp']
                    }
                    for d in current_data
                ]
                
                volume_data = [
                    {
                        'volume': d.get('volume', 0),
                        'timestamp': d['timestamp']
                    }
                    for d in current_data
                ]
                
                # Build features
                features = await self.build_features(symbol, price_data, volume_data)
                all_features.append(features)
                
                # Calculate target
                future_price = historical_data[i + prediction_horizon]['close']
                current_price = historical_data[i]['close']
                target_value = (future_price - current_price) / current_price * 100  # Percentage change
                
                targets[target_variable].append(target_value)
            
            # Create dataset
            dataset = FeatureDataset(
                symbol=symbol,
                features=all_features,
                target_variables=targets,
                metadata={
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'samples': len(all_features),
                    'target_variable': target_variable,
                    'prediction_horizon': prediction_horizon,
                    'feature_count': self._count_total_features(all_features[0]) if all_features else 0
                }
            )
            
            logger.info(f"Built training dataset for {symbol}: {len(all_features)} samples")
            return dataset
            
        except Exception as e:
            logger.error(f"Error building training dataset for {symbol}: {e}")
            return self._create_empty_dataset(symbol)
    
    def _store_features(self, symbol: str, features: MarketFeatures) -> None:
        """Store features in history"""
        if symbol not in self.feature_history:
            self.feature_history[symbol] = []
        
        self.feature_history[symbol].append(features)
        
        # Limit history size
        if len(self.feature_history[symbol]) > self.max_history_size:
            self.feature_history[symbol] = self.feature_history[symbol][-self.max_history_size:]
    
    def _create_default_features(self, symbol: str) -> MarketFeatures:
        """Create default features for error cases"""
        return MarketFeatures(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            price_features={},
            volume_features={},
            volatility_features={},
            momentum_features={},
            technical_features={},
            options_features={},
            sentiment_features={},
            regime_features={}
        )
    
    def _create_empty_dataset(self, symbol: str) -> FeatureDataset:
        """Create empty dataset for error cases"""
        return FeatureDataset(
            symbol=symbol,
            features=[],
            target_variables={},
            metadata={
                'created_at': datetime.now(timezone.utc).isoformat(),
                'samples': 0,
                'error': 'Insufficient data or error in processing'
            }
        )
    
    # Technical indicator calculation methods
    def _calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """Calculate True Range"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[float, float, float]:
        """Calculate MACD"""
        exp1 = prices.ewm(span=self.macd_fast).mean()
        exp2 = prices.ewm(span=self.macd_slow).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=self.macd_signal).mean()
        histogram = macd_line - signal_line
        
        return (macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0,
                signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0,
                histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0)
    
    def _calculate_slope(self, series: pd.Series, window: int) -> float:
        """Calculate linear slope over window"""
        if len(series) < window:
            return 0
        
        y = series.tail(window).values
        x = np.arange(len(y))
        
        # Linear regression
        slope = np.polyfit(x, y, 1)[0]
        return slope
    
    def _calculate_trend_strength(self, prices: pd.Series, window: int) -> float:
        """Calculate trend strength using R-squared of linear fit"""
        if len(prices) < window:
            return 0
        
        y = prices.tail(window).values
        x = np.arange(len(y))
        
        # Linear regression
        coeffs = np.polyfit(x, y, 1)
        y_pred = np.polyval(coeffs, x)
        
        # R-squared
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return r_squared
    
    def _count_total_features(self, features: MarketFeatures) -> int:
        """Count total number of features"""
        return (len(features.price_features) + len(features.volume_features) +
                len(features.volatility_features) + len(features.momentum_features) +
                len(features.technical_features) + len(features.options_features) +
                len(features.sentiment_features) + len(features.regime_features))
    
    # Query methods
    def get_latest_features(self, symbol: str) -> Optional[MarketFeatures]:
        """Get latest features for symbol"""
        if symbol in self.feature_history and self.feature_history[symbol]:
            return self.feature_history[symbol][-1]
        return None
    
    def get_feature_history(self, symbol: str, count: int = 100) -> List[MarketFeatures]:
        """Get feature history for symbol"""
        if symbol in self.feature_history:
            return self.feature_history[symbol][-count:]
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get feature building statistics"""
        total_features = sum(len(history) for history in self.feature_history.values())
        symbols = list(self.feature_history.keys())
        
        return {
            "symbols_tracked": len(symbols),
            "total_feature_records": total_features,
            "features_per_symbol": {symbol: len(history) for symbol, history in self.feature_history.items()},
            "window_configurations": {
                "price_windows": self.price_window_sizes,
                "volume_windows": self.volume_window_sizes,
                "volatility_windows": self.volatility_window_sizes
            }
        }
    
    # Cleanup methods
    def clear_features(self, symbol: Optional[str] = None) -> None:
        """Clear features for symbol or all symbols"""
        if symbol:
            if symbol in self.feature_history:
                del self.feature_history[symbol]
                logger.info(f"Cleared features for {symbol}")
        else:
            self.feature_history.clear()
            logger.info("Cleared all features")
    
    async def _persist_features_to_db(self, symbol: str, features: MarketFeatures) -> None:
        """Persist features to database"""
        try:
            if not self.db_session:
                return
            
            # Extract key features for ML
            pcr = features.options_features.get('pcr', 0)
            gamma_exposure = features.options_features.get('net_gamma', 0)
            oi_velocity = features.options_features.get('oi_change', 0)
            volatility = features.volatility_features.get('volatility_20', 0)
            trend_strength = features.momentum_features.get('trend_strength', 0)
            liquidity_score = features.volume_features.get('volume_trend', 0)
            market_regime = features.regime_features.get('regime_score', 0)
            
            # Create full feature vector
            feature_vector = {
                'price_features': features.price_features,
                'volume_features': features.volume_features,
                'volatility_features': features.volatility_features,
                'momentum_features': features.momentum_features,
                'technical_features': features.technical_features,
                'options_features': features.options_features,
                'sentiment_features': features.sentiment_features,
                'regime_features': features.regime_features
            }
            
            # Create AI feature record
            ai_feature = AIFeature(
                symbol=symbol,
                timestamp=features.timestamp,
                pcr=pcr,
                gamma_exposure=gamma_exposure,
                oi_velocity=oi_velocity,
                volatility=volatility,
                trend_strength=trend_strength,
                liquidity_score=liquidity_score,
                market_regime=str(market_regime),
                feature_vector_json=feature_vector
            )
            
            # Save to database
            self.db_session.add(ai_feature)
            self.db_session.commit()
            
            logger.debug(f"Persisted features for {symbol} to database")
            
        except Exception as e:
            logger.error(f"Error persisting features to database: {e}")
            if self.db_session:
                self.db_session.rollback()
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down FeatureBuilder")
        self.clear_features()
        logger.info("FeatureBuilder shutdown complete")
