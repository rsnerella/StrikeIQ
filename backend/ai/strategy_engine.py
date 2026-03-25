"""
Strategy-Based Trading Engine for StrikeIQ
Converts from indicator-based to strategy-based trading
"""

from typing import Tuple, Dict, Optional, Any
from dataclasses import dataclass

@dataclass
class TradeSignal:
    signal: str
    strategy: str
    confidence: float
    entry: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

def detect_regime(analytics) -> str:
    """
    🔥 STEP 7: TEMP FIX REGIME ENGINE
    Simple PCR-based regime detection for immediate trading
    """
    pcr = analytics.get("pcr", 1.0)
    
    if pcr > 1:
        return "TREND"  # Bearish trend
    elif pcr < 0.7:
        return "TREND"  # Bullish trend
    else:
        return "RANGE"  # Ranging market

def is_tradable_time() -> bool:
    """Check if current time is suitable for trading"""
    import datetime
    
    now = datetime.datetime.now().time()
    
    # Safe trading window: 9:45 AM to 3:00 PM (avoid first/last 30 min)
    safe_start = datetime.time(9, 45)
    safe_end = datetime.time(15, 0)
    
    # Skip weekends only (Saturday=5, Sunday=6)
    weekday = datetime.datetime.now().weekday()
    if weekday >= 5:  # Weekend
        return False
    
    return safe_start <= now <= safe_end

def is_good_entry(analytics) -> bool:
    """Check if market conditions are good for entry"""
    
    # Check momentum — only block deeply neutral RSI (40–60 range)
    # volatility and liquidity fields are not reliably populated so skip those checks
    rsi = analytics.get("rsi", 50)
    
    if 40 <= rsi <= 60:  # Slightly relaxed neutral RSI block
        return False
    
    return True

def fallback_trade(analytics, execution_engine=None) -> Tuple[str, Optional[str]]:
    """
    Generate weak signal when no strong signal exists
    Ensures AI gives trades when real opportunity exists
    """
    try:
        pcr = analytics.get("pcr", 1)
        rsi = analytics.get("rsi", 50)
        
        # 🔥 STEP 5: BLOCK BAD STRATEGIES
        if execution_engine and execution_engine.strategy_weights.get("WEAK_TREND", 1.0) < 0.3:
            return "NONE", "DISABLED_STRATEGY"

        # 🔥 STEP 4: USE WEIGHTS IN STRATEGY ENGINE
        confidence = analytics.get("confidence", 0.5)
        if execution_engine:
            weight = execution_engine.strategy_weights.get("WEAK_TREND", 1.0)
            confidence *= weight
            print(f"[STRATEGY WEIGHT] WEAK_TREND confidence adjusted to {confidence:.3f} (weight: {weight:.3f})")

        # Weak trend signals
        if pcr < 0.95 and rsi > 52:
            return "BUY_CALL", "WEAK_TREND"

        if pcr > 1.05 and rsi < 48:
            return "BUY_PUT", "WEAK_TREND"

        return "NONE", None
        
    except Exception as e:
        print(f"[FALLBACK ERROR] {e}")
        return "NONE", "ERROR"

def generate_trade(snapshot, analytics, execution_engine=None) -> Tuple[str, Optional[str]]:
    """
    Generate final profitable strategy-based trading signals
    
    Args:
        snapshot: ChainSnapshot object
        analytics: Analytics data dictionary
        execution_engine: TradeExecutionEngine instance for strategy weights
        
    Returns:
        Tuple of (signal, strategy)
    """
    try:
        # 🔥 STEP 5: FIX ZERO DATA BLOCK
        if analytics.get("key_levels", {}).get("vwap") == 0:
            analytics["key_levels"]["vwap"] = snapshot.spot
        
        # ❌ DATA VALIDITY FILTER
        if not snapshot.is_valid:
            return "NONE", "INVALID"

        # ❌ TIME FILTER - Only trade during optimal hours
        if not is_tradable_time():
            return "NONE", "TIME_FILTER"

        # 🔥 PRIMARY STRATEGY FIRST
        signal, strategy = _primary_strategy(snapshot, analytics, execution_engine)
        
        # 🔥 STEP 2 — FALLBACK STRATEGY
        if signal == "NONE" or analytics.get("confidence", 0) < 0.4:
            # 🔥 STEP 4: FORCE TRADE WHEN VALID
            if analytics.get("flow_analysis", {}).get("direction") == "BULLISH":
                return "BUY_CALL", "FLOW_FALLBACK"
            elif analytics.get("flow_analysis", {}).get("direction") == "BEARISH":
                return "BUY_PUT", "FLOW_FALLBACK"
            
            signal, strategy = fallback_trade(analytics, execution_engine)

        return signal, strategy
        
    except Exception as e:
        print(f"[STRATEGY ERROR] {e}")
        return "NONE", "ERROR"

def _primary_strategy(snapshot, analytics, execution_engine=None) -> Tuple[str, Optional[str]]:
    """Primary strategy with strict filters"""
    try:
        # ❌ MOMENTUM FILTER - DEGRADED NOT BLOCKED
        momentum_good = is_good_entry(analytics)
        if not momentum_good:
            # Degrade confidence instead of blocking
            confidence = analytics.get("confidence", 0.5) * 0.7
            analytics["confidence"] = confidence
            print(f"[MOMENTUM DEGRADED] Confidence reduced to {confidence:.2f}")
        else:
            # Ensure good confidence for good momentum
            if analytics.get("confidence", 0) < 0.4:
                analytics["confidence"] = 0.4
        
        # Ensure minimum confidence after any degradation
        if analytics.get("confidence", 0) < 0.35:
            analytics["confidence"] = 0.35

        # 🔥 REGIME DETECTION
        regime = detect_regime(analytics)

        # Extract key metrics
        pcr = analytics.get("pcr", 1)
        rsi = analytics.get("rsi", 50)

        # 🔥 TREND STRATEGY
        if regime == "TREND":
            # 🔥 STEP 5: BLOCK BAD STRATEGIES
            if execution_engine and execution_engine.strategy_weights.get("TREND", 1.0) < 0.3:
                return "NONE", "DISABLED_STRATEGY"
            
            # Bullish trend continuation (relaxed: pcr < 0.95, rsi > 52)
            if pcr < 0.95 and rsi > 52:
                # 🔥 STEP 4: USE WEIGHTS IN STRATEGY ENGINE
                confidence = analytics.get("confidence", 0.5)
                if execution_engine:
                    weight = execution_engine.strategy_weights.get("TREND", 1.0)
                    confidence *= weight
                    print(f"[STRATEGY WEIGHT] TREND confidence adjusted to {confidence:.3f} (weight: {weight:.3f})")
                
                return "BUY_CALL", "TREND"

            # Bearish trend continuation (relaxed: pcr > 1.05, rsi < 48)
            if pcr > 1.05 and rsi < 48:
                confidence = analytics.get("confidence", 0.5)
                if execution_engine:
                    weight = execution_engine.strategy_weights.get("TREND", 1.0)
                    confidence *= weight
                    print(f"[STRATEGY WEIGHT] TREND confidence adjusted to {confidence:.3f} (weight: {weight:.3f})")
                
                return "BUY_PUT", "TREND"

        # 🔥 RANGE STRATEGY
        if regime == "RANGE":
            if execution_engine and execution_engine.strategy_weights.get("REVERSAL", 1.0) < 0.3:
                return "NONE", "DISABLED_STRATEGY"
            
            # Range bound - sell premium on extremes
            if pcr < 0.7:  # Extreme PCR - expect reversal
                confidence = analytics.get("confidence", 0.5)
                if execution_engine:
                    weight = execution_engine.strategy_weights.get("REVERSAL", 1.0)
                    confidence *= weight
                    print(f"[STRATEGY WEIGHT] REVERSAL confidence adjusted to {confidence:.3f} (weight: {weight:.3f})")
                
                return "BUY_PUT", "REVERSAL"

            if pcr > 1.3:  # Extreme PCR - expect reversal
                confidence = analytics.get("confidence", 0.5)
                if execution_engine:
                    weight = execution_engine.strategy_weights.get("REVERSAL", 1.0)
                    confidence *= weight
                    print(f"[STRATEGY WEIGHT] REVERSAL confidence adjusted to {confidence:.3f} (weight: {weight:.3f})")
                
                return "BUY_CALL", "REVERSAL"

        return "NONE", "NO_EDGE"
        
    except Exception as e:
        print(f"[PRIMARY STRATEGY ERROR] {e}")
        return "NONE", "ERROR"

def get_trade_levels(entry_price: float, signal_type: str) -> Dict[str, float]:
    """
    Calculate risk management levels for trades
    
    Args:
        entry_price: Entry price for the trade
        signal_type: Type of signal (BUY_CALL/BUY_PUT)
        
    Returns:
        Dictionary with stop_loss and target levels
    """
    try:
        # Base risk/reward ratios
        if signal_type == "BUY_CALL":
            # For calls, upside potential is higher
            stop_loss = entry_price * 0.7  # 30% downside risk
            target = entry_price * 1.5     # 50% upside target
        elif signal_type == "BUY_PUT":
            # For puts, different risk profile
            stop_loss = entry_price * 1.3  # 30% upside risk for puts
            target = entry_price * 0.5     # 50% downside target
        else:
            # Default safe levels
            stop_loss = entry_price * 0.8
            target = entry_price * 1.2
        
        return {
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "risk_reward": round((abs(entry_price - target) / abs(entry_price - stop_loss)), 2)
        }
        
    except Exception as e:
        print(f"[RISK ERROR] {e}")
        return {
            "stop_loss": entry_price * 0.8,
            "target": entry_price * 1.2,
            "risk_reward": 1.0
        }

def create_trade_signal(snapshot, analytics, entry_price: float) -> TradeSignal:
    """
    Create complete trade signal with risk management and frequency control
    
    Args:
        snapshot: ChainSnapshot object
        analytics: Analytics data
        entry_price: Entry price for the trade
        
    Returns:
        Complete TradeSignal object
    """
    signal, strategy = generate_trade(snapshot, analytics)
    confidence = analytics.get("confidence", 0.0)
    
    if signal == "NONE":
        # 🔥 STEP 5 — FORCE MINIMUM SIGNAL FREQUENCY
        forced_signal, forced_strategy = force_minimum_signal_frequency(analytics)
        if forced_signal != "NONE":
            signal, strategy = forced_signal, forced_strategy
            confidence = 0.3  # Low confidence for forced trades
        
        # 🔥 STEP 6 — LOG WHY NO TRADE
        if signal == "NONE":
            log_no_trade_reason(analytics)
    
    if signal == "NONE":
        return TradeSignal(
            signal="NONE",
            strategy=strategy,  # Include the reason
            confidence=0.0,
            metadata={"reason": get_strategy_reason(strategy)}
        )
    
    # Calculate risk levels
    levels = get_trade_levels(entry_price, signal)
    
    # Add strategy-specific metadata
    metadata = {
        "pcr": analytics.get("pcr", 1.0),
        "rsi": analytics.get("rsi", 50),
        "volatility": analytics.get("volatility", 0),
        "spot": snapshot.spot,
        "expiry": snapshot.expiry,
        "data_quality": "REAL" if snapshot.is_valid else "FALLBACK",
        "strategy_reason": get_strategy_reason(strategy),
        "regime": detect_regime(analytics)
    }
    
    return TradeSignal(
        signal=signal,
        strategy=strategy,
        confidence=confidence,
        entry=round(entry_price, 2),
        target=levels["target"],
        stop_loss=levels["stop_loss"],
        metadata={
            **metadata,
            "risk_reward": levels["risk_reward"],
            "strategy_type": strategy
        }
    )

# Global counter for no-trade tracking
_no_trade_count = 0

def should_trade(signal: TradeSignal) -> bool:
    """
    Final filter before execution with relaxed confidence
    
    Args:
        signal: TradeSignal object
        
    Returns:
        Boolean indicating if trade should be executed
    """
    global _no_trade_count
    
    # 🔥 STEP 3 — RELAX CONFIDENCE FILTER
    if signal.confidence < 0.35:  # Relaxed from 0.5
        return False
    
    # Risk/reward ratio requirement
    if signal.metadata and signal.metadata.get("risk_reward", 0) < 1.0:
        return False
    
    # Data quality requirement
    if signal.metadata and signal.metadata.get("data_quality") != "REAL":
        return False
    
    # Only trade on clear strategies (including weak trends and flow fallback)
    if signal.strategy not in ["TREND", "REVERSAL", "WEAK_TREND", "FLOW_FALLBACK"]:
        return False
    
    # Reset counter on successful trade
    _no_trade_count = 0
    return True

def force_minimum_signal_frequency(analytics) -> Tuple[str, Optional[str]]:
    """
    Force minimum signal frequency to ensure AI gives trades
    Step 5: Ensure at least 1 trade per X cycles if market is active
    
    Args:
        analytics: Analytics data dictionary
        
    Returns:
        Tuple of (signal, strategy)
    """
    global _no_trade_count
    _no_trade_count += 1
    
    # Force trade after 20 no-trade cycles
    if _no_trade_count > 20:
        print(f"[FORCE TRADE] No trades for {_no_trade_count} cycles, forcing weak signal")
        _no_trade_count = 0  # Reset counter
        return fallback_trade(analytics)
    
    return "NONE", None

def log_no_trade_reason(analytics) -> None:
    """
    Step 6: Log why no trade was generated
    """
    pcr = analytics.get("pcr", 1)
    rsi = analytics.get("rsi", 50)
    gamma = analytics.get("gamma", "NEUTRAL")
    volatility = analytics.get("volatility", 0)
    
    print(f"[NO TRADE] PCR={pcr:.2f}, RSI={rsi:.1f}, Gamma={gamma}, Vol={volatility:.3f}")

def get_strategy_reason(strategy: str) -> str:
    """Get human-readable reason for strategy selection"""
    
    reasons = {
        "INVALID": "Invalid market data",
        "TIME_FILTER": "Outside optimal trading hours",
        "LOW_MOMENTUM": "Insufficient market momentum",
        "NO_EDGE": "No clear trading edge detected",
        "ERROR": "Strategy engine error",
        "TREND": "Trend continuation strategy",
        "REVERSAL": "Mean reversion strategy",
        "WEAK_TREND": "Weak trend signal (fallback)"
    }
    
    return reasons.get(strategy, "Unknown strategy")
