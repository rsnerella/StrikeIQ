import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from ...models.market_data import OptionChainSnapshot, MarketSnapshot
import numpy as np
from collections import defaultdict
from app.core.diagnostics import diag
from app.core.ai_health_state import mark_health

logger = logging.getLogger(__name__)

class SmartMoneyEngine:
    """Smart Money Engine for generating directional bias from option chain snapshots"""
    
    def __init__(self, snapshot_count: int = 30):
        self.snapshot_count = snapshot_count
        self._cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._cache_ttl = timedelta(seconds=30)
    
    async def generate_smart_money_signal(
        self, 
        symbol: str, 
        db: Session
    ) -> Dict[str, Any]:
        """Generate smart money signal for a symbol"""
        try:
            # Check cache first
            cache_key = f"smart_money_{symbol}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Returning cached smart money signal for {symbol}")
                return cached_result
            
            # Validate symbol
            if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
                raise ValueError(f"Invalid symbol: {symbol}. Must be NIFTY or BANKNIFTY")
            
            # Get latest snapshots
            snapshots = self._get_latest_snapshots(symbol, db)
            if not snapshots:
                return self._create_closed_market_response(symbol)
            
            # Calculate features
            features = await self._calculate_features(snapshots, db)
            
            # Generate bias and confidence
            bias, confidence, reasoning = self._generate_bias(features)
            
            # Create response
            result = {
                "symbol": symbol.upper(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bias": bias,
                "confidence": confidence,
                "metrics": {
                    "pcr": features["pcr"],
                    "pcr_shift": features["pcr_shift"],
                    "atm_straddle": features["atm_straddle"],
                    "straddle_change_percent": features["straddle_change_percent"],
                    "oi_acceleration": features["oi_acceleration"],
                    "iv_regime": features["iv_regime"]
                },
                "reasoning": reasoning
            }
            
            # Cache result
            self._cache_result(cache_key, result)
            
            # Mark flow engine as healthy
            mark_health("flow")
            
            logger.info(f"Generated smart money signal for {symbol}: {bias} (confidence: {confidence:.1f})")
            return result
            
        except Exception as e:
            logger.error(f"Error generating smart money signal for {symbol}: {e}")
            raise
    
    def _get_latest_snapshots(self, symbol: str, db: Session) -> List[OptionChainSnapshot]:
        """Get latest option chain snapshots for symbol with optimized queries"""
        try:
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
            
            # Batch fetch all snapshots for these timestamps with optimized query
            snapshots = (
                db.query(OptionChainSnapshot)
                .filter(
                    and_(
                        OptionChainSnapshot.symbol == symbol.upper(),
                        OptionChainSnapshot.timestamp.in_(timestamps)
                    )
                )
                .options(
                    # Eager loading optimization if needed
                    # sqlalchemy.orm.joinedload(OptionChainSnapshot.market_snapshot)
                )
                .order_by(desc(OptionChainSnapshot.timestamp))
                .all()
            )
            
            # Apply additional filtering in memory for better performance
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
    
    async def _calculate_features(
        self, 
        snapshots: List[OptionChainSnapshot], 
        db: Session
    ) -> Dict[str, Any]:
        """Calculate all required features from snapshots"""
        
        # Group snapshots by timestamp
        snapshots_by_time = defaultdict(list)
        for snapshot in snapshots:
            snapshots_by_time[snapshot.timestamp].append(snapshot)
        
        sorted_timestamps = sorted(snapshots_by_time.keys(), reverse=True)
        
        if len(sorted_timestamps) < 2:
            # Not enough data for delta calculations
            return self._calculate_basic_features(snapshots_by_time[sorted_timestamps[0]] if sorted_timestamps else [])
        
        # Current snapshot (latest)
        current_data = snapshots_by_time[sorted_timestamps[0]]
        previous_data = snapshots_by_time[sorted_timestamps[1]] if len(sorted_timestamps) > 1 else []
        
        # Calculate basic features
        current_features = self._calculate_basic_features(current_data)
        previous_features = self._calculate_basic_features(previous_data) if previous_data else current_features
        
        # Calculate time-based features
        features = current_features.copy()
        
        # PCR shift (current vs average of last 15 minutes)
        features["pcr_shift"] = self._calculate_pcr_shift(snapshots_by_time, sorted_timestamps)
        
        # Straddle change % (last 5 min)
        features["straddle_change_percent"] = self._calculate_straddle_change(
            current_features["atm_straddle"],
            previous_features["atm_straddle"]
        )
        
        # OI acceleration
        features["oi_acceleration"] = self._calculate_oi_acceleration(current_data, previous_data)
        
        # IV regime
        features["iv_regime"] = self._calculate_iv_regime(snapshots_by_time, sorted_timestamps)
        
        return features
    
    def _calculate_basic_features(self, snapshots: List[OptionChainSnapshot]) -> Dict[str, Any]:
        """Calculate basic features from a single snapshot"""
        if not snapshots:
            return {
                "total_call_oi": 0,
                "total_put_oi": 0,
                "pcr": 0,
                "atm_straddle": 0,
                "spot_price": 0
            }
        
        # Separate calls and puts
        calls = [s for s in snapshots if s.option_type == "CE"]
        puts = [s for s in snapshots if s.option_type == "PE"]
        
        # Total OI
        total_call_oi = sum(s.oi for s in calls)
        total_put_oi = sum(s.oi for s in puts)
        
        # Total Volume
        total_call_volume = sum(s.volume for s in calls)
        total_put_volume = sum(s.volume for s in puts)
        
        # Add diagnostic logging for volume analysis
        diag("AI_TEST", f"Call volume: {total_call_volume}")
        diag("AI_TEST", f"Put volume: {total_put_volume}")
        
        # PCR
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Get spot price from market snapshot or estimate from ATM strike
        spot_price = self._get_spot_price(snapshots)
        
        # ATM strike and straddle
        atm_strike, atm_straddle = self._calculate_atm_straddle(calls, puts, spot_price)
        
        return {
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "pcr": pcr,
            "atm_strike": atm_strike,
            "atm_straddle": atm_straddle,
            "spot_price": spot_price
        }
    
    def _get_spot_price(self, snapshots: List[OptionChainSnapshot]) -> float:
        """Get spot price from snapshots or estimate"""
        # Try to get from market snapshot first
        if snapshots:
            # For now, estimate from ATM strike range
            strikes = [s.strike for s in snapshots]
            if strikes:
                return sum(strikes) / len(strikes)
        return 0
    
    def _calculate_atm_straddle(
        self, 
        calls: List[OptionChainSnapshot], 
        puts: List[OptionChainSnapshot],
        spot_price: float
    ) -> Tuple[float, float]:
        """Calculate ATM strike and straddle price"""
        if not calls or not puts or spot_price == 0:
            return 0, 0
        
        # Find ATM strike (closest to spot price)
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
    
    def _calculate_pcr_shift(
        self, 
        snapshots_by_time: Dict[datetime, List[OptionChainSnapshot]],
        sorted_timestamps: List[datetime]
    ) -> float:
        """Calculate PCR shift vs 15-minute average"""
        if len(sorted_timestamps) < 2:
            return 0
        
        # Current PCR
        current_data = snapshots_by_time[sorted_timestamps[0]]
        current_features = self._calculate_basic_features(current_data)
        current_pcr = current_features["pcr"]
        
        # Calculate average PCR over last 15 minutes (or available data)
        cutoff_time = sorted_timestamps[0] - timedelta(minutes=15)
        recent_timestamps = [t for t in sorted_timestamps if t >= cutoff_time]
        
        if len(recent_timestamps) <= 1:
            return 0
        
        pcr_values = []
        for timestamp in recent_timestamps[1:]:  # Exclude current
            data = snapshots_by_time[timestamp]
            features = self._calculate_basic_features(data)
            pcr_values.append(features["pcr"])
        
        avg_pcr = sum(pcr_values) / len(pcr_values) if pcr_values else current_pcr
        
        return current_pcr - avg_pcr
    
    def _calculate_straddle_change(
        self, 
        current_straddle: float, 
        previous_straddle: float
    ) -> float:
        """Calculate straddle change percentage"""
        if previous_straddle == 0:
            return 0
        
        return ((current_straddle - previous_straddle) / previous_straddle) * 100
    
    def _calculate_oi_acceleration(
        self, 
        current_data: List[OptionChainSnapshot],
        previous_data: List[OptionChainSnapshot]
    ) -> float:
        """Calculate OI acceleration (change in OI delta)"""
        if not current_data or not previous_data:
            return 0
        
        # Current OI delta
        current_oi_delta = self._calculate_oi_delta(current_data)
        previous_oi_delta = self._calculate_oi_delta(previous_data)
        
        return current_oi_delta - previous_oi_delta
    
    def _calculate_oi_delta(self, snapshots: List[OptionChainSnapshot]) -> float:
        """Calculate OI delta (PE OI delta - CE OI delta)"""
        calls = [s for s in snapshots if s.option_type == "CE"]
        puts = [s for s in snapshots if s.option_type == "PE"]
        
        # Use oi_delta field if available, otherwise fall back to oi_change
        call_oi_delta = sum(s.oi_delta or s.oi_change or 0 for s in calls)
        put_oi_delta = sum(s.oi_delta or s.oi_change or 0 for s in puts)
        
        return put_oi_delta - call_oi_delta
    
    def _calculate_iv_regime(
        self, 
        snapshots_by_time: Dict[datetime, List[OptionChainSnapshot]],
        sorted_timestamps: List[datetime]
    ) -> str:
        """Classify IV regime based on percentile"""
        if len(sorted_timestamps) < 5:
            return "NORMAL"
        
        # Calculate average IV for each timestamp
        iv_values = []
        for timestamp in sorted_timestamps[:min(30, len(sorted_timestamps))]:  # Last 30 snapshots
            data = snapshots_by_time[timestamp]
            valid_iv = [s.iv for s in data if s.iv and s.iv > 0]
            if valid_iv:
                iv_values.append(sum(valid_iv) / len(valid_iv))
        
        if len(iv_values) < 5:
            return "NORMAL"
        
        # Classify based on percentiles
        current_iv = iv_values[0]
        iv_sorted = sorted(iv_values)
        
        p33 = np.percentile(iv_sorted, 33)
        p67 = np.percentile(iv_sorted, 67)
        
        if current_iv <= p33:
            return "LOW"
        elif current_iv >= p67:
            return "HIGH"
        else:
            return "NORMAL"
    
    def _generate_bias(self, features: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Generate directional bias and confidence based on features"""
        reasoning = []
        bullish_signals = 0
        bearish_signals = 0
        
        # Put OI increasing significantly
        if features.get("oi_acceleration", 0) > 1000:  # Threshold for significance
            bullish_signals += 1
            reasoning.append("Put OI increasing faster than Call OI")
        elif features.get("oi_acceleration", 0) < -1000:
            bearish_signals += 1
            reasoning.append("Call OI increasing faster than Put OI")
        
        # PCR shift
        pcr_shift = features.get("pcr_shift", 0)
        if pcr_shift > 0.1:  # PCR increasing
            bullish_signals += 1
            reasoning.append("PCR rising above recent average")
        elif pcr_shift < -0.1:  # PCR decreasing
            bearish_signals += 1
            reasoning.append("PCR falling below recent average")
        
        # Straddle change
        straddle_change = features.get("straddle_change_percent", 0)
        if straddle_change > 2:  # Straddle expanding upward
            bullish_signals += 1
            reasoning.append("ATM straddle expanding upward")
        elif straddle_change < -2:  # Straddle expanding downward
            bearish_signals += 1
            reasoning.append("ATM straddle expanding downward")
        
        # PCR level
        pcr = features.get("pcr", 0)
        if pcr > 1.2:  # High PCR (bullish)
            bullish_signals += 1
            reasoning.append("High PCR indicating bullish sentiment")
        elif pcr < 0.8:  # Low PCR (bearish)
            bearish_signals += 1
            reasoning.append("Low PCR indicating bearish sentiment")
        
        # Determine bias
        if bullish_signals > bearish_signals:
            bias = "BULLISH"
        elif bearish_signals > bullish_signals:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
        
        # Calculate confidence (0-100)
        total_signals = bullish_signals + bearish_signals
        signal_strength = abs(bullish_signals - bearish_signals)
        base_confidence = (signal_strength / max(total_signals, 1)) * 50
        
        # Boost confidence based on feature magnitudes
        confidence_boost = 0
        confidence_boost += min(abs(pcr_shift) * 20, 20)  # PCR shift contribution
        confidence_boost += min(abs(straddle_change) * 5, 15)  # Straddle change contribution
        confidence_boost += min(abs(features.get("oi_acceleration", 0)) / 100, 15)  # OI acceleration contribution
        
        confidence = min(base_confidence + confidence_boost, 100)
        
        # Add reasoning for neutral bias
        if bias == "NEUTRAL":
            reasoning.append("Mixed signals with no clear directional bias")
        
        return bias, round(confidence, 1), reasoning
    
    def _create_closed_market_response(self, symbol: str) -> Dict[str, Any]:
        """Create response for closed market"""
        return {
            "symbol": symbol.upper(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bias": "NEUTRAL",
            "confidence": 0.0,
            "metrics": {
                "pcr": 0.0,
                "pcr_shift": 0.0,
                "atm_straddle": 0.0,
                "straddle_change_percent": 0.0,
                "oi_acceleration": 0.0,
                "iv_regime": "NORMAL"
            },
            "reasoning": ["Market closed - insufficient data"]
        }
    
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
        logger.info("Smart money engine cache cleared")
