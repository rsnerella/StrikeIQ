"""
Trade Decision Engine - Generates specific trade suggestions
Lightweight, optimized for Intel i5 CPU, 8GB RAM
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import math

from .risk_engine import RiskEngine
from .ai_db import ai_db

logger = logging.getLogger(__name__)

@dataclass
class TradeSuggestion:
    """Complete trade suggestion"""
    symbol: str
    option_strike: float
    option_type: str  # CE / PE
    entry_price: float
    target_price: float
    stoploss_price: float
    confidence: float  # 0.0 - 1.0
    strategy: str

class TradeDecisionEngine:
    """
    Generates specific trade suggestions based on strategy and market conditions
    Calculates optimal strikes, entry, target, and stoploss levels
    """
    
    def __init__(self):
        # Standard option parameters
        self.contract_multiplier = 75  # NFO options
        self.min_premium = 20.0  # Minimum premium to consider
        self.max_premium = 500.0  # Maximum premium to consider
        
        # Risk management parameters
        self.default_risk_reward = 2.0  # Target:Risk ratio
        self.stoploss_pct = 0.25  # 25% of premium as stoploss
        self.target_pct = 0.50   # 50% of premium as target
        self.risk_engine = RiskEngine()
    
    def generate_trade(self, metrics, strategy_choice) -> Optional[TradeSuggestion]:
        """
        Generate complete trade suggestion
        """
        try:
            if strategy_choice.strategy == "Hold" or strategy_choice.confidence < 0.5:
                return None
            
            symbol = metrics.symbol
            spot = metrics.spot
            
            # Generate trade based on strategy
            suggestion = None
            if strategy_choice.strategy == "Long Call":
                suggestion = self._generate_long_call(symbol, spot, strategy_choice, metrics)
            elif strategy_choice.strategy == "Long Put":
                suggestion = self._generate_long_put(symbol, spot, strategy_choice, metrics)
            elif strategy_choice.strategy == "Bull Call Spread":
                suggestion = self._generate_bull_call_spread(symbol, spot, strategy_choice, metrics)
            elif strategy_choice.strategy == "Bear Put Spread":
                suggestion = self._generate_bear_put_spread(symbol, spot, strategy_choice, metrics)
            elif strategy_choice.strategy == "Iron Condor":
                suggestion = self._generate_iron_condor(symbol, spot, strategy_choice, metrics)
            elif strategy_choice.strategy == "Straddle":
                suggestion = self._generate_straddle(symbol, spot, strategy_choice, metrics)
            elif strategy_choice.strategy == "Strangle":
                suggestion = self._generate_strangle(symbol, spot, strategy_choice, metrics)
            
            # Log successful trade generation
            if suggestion:
                self._log_trade_to_history(suggestion, metrics, strategy_choice)
                
            return suggestion
                
        except Exception as e:
            logger.error(f"Trade generation error: {e}")
            return None

    def _log_trade_to_history(self, suggestion, metrics, strategy_choice):
        """Log trade to ai_trade_history table"""
        try:
            risk_metrics = self.risk_engine.calculate_trade_risk(suggestion)
            
            query = """
            INSERT INTO ai_trade_history (
                symbol, strategy, direction, trade_type, entry_price, 
                target_price, stoploss_price, confidence, trade_reason, 
                strike, lot_size, expected_profit, expected_loss, 
                market_regime, signal_strength
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            direction = "CALL" if suggestion.option_type == "CE" else "PUT"
            trade_type = "BUY" # Default
            if "Iron Condor" in suggestion.strategy:
                trade_type = "SELL"
                
            params = (
                suggestion.symbol,
                suggestion.strategy,
                direction,
                trade_type,
                suggestion.entry_price,
                suggestion.target_price,
                suggestion.stoploss_price,
                suggestion.confidence,
                getattr(strategy_choice, 'reasoning', 'AI Generated'),
                suggestion.option_strike,
                risk_metrics['lot_size'],
                risk_metrics['expected_profit'],
                risk_metrics['expected_loss'],
                getattr(metrics, 'regime', 'UNKNOWN'),
                getattr(metrics, 'signal_strength', 0.0)
            )
            
            ai_db.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Error logging trade to history: {e}")
    
    def _generate_long_call(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Long Call trade"""
        # Select strike - slightly OTM for better risk/reward
        strike = self._select_call_strike(spot, metrics, otm_factor=0.02)
        
        # Estimate premium (simplified)
        premium = self._estimate_call_premium(strike, spot, metrics)
        
        # Calculate entry, target, stoploss
        entry = premium
        stoploss = premium * (1 - self.stoploss_pct)
        target = premium * (1 + self.target_pct)
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=strike,
            option_type="CE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _generate_long_put(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Long Put trade"""
        # Select strike - slightly OTM for better risk/reward
        strike = self._select_put_strike(spot, metrics, otm_factor=0.02)
        
        # Estimate premium (simplified)
        premium = self._estimate_put_premium(strike, spot, metrics)
        
        # Calculate entry, target, stoploss
        entry = premium
        stoploss = premium * (1 - self.stoploss_pct)
        target = premium * (1 + self.target_pct)
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=strike,
            option_type="PE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _generate_bull_call_spread(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Bull Call Spread trade - return the long leg"""
        # Select strikes for spread
        long_strike = self._select_call_strike(spot, metrics, otm_factor=0.01)
        short_strike = self._select_call_strike(spot, metrics, otm_factor=0.04)
        
        # Estimate net premium (debit spread)
        long_premium = self._estimate_call_premium(long_strike, spot, metrics)
        short_premium = self._estimate_call_premium(short_strike, spot, metrics) * 0.7  # OTM discount
        net_premium = max(long_premium - short_premium, self.min_premium * 0.5)
        
        # Calculate levels for spread
        max_profit = (short_strike - long_strike) - net_premium
        max_loss = net_premium
        
        entry = net_premium
        target = net_premium + (max_profit * 0.8)  # Target 80% of max profit
        stoploss = net_premium * 0.5  # Stop at 50% of max loss
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=long_strike,
            option_type="CE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _generate_bear_put_spread(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Bear Put Spread trade - return the long leg"""
        # Select strikes for spread
        long_strike = self._select_put_strike(spot, metrics, otm_factor=0.01)
        short_strike = self._select_put_strike(spot, metrics, otm_factor=0.04)
        
        # Estimate net premium (debit spread)
        long_premium = self._estimate_put_premium(long_strike, spot, metrics)
        short_premium = self._estimate_put_premium(short_strike, spot, metrics) * 0.7  # OTM discount
        net_premium = max(long_premium - short_premium, self.min_premium * 0.5)
        
        # Calculate levels for spread
        max_profit = (long_strike - short_strike) - net_premium
        max_loss = net_premium
        
        entry = net_premium
        target = net_premium + (max_profit * 0.8)  # Target 80% of max profit
        stoploss = net_premium * 0.5  # Stop at 50% of max loss
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=long_strike,
            option_type="PE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _generate_iron_condor(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Iron Condor trade - return the short put leg"""
        # Iron Condor: Sell put spread + sell call spread
        put_short_strike = self._select_put_strike(spot, metrics, otm_factor=0.03)
        put_long_strike = self._select_put_strike(spot, metrics, otm_factor=0.06)
        call_short_strike = self._select_call_strike(spot, metrics, otm_factor=0.03)
        call_long_strike = self._select_call_strike(spot, metrics, otm_factor=0.06)
        
        # Estimate net credit
        put_short_premium = self._estimate_put_premium(put_short_strike, spot, metrics)
        put_long_premium = self._estimate_put_premium(put_long_strike, spot, metrics) * 0.5
        call_short_premium = self._estimate_call_premium(call_short_strike, spot, metrics)
        call_long_premium = self._estimate_call_premium(call_long_strike, spot, metrics) * 0.5
        
        net_credit = (put_short_premium + call_short_premium) - (put_long_premium + call_long_premium)
        net_credit = max(net_credit, self.min_premium * 0.3)
        
        # Iron condor levels
        max_profit = net_credit
        max_loss = ((put_short_strike - put_long_strike) - net_credit) * self.contract_multiplier
        
        entry = net_credit
        target = net_credit * 0.5  # Take profit at 50% of max
        stoploss = net_credit * 2.0  # Stop if credit doubles (loss)
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=put_short_strike,
            option_type="PE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _generate_straddle(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Straddle trade - return the call leg"""
        # Straddle: Buy ATM call + ATM put
        call_strike = self._find_atm_strike(spot)
        put_strike = call_strike  # Same strike for straddle
        
        # Estimate premiums
        call_premium = self._estimate_call_premium(call_strike, spot, metrics)
        put_premium = self._estimate_put_premium(put_strike, spot, metrics)
        total_premium = call_premium + put_premium
        
        # Straddle levels
        entry = call_premium  # Return call leg premium
        target = total_premium * 0.75  # Target 75% of total premium
        stoploss = call_premium * 0.5  # Stop at 50% of call premium
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=call_strike,
            option_type="CE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _generate_strangle(self, symbol: str, spot: float, strategy_choice, metrics) -> TradeSuggestion:
        """Generate Strangle trade - return the call leg"""
        # Strangle: Buy OTM call + OTM put
        call_strike = self._select_call_strike(spot, metrics, otm_factor=0.03)
        put_strike = self._select_put_strike(spot, metrics, otm_factor=0.03)
        
        # Estimate premiums
        call_premium = self._estimate_call_premium(call_strike, spot, metrics)
        put_premium = self._estimate_put_premium(put_strike, spot, metrics)
        total_premium = call_premium + put_premium
        
        # Strangle levels
        entry = call_premium  # Return call leg premium
        target = total_premium * 0.6  # Target 60% of total premium
        stoploss = call_premium * 0.4  # Stop at 40% of call premium
        
        return TradeSuggestion(
            symbol=symbol,
            option_strike=call_strike,
            option_type="CE",
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stoploss_price=round(stoploss, 2),
            confidence=strategy_choice.confidence,
            strategy=strategy_choice.strategy
        )
    
    def _find_atm_strike(self, spot: float) -> float:
        """Find at-the-money strike"""
        # Round to nearest 50 for NIFTY/BANKNIFTY style strikes
        return round(spot / 50) * 50
    
    def _select_call_strike(self, spot: float, metrics, otm_factor: float = 0.02) -> float:
        """Select optimal call strike"""
        base_strike = self._find_atm_strike(spot)
        otm_amount = spot * otm_factor
        selected_strike = base_strike + otm_amount
        
        # Round to nearest 50
        return round(selected_strike / 50) * 50
    
    def _select_put_strike(self, spot: float, metrics, otm_factor: float = 0.02) -> float:
        """Select optimal put strike"""
        base_strike = self._find_atm_strike(spot)
        otm_amount = spot * otm_factor
        selected_strike = base_strike - otm_amount
        
        # Round to nearest 50
        return round(selected_strike / 50) * 50
    
    def _estimate_call_premium(self, strike: float, spot: float, metrics) -> float:
        """Estimate call option premium (simplified)"""
        try:
            # Basic option pricing approximation
            intrinsic = max(0, spot - strike)
            
            # Time value based on expected move and volatility
            expected_move = getattr(metrics, 'expected_move', spot * 0.02)
            volatility_regime = getattr(metrics, 'volatility_regime', 'normal')
            
            # Volatility multiplier
            vol_multiplier = {
                'low': 0.8,
                'normal': 1.0,
                'elevated': 1.3,
                'extreme': 1.6
            }.get(volatility_regime, 1.0)
            
            # Distance from strike affects time value
            distance_pct = abs(strike - spot) / spot
            time_value = expected_move * vol_multiplier * math.exp(-distance_pct * 2)
            
            premium = intrinsic + time_value
            
            # Ensure reasonable bounds
            return max(self.min_premium, min(premium, self.max_premium))
            
        except Exception as e:
            logger.error(f"Call premium estimation error: {e}")
            return self.min_premium * 2
    
    def _estimate_put_premium(self, strike: float, spot: float, metrics) -> float:
        """Estimate put option premium (simplified)"""
        try:
            # Basic option pricing approximation
            intrinsic = max(0, strike - spot)
            
            # Time value based on expected move and volatility
            expected_move = getattr(metrics, 'expected_move', spot * 0.02)
            volatility_regime = getattr(metrics, 'volatility_regime', 'normal')
            
            # Volatility multiplier
            vol_multiplier = {
                'low': 0.8,
                'normal': 1.0,
                'elevated': 1.3,
                'extreme': 1.6
            }.get(volatility_regime, 1.0)
            
            # Distance from strike affects time value
            distance_pct = abs(strike - spot) / spot
            time_value = expected_move * vol_multiplier * math.exp(-distance_pct * 2)
            
            premium = intrinsic + time_value
            
            # Ensure reasonable bounds
            return max(self.min_premium, min(premium, self.max_premium))
            
        except Exception as e:
            logger.error(f"Put premium estimation error: {e}")
            return self.min_premium * 2
