"""
Institutional Flow Engine - Unified Smart Money Analysis
Consolidates smart_money_engine, smart_money_engine_v2, and smart_money_detector
Provides comprehensive institutional flow analysis with statistical stability
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class InstitutionalSignal:
    """Unified institutional flow signal"""
    signal: str  # BULLISH | BEARISH | NEUTRAL
    confidence: float
    direction: str  # UP | DOWN | NONE
    strength: float
    reasoning: str
    metrics: Dict[str, Any]

class InstitutionalFlowEngine:
    """
    Unified Institutional Flow Engine
    
    Combines:
    - Basic smart money detection (from ai/smart_money_engine.py)
    - Advanced database analysis (from services/market_data/smart_money_engine.py)
    - Statistical normalization (from services/market_data/smart_money_engine_v2.py)
    
    Features:
    - Real-time flow detection
    - Historical pattern analysis
    - Statistical confidence scoring
    - Activation thresholds
    - Data quality validation
    """
    
    def __init__(self, snapshot_count: int = 30, min_snapshots: int = 10):
        # Basic detection thresholds (from smart_money_engine.py)
        self.pcr_bullish_threshold = 1.3
        self.pcr_bearish_threshold = 0.7
        self.flow_imbalance_threshold = 0.25
        self.oi_concentration_threshold = 0.3
        self.intent_score_threshold = 70
        
        # Advanced analysis parameters (from smart_money_engine_v2.py)
        self.snapshot_count = snapshot_count
        self.min_snapshots = min_snapshots
        self._cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._cache_ttl = timedelta(seconds=30)
        
        # Activation thresholds
        self.min_oi_change_threshold = 5000
        self.min_volume_ratio = 0.8
        self.max_data_age_minutes = 2
        
        # Production safety features
        self.last_signal_timestamp = 0
        self.cooldown_seconds = 3
        
        # Safe default output
        self.safe_default = {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "direction": "NONE",
            "strength": 0.0,
            "reasoning": "invalid_metrics",
            "metrics": {}
        }
        
        logger.info("InstitutionalFlowEngine initialized - Unified smart money analysis")
    
    async def analyze_institutional_flow(
        self, 
        symbol: str, 
        db: Session,
        live_metrics: Optional[Dict[str, Any]] = None,
        save_prediction: bool = True
    ) -> InstitutionalSignal:
        """
        Unified institutional flow analysis
        
        Combines real-time detection with historical analysis
        """
        try:
            # Check cache first
            cache_key = f"institutional_flow_{symbol}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Returning cached institutional flow signal for {symbol}")
                return InstitutionalSignal(**cached_result)
            
            # Validate symbol
            if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
                raise ValueError(f"Invalid symbol: {symbol}. Must be NIFTY or BANKNIFTY")
            
            # Try advanced database analysis first
            db_result = await self._analyze_from_database(symbol, db, save_prediction)
            if db_result:
                return db_result
            
            # Fallback to real-time metrics analysis
            if live_metrics:
                rt_result = self._analyze_realtime_metrics(live_metrics)
                return rt_result
            
            # No data available
            return self._create_closed_market_signal(symbol)
            
        except Exception as e:
            logger.error(f"Error analyzing institutional flow for {symbol}: {e}")
            return InstitutionalSignal(**self.safe_default)
    
    async def _analyze_from_database(
        self, 
        symbol: str, 
        db: Session,
        save_prediction: bool = True
    ) -> Optional[InstitutionalSignal]:
        """Advanced analysis from database snapshots"""
        try:
            # Get latest snapshots
            snapshots = self._get_latest_snapshots(symbol, db)
            if not snapshots:
                return None
            
            # Apply activation thresholds
            activation_result = self._check_activation_thresholds(snapshots, symbol)
            if activation_result:
                if save_prediction:
                    await self._save_prediction(db, symbol, activation_result)
                return InstitutionalSignal(**activation_result)
            
            # Validate data quality
            validation_result = self._validate_data_quality(snapshots)
            if validation_result:
                if save_prediction:
                    await self._save_prediction(db, symbol, validation_result)
                return InstitutionalSignal(**validation_result)
            
            # Calculate normalized features
            features = await self._calculate_normalized_features(snapshots, db)
            
            # Generate bias and confidence
            bias, confidence, reasoning = self._generate_normalized_bias(features)
            
            # Create unified signal
            result = {
                "signal": bias,
                "confidence": confidence,
                "direction": "UP" if bias == "BULLISH" else "DOWN" if bias == "BEARISH" else "NONE",
                "strength": confidence,
                "reasoning": "; ".join(reasoning) if isinstance(reasoning, list) else reasoning,
                "metrics": {
                    "pcr": features["pcr"],
                    "pcr_shift_z": features.get("pcr_shift_z", 0),
                    "atm_straddle": features["atm_straddle"],
                    "straddle_change_normalized": features.get("straddle_change_normalized", 0),
                    "oi_acceleration_ratio": features.get("oi_acceleration_ratio", 0),
                    "volume_ratio": features.get("volume_ratio", 0),
                    "iv_regime": features["iv_regime"]
                }
            }
            
            # Cache result
            cache_key = f"institutional_flow_{symbol}"
            self._cache_result(cache_key, result)
            
            # Save prediction for tracking
            if save_prediction:
                await self._save_prediction(db, symbol, result, features)
            
            logger.info(f"Generated institutional flow signal for {symbol}: {bias} (confidence: {confidence:.1f})")
            return InstitutionalSignal(**result)
            
        except Exception as e:
            logger.error(f"Database analysis error for {symbol}: {e}")
            return None
    
    def _analyze_realtime_metrics(self, live_metrics: Dict[str, Any]) -> InstitutionalSignal:
        """Real-time analysis from LiveMetrics (original smart_money_engine.py logic)"""
        try:
            # Apply cooldown
            current_time = time.time()
            if current_time - self.last_signal_timestamp < self.cooldown_seconds:
                return InstitutionalSignal(**{
                    "signal": "NEUTRAL",
                    "confidence": 0.0,
                    "direction": "NONE",
                    "strength": 0.0,
                    "reasoning": "signal_cooldown",
                    "metrics": {}
                })
            
            # Extract metrics safely
            pcr = live_metrics.get("pcr") if isinstance(live_metrics, dict) else getattr(live_metrics, 'pcr', 1.0)
            if not pcr or pcr <= 0:
                return InstitutionalSignal(**self.safe_default)
            
            flow_imbalance = live_metrics.get("flow_imbalance") if isinstance(live_metrics, dict) else getattr(live_metrics, 'flow_imbalance', 0)
            flow_direction = live_metrics.get("flow_direction") if isinstance(live_metrics, dict) else getattr(live_metrics, 'flow_direction', 'neutral')
            total_oi = live_metrics.get("total_oi") if isinstance(live_metrics, dict) else getattr(live_metrics, 'total_oi', 0)
            intent_score = live_metrics.get("intent_score") if isinstance(live_metrics, dict) else getattr(live_metrics, 'intent_score', 50)
            net_gamma = live_metrics.get("net_gamma") if isinstance(live_metrics, dict) else getattr(live_metrics, 'net_gamma', 0)
            volatility_regime = live_metrics.get("volatility_regime") if isinstance(live_metrics, dict) else getattr(live_metrics, 'volatility_regime', 'normal')
            
            # Detect patterns
            bullish_signals = self._detect_bullish_positioning(pcr, flow_direction, intent_score, net_gamma, volatility_regime)
            bearish_signals = self._detect_bearish_positioning(pcr, flow_direction, intent_score, net_gamma, volatility_regime)
            
            # Determine final signal
            if bullish_signals['confidence'] > bearish_signals['confidence'] and bullish_signals['confidence'] > 0.5:
                self.last_signal_timestamp = current_time
                logger.info(f"Institutional flow BULLISH detected: {bullish_signals['reason']}")
                return InstitutionalSignal(
                    signal="BULLISH",
                    confidence=bullish_signals['confidence'],
                    direction="UP",
                    strength=bullish_signals['confidence'],
                    reasoning=bullish_signals['reason'],
                    metrics={
                        "pcr": pcr,
                        "flow_imbalance": flow_imbalance,
                        "intent_score": intent_score,
                        "net_gamma": net_gamma,
                        "volatility_regime": volatility_regime
                    }
                )
            elif bearish_signals['confidence'] > bullish_signals['confidence'] and bearish_signals['confidence'] > 0.5:
                self.last_signal_timestamp = current_time
                logger.info(f"Institutional flow BEARISH detected: {bearish_signals['reason']}")
                return InstitutionalSignal(
                    signal="BEARISH",
                    confidence=bearish_signals['confidence'],
                    direction="DOWN",
                    strength=bearish_signals['confidence'],
                    reasoning=bearish_signals['reason'],
                    metrics={
                        "pcr": pcr,
                        "flow_imbalance": flow_imbalance,
                        "intent_score": intent_score,
                        "net_gamma": net_gamma,
                        "volatility_regime": volatility_regime
                    }
                )
            else:
                return InstitutionalSignal(
                    signal="NEUTRAL",
                    confidence=0.0,
                    direction="NONE",
                    strength=0.0,
                    reasoning="no_institutional_bias",
                    metrics={
                        "pcr": pcr,
                        "flow_imbalance": flow_imbalance,
                        "intent_score": intent_score,
                        "net_gamma": net_gamma,
                        "volatility_regime": volatility_regime
                    }
                )
                
        except Exception as e:
            logger.error(f"Real-time institutional flow analysis error: {e}")
            return InstitutionalSignal(**self.safe_default)
    
    def _detect_bullish_positioning(self, pcr: float, flow_direction: str, intent_score: float, net_gamma: float, volatility_regime: str) -> Dict[str, Any]:
        """Detect bullish institutional positioning"""
        try:
            confidence = 0.0
            reasons = []
            
            # PCR for put writing dominance
            if pcr > self.pcr_bullish_threshold:
                confidence += 0.3
                reasons.append("high_pcr_put_writing")
            elif pcr > 1.1:
                confidence += 0.15
                reasons.append("moderate_pcr")
            
            # Flow direction for institutional buying
            if flow_direction == 'call':
                confidence += 0.2
                reasons.append("call_flow_dominance")
            
            # Intent score
            if intent_score > self.intent_score_threshold:
                confidence += 0.25
                reasons.append("high_institutional_intent")
            elif intent_score > 60:
                confidence += 0.1
                reasons.append("elevated_intent")
            
            # Net gamma for dealer positioning
            if net_gamma > 50000:
                confidence += 0.15
                reasons.append("positive_gamma")
            elif net_gamma > 20000:
                confidence += 0.05
                reasons.append("moderate_positive_gamma")
            
            # Volatility regime
            if volatility_regime == 'normal':
                confidence += 0.1
                reasons.append("normal_volatility")
            
            return {
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons) if reasons else "no_bullish_signals"
            }
            
        except Exception as e:
            logger.error(f"Bullish positioning detection error: {e}")
            return {'confidence': 0.0, 'reason': 'detection_error'}
    
    def _detect_bearish_positioning(self, pcr: float, flow_direction: str, intent_score: float, net_gamma: float, volatility_regime: str) -> Dict[str, Any]:
        """Detect bearish institutional positioning"""
        try:
            confidence = 0.0
            reasons = []
            
            # PCR for call writing dominance
            if pcr < self.pcr_bearish_threshold:
                confidence += 0.3
                reasons.append("low_pcr_call_writing")
            elif pcr < 0.9:
                confidence += 0.15
                reasons.append("moderate_pcr")
            
            # Flow direction for institutional selling
            if flow_direction == 'put':
                confidence += 0.2
                reasons.append("put_flow_dominance")
            
            # Intent score
            if intent_score > self.intent_score_threshold:
                confidence += 0.25
                reasons.append("high_institutional_intent")
            elif intent_score > 60:
                confidence += 0.1
                reasons.append("elevated_intent")
            
            # Net gamma for dealer positioning
            if net_gamma < -50000:
                confidence += 0.15
                reasons.append("negative_gamma")
            elif net_gamma < -20000:
                confidence += 0.05
                reasons.append("moderate_negative_gamma")
            
            # Volatility regime
            if volatility_regime == 'normal':
                confidence += 0.1
                reasons.append("normal_volatility")
            
            return {
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons) if reasons else "no_bearish_signals"
            }
            
        except Exception as e:
            logger.error(f"Bearish positioning detection error: {e}")
            return {'confidence': 0.0, 'reason': 'detection_error'}
    
    def _get_latest_snapshots(self, symbol: str, db: Session) -> List:
        """Get latest option chain snapshots for symbol"""
        try:
            from ...models.market_data import OptionChainSnapshot
            
            # Use indexed query to get latest N timestamps efficiently
            latest_timestamps = (
                db.query(OptionChainSnapshot.timestamp)
                .filter(OptionChainSnapshot.symbol == symbol.upper())
                .distinct()
                .order_by(desc(OptionChainSnapshot.timestamp))
                .limit(self.snapshot_count)
                .all()
            )
            
            if not latest_timestamps:
                return []
            
            timestamps = [t[0] for t in latest_timestamps]
            
            # Batch fetch all snapshots for these timestamps
            snapshots = (
                db.query(OptionChainSnapshot)
                .filter(
                    and_(
                        OptionChainSnapshot.symbol == symbol.upper(),
                        OptionChainSnapshot.timestamp.in_(timestamps)
                    )
                )
                .order_by(desc(OptionChainSnapshot.timestamp))
                .all()
            )
            
            # Apply additional filtering in memory
            filtered_snapshots = []
            seen_strikes = set()
            
            for snapshot in snapshots:
                strike_key = (snapshot.timestamp, snapshot.strike, snapshot.option_type)
                if strike_key not in seen_strikes:
                    seen_strikes.add(strike_key)
                    filtered_snapshots.append(snapshot)
            
            return filtered_snapshots
            
        except Exception as e:
            logger.error(f"Error fetching snapshots for {symbol}: {e}")
            return []
    
    def _check_activation_thresholds(self, snapshots: List, symbol: str) -> Optional[Dict[str, Any]]:
        """Check minimum activation thresholds"""
        if not snapshots:
            return self._create_insufficient_data_response(symbol, "No data available")
        
        # Check minimum snapshot count
        unique_timestamps = len(set(s.timestamp for s in snapshots))
        if unique_timestamps < self.min_snapshots:
            return self._create_insufficient_data_response(
                symbol, 
                f"Insufficient snapshots: {unique_timestamps} < {self.min_snapshots}"
            )
        
        # Check data freshness
        latest_timestamp = max(s.timestamp for s in snapshots)
        data_age = datetime.now(timezone.utc) - latest_timestamp
        if data_age > timedelta(minutes=self.max_data_age_minutes):
            return self._create_insufficient_data_response(
                symbol,
                f"Data too old: {data_age.total_seconds()/60:.1f} minutes"
            )
        
        # Calculate total OI change
        total_oi_change = sum(abs(s.oi_change or 0) for s in snapshots)
        if total_oi_change < self.min_oi_change_threshold:
            return self._create_insufficient_data_response(
                symbol,
                f"Insufficient OI change: {total_oi_change} < {self.min_oi_change_threshold}"
            )
        
        # Calculate volume ratio
        current_volume = sum(s.volume or 0 for s in snapshots if s.timestamp == latest_timestamp)
        avg_volume_15min = self._calculate_average_volume(snapshots, minutes=15)
        volume_ratio = current_volume / avg_volume_15min if avg_volume_15min > 0 else 0
        
        if volume_ratio < self.min_volume_ratio:
            return self._create_insufficient_data_response(
                symbol,
                f"Low volume ratio: {volume_ratio:.2f} < {self.min_volume_ratio}"
            )
        
        return None
    
    def _validate_data_quality(self, snapshots: List) -> Optional[Dict[str, Any]]:
        """Validate data quality before processing"""
        for snapshot in snapshots:
            if snapshot.oi is None or snapshot.oi < 0:
                return self._create_invalid_data_response("Invalid OI value detected")
            
            if snapshot.ltp is None or snapshot.ltp <= 0:
                return self._create_invalid_data_response("Invalid LTP value detected")
            
            if snapshot.strike is None or snapshot.strike <= 0:
                return self._create_invalid_data_response("Invalid strike value detected")
        
        # Check timestamp ordering
        timestamps = [s.timestamp for s in snapshots]
        if timestamps != sorted(timestamps, reverse=True):
            return self._create_invalid_data_response("Timestamp ordering inconsistency")
        
        return None
    
    async def _calculate_normalized_features(self, snapshots: List, db: Session) -> Dict[str, Any]:
        """Calculate normalized features from snapshots"""
        # Group snapshots by timestamp
        snapshots_by_time = defaultdict(list)
        for snapshot in snapshots:
            snapshots_by_time[snapshot.timestamp].append(snapshot)
        
        sorted_timestamps = sorted(snapshots_by_time.keys(), reverse=True)
        
        if len(sorted_timestamps) < 2:
            return self._calculate_basic_normalized_features(
                snapshots_by_time[sorted_timestamps[0]] if sorted_timestamps else []
            )
        
        # Current and previous data
        current_data = snapshots_by_time[sorted_timestamps[0]]
        previous_data = snapshots_by_time[sorted_timestamps[1]] if len(sorted_timestamps) > 1 else []
        
        # Calculate basic features
        current_features = self._calculate_basic_normalized_features(current_data)
        previous_features = self._calculate_basic_normalized_features(previous_data) if previous_data else current_features
        
        # Calculate normalized features
        features = current_features.copy()
        
        # PCR Z-score
        features["pcr_shift_z"] = self._calculate_pcr_zscore(snapshots_by_time, sorted_timestamps)
        
        # Normalized straddle change
        features["straddle_change_normalized"] = self._normalize_straddle_change(
            current_features["atm_straddle"],
            previous_features["atm_straddle"]
        )
        
        # Normalized OI acceleration
        features["oi_acceleration_ratio"] = self._normalize_oi_acceleration(
            current_data, previous_data, current_features["total_oi"]
        )
        
        # Volume ratio
        current_volume = sum(s.volume or 0 for s in current_data)
        avg_volume_15min = self._calculate_average_volume(snapshots, minutes=15)
        features["volume_ratio"] = current_volume / avg_volume_15min if avg_volume_15min > 0 else 0
        
        # IV regime
        features["iv_regime"] = self._calculate_iv_regime_robust(snapshots_by_time, sorted_timestamps)
        
        return features
    
    def _calculate_basic_normalized_features(self, snapshots: List) -> Dict[str, Any]:
        """Calculate basic features from snapshots"""
        if not snapshots:
            return {
                "total_call_oi": 0,
                "total_put_oi": 0,
                "pcr": 0,
                "atm_straddle": 0,
                "spot_price": 0,
                "total_oi": 0
            }
        
        # Separate calls and puts
        calls = [s for s in snapshots if s.option_type == "CE"]
        puts = [s for s in snapshots if s.option_type == "PE"]
        
        # Total OI
        total_call_oi = sum(s.oi for s in calls)
        total_put_oi = sum(s.oi for s in puts)
        total_oi = total_call_oi + total_put_oi
        
        # PCR
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Get spot price
        spot_price = self._get_spot_price(snapshots)
        
        # ATM strike and straddle
        atm_strike, atm_straddle = self._calculate_atm_straddle(calls, puts, spot_price)
        
        return {
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "total_oi": total_oi,
            "pcr": pcr,
            "atm_strike": atm_strike,
            "atm_straddle": atm_straddle,
            "spot_price": spot_price
        }
    
    def _get_spot_price(self, snapshots: List) -> float:
        """Get spot price from snapshots or estimate"""
        strikes = [s.strike for s in snapshots if s.strike]
        if strikes:
            return sum(strikes) / len(strikes)
        return 0
    
    def _calculate_atm_straddle(self, calls: List, puts: List, spot_price: float) -> Tuple[float, float]:
        """Calculate ATM strike and straddle price"""
        if not calls or not puts or spot_price == 0:
            return 0, 0
        
        # Find ATM strike
        all_strikes = set(s.strike for s in calls) | set(s.strike for s in puts)
        if not all_strikes:
            return 0, 0
        
        atm_strike = min(all_strikes, key=lambda x: abs(x - spot_price))
        
        # Find corresponding CE and PE at ATM strike
        atm_ce = next((s for s in calls if s.strike == atm_strike), None)
        atm_pe = next((s for s in puts if s.strike == atm_strike), None)
        
        # Calculate straddle price
        straddle_price = 0
        if atm_ce and atm_pe:
            straddle_price = atm_ce.ltp + atm_pe.ltp
        
        return atm_strike, straddle_price
    
    def _calculate_pcr_zscore(self, snapshots_by_time: Dict, sorted_timestamps: List) -> float:
        """Calculate PCR z-score over last N snapshots"""
        if len(sorted_timestamps) < 5:
            return 0.0
        
        # Calculate PCR for each timestamp
        pcr_values = []
        for timestamp in sorted_timestamps[:self.snapshot_count]:
            data = snapshots_by_time[timestamp]
            features = self._calculate_basic_normalized_features(data)
            pcr_values.append(features["pcr"])
        
        if len(pcr_values) < 3:
            return 0.0
        
        # Calculate z-score
        current_pcr = pcr_values[0]
        mean_pcr = np.mean(pcr_values[1:])
        std_pcr = np.std(pcr_values[1:])
        
        if std_pcr == 0:
            return 0.0
        
        return (current_pcr - mean_pcr) / std_pcr
    
    def _normalize_straddle_change(self, current_straddle: float, previous_straddle: float) -> float:
        """Normalize straddle change to 0-1 range"""
        if previous_straddle == 0:
            return 0.0
        
        pct_change = abs((current_straddle - previous_straddle) / previous_straddle)
        return min(pct_change / 0.5, 1.0)
    
    def _normalize_oi_acceleration(self, current_data: List, previous_data: List, total_oi: float) -> float:
        """Normalize OI acceleration by total OI"""
        if total_oi == 0:
            return 0.0
        
        current_oi_delta = self._calculate_oi_delta(current_data)
        previous_oi_delta = self._calculate_oi_delta(previous_data)
        
        acceleration = current_oi_delta - previous_oi_delta
        return acceleration / total_oi if total_oi > 0 else 0.0
    
    def _calculate_oi_delta(self, snapshots: List) -> float:
        """Calculate OI delta (PE OI delta - CE OI delta)"""
        calls = [s for s in snapshots if s.option_type == "CE"]
        puts = [s for s in snapshots if s.option_type == "PE"]
        
        call_oi_delta = sum(s.oi_delta or s.oi_change or 0 for s in calls)
        put_oi_delta = sum(s.oi_delta or s.oi_change or 0 for s in puts)
        
        return put_oi_delta - call_oi_delta
    
    def _calculate_iv_regime_robust(self, snapshots_by_time: Dict, sorted_timestamps: List) -> str:
        """Classify IV regime using historical data"""
        min_historical_snapshots = 75
        
        if len(sorted_timestamps) < min_historical_snapshots:
            return "NORMAL"
        
        # Calculate average IV for each timestamp
        iv_values = []
        for timestamp in sorted_timestamps[:min_historical_snapshots]:
            data = snapshots_by_time[timestamp]
            valid_iv = [s.iv for s in data if s.iv and s.iv > 0]
            if valid_iv:
                iv_values.append(sum(valid_iv) / len(valid_iv))
        
        if len(iv_values) < 20:
            return "NORMAL"
        
        # Classify based on percentiles
        current_iv = iv_values[0]
        iv_sorted = sorted(iv_values)
        
        p30 = np.percentile(iv_sorted, 30)
        p70 = np.percentile(iv_sorted, 70)
        
        if current_iv <= p30:
            return "LOW"
        elif current_iv >= p70:
            return "HIGH"
        else:
            return "NORMAL"
    
    def _calculate_average_volume(self, snapshots: List, minutes: int) -> float:
        """Calculate average volume over specified minutes"""
        if not snapshots:
            return 0
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_snapshots = [s for s in snapshots if s.timestamp >= cutoff_time]
        
        if not recent_snapshots:
            return 0
        
        volume_by_time = defaultdict(int)
        for s in recent_snapshots:
            volume_by_time[s.timestamp] += s.volume or 0
        
        return sum(volume_by_time.values()) / len(volume_by_time) if volume_by_time else 0
    
    def _generate_normalized_bias(self, features: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Generate bias using normalized features"""
        reasoning = []
        
        # Extract normalized features
        pcr_z = features.get("pcr_shift_z", 0)
        straddle_norm = features.get("straddle_change_normalized", 0)
        oi_accel_ratio = features.get("oi_acceleration_ratio", 0)
        volume_ratio = features.get("volume_ratio", 0)
        pcr = features.get("pcr", 0)
        
        # Calculate weighted sum for bias
        bullish_weight = 0
        bearish_weight = 0
        
        # PCR Z-score contribution
        if pcr_z > 0.5:
            bullish_weight += pcr_z
            reasoning.append(f"PCR Z-score bullish: {pcr_z:.2f}")
        elif pcr_z < -0.5:
            bearish_weight += abs(pcr_z)
            reasoning.append(f"PCR Z-score bearish: {pcr_z:.2f}")
        
        # OI acceleration contribution
        if oi_accel_ratio > 0.001:
            bullish_weight += oi_accel_ratio * 100
            reasoning.append(f"Positive OI acceleration: {oi_accel_ratio:.4f}")
        elif oi_accel_ratio < -0.001:
            bearish_weight += abs(oi_accel_ratio) * 100
            reasoning.append(f"Negative OI acceleration: {oi_accel_ratio:.4f}")
        
        # Straddle change contribution
        if straddle_norm > 0.3:
            if features.get("straddle_change_percent", 0) > 0:
                bullish_weight += straddle_norm * 2
                reasoning.append(f"Upward straddle expansion: {straddle_norm:.2f}")
            else:
                bearish_weight += straddle_norm * 2
                reasoning.append(f"Downward straddle expansion: {straddle_norm:.2f}")
        
        # Volume ratio contribution
        if volume_ratio > 1.2:
            bullish_weight += (volume_ratio - 1) * 2
            reasoning.append(f"High volume ratio: {volume_ratio:.2f}")
        
        # PCR level contribution
        if pcr > 1.3:
            bullish_weight += 1
            reasoning.append(f"High PCR level: {pcr:.2f}")
        elif pcr < 0.7:
            bearish_weight += 1
            reasoning.append(f"Low PCR level: {pcr:.2f}")
        
        # Determine bias
        weight_diff = bullish_weight - bearish_weight
        if weight_diff > 0.5:
            bias = "BULLISH"
        elif weight_diff < -0.5:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
        
        # Calculate confidence using sigmoid
        weighted_sum = weight_diff
        confidence = self._sigmoid_confidence(weighted_sum) * 100
        
        if bias == "NEUTRAL":
            reasoning.append("Conflicting signals - neutral bias")
        
        return bias, round(confidence, 1), reasoning
    
    def _sigmoid_confidence(self, weighted_sum: float) -> float:
        """Calculate confidence using sigmoid function"""
        scaled_input = weighted_sum * 2
        sigmoid_value = 1 / (1 + np.exp(-scaled_input))
        return max(0, min(1, sigmoid_value))
    
    def _create_insufficient_data_response(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Create response for insufficient data"""
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "direction": "NONE",
            "strength": 0.0,
            "reasoning": f"Insufficient data for directional signal: {reason}",
            "metrics": {
                "pcr": 0.0,
                "pcr_shift_z": 0.0,
                "atm_straddle": 0.0,
                "straddle_change_normalized": 0.0,
                "oi_acceleration_ratio": 0.0,
                "volume_ratio": 0.0,
                "iv_regime": "NORMAL"
            }
        }
    
    def _create_invalid_data_response(self, reason: str) -> Dict[str, Any]:
        """Create response for invalid data"""
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "direction": "NONE",
            "strength": 0.0,
            "reasoning": f"Data validation failed: {reason}",
            "metrics": {
                "pcr": 0.0,
                "pcr_shift_z": 0.0,
                "atm_straddle": 0.0,
                "straddle_change_normalized": 0.0,
                "oi_acceleration_ratio": 0.0,
                "volume_ratio": 0.0,
                "iv_regime": "NORMAL"
            }
        }
    
    def _create_closed_market_signal(self, symbol: str) -> InstitutionalSignal:
        """Create signal for closed market"""
        return InstitutionalSignal(
            signal="NEUTRAL",
            confidence=0.0,
            direction="NONE",
            strength=0.0,
            reasoning="Market closed - insufficient data",
            metrics={}
        )
    
    async def _save_prediction(self, db: Session, symbol: str, result: Dict[str, Any], features: Optional[Dict[str, Any]] = None):
        """Save prediction for performance tracking"""
        try:
            from ...models.market_data import SmartMoneyPrediction
            
            prediction = SmartMoneyPrediction(
                symbol=symbol.upper(),
                bias=result["signal"],
                confidence=result["confidence"],
                pcr=result["metrics"]["pcr"],
                pcr_shift_z=result["metrics"].get("pcr_shift_z", 0),
                atm_straddle=result["metrics"]["atm_straddle"],
                straddle_change_normalized=result["metrics"].get("straddle_change_normalized", 0),
                oi_acceleration_ratio=result["metrics"].get("oi_acceleration_ratio", 0),
                iv_regime=result["metrics"]["iv_regime"],
                expiry_date=features.get("expiry_date", "") if features else ""
            )
            
            db.add(prediction)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
            db.rollback()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if valid"""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if datetime.now(timezone.utc) - timestamp < self._cache_ttl:
                return result
            else:
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache result with timestamp"""
        self._cache[cache_key] = (result, datetime.now(timezone.utc))
    
    def clear_cache(self):
        """Clear all cached results"""
        self._cache.clear()
        logger.info("Institutional flow engine cache cleared")
