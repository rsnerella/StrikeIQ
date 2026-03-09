"""
Risk Engine - Validates trade suggestions against risk rules
Lightweight, optimized for Intel i5 CPU, 8GB RAM
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class RiskAssessment:
    """Risk assessment result"""
    approved: bool
    reason: str
    risk_score: float  # 0.0 - 1.0 (higher = riskier)
    max_position_size: float  # Maximum recommended position size

class RiskEngine:
    """
    Validates trade suggestions against risk management rules
    Ensures trades meet safety criteria before execution
    """
    
    def __init__(self):
        # Risk parameters
        self.max_risk_per_trade = 0.02  # 2% max risk per trade
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.min_confidence = 0.60  # Minimum confidence required
        self.max_positions = 5  # Maximum concurrent positions
        
        # Track daily performance
        self.daily_trades = []
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def validate_trade(self, trade_suggestion, strategy_choice, account_size: float = 100000) -> RiskAssessment:
        """
        Validate trade suggestion against risk rules
        """
        try:
            # Reset daily tracking if new day
            self._reset_daily_if_needed()
            
            # Check minimum confidence
            if trade_suggestion.confidence < self.min_confidence:
                return RiskAssessment(
                    approved=False,
                    reason=f"Confidence too low: {trade_suggestion.confidence:.2f} < {self.min_confidence}",
                    risk_score=0.8,
                    max_position_size=0
                )
            
            # Check daily loss limit
            if self.daily_pnl < -self.max_daily_loss * account_size:
                return RiskAssessment(
                    approved=False,
                    reason=f"Daily loss limit exceeded: {self.daily_pnl:.2f}",
                    risk_score=0.9,
                    max_position_size=0
                )
            
            # Calculate position risk
            position_risk = self._calculate_position_risk(trade_suggestion, account_size)
            
            # Check risk per trade limit
            if position_risk > self.max_risk_per_trade * account_size:
                return RiskAssessment(
                    approved=False,
                    reason=f"Position risk too high: {position_risk:.2f} > {self.max_risk_per_trade * account_size:.2f}",
                    risk_score=0.7,
                    max_position_size=0
                )
            
            # Check strategy-specific risks
            strategy_risk = self._validate_strategy_risk(trade_suggestion, strategy_choice)
            if not strategy_risk[0]:
                return RiskAssessment(
                    approved=False,
                    reason=strategy_risk[1],
                    risk_score=0.6,
                    max_position_size=0
                )
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(trade_suggestion, position_risk, account_size)
            
            # Calculate maximum position size
            max_size = self._calculate_max_position_size(trade_suggestion, account_size)
            
            return RiskAssessment(
                approved=True,
                reason="Trade meets all risk criteria",
                risk_score=risk_score,
                max_position_size=max_size
            )
            
        except Exception as e:
            logger.error(f"Risk validation error: {e}")
            return RiskAssessment(
                approved=False,
                reason="Risk assessment error",
                risk_score=1.0,
                max_position_size=0
            )
    
    def _reset_daily_if_needed(self):
        """Reset daily tracking if it's a new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trades = []
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
    
    def _calculate_position_risk(self, trade_suggestion, account_size: float) -> float:
        """Calculate maximum possible loss for position"""
        try:
            # Risk = (Entry - Stoploss) * Contract multiplier * Quantity
            entry_price = trade_suggestion.entry_price
            stoploss_price = trade_suggestion.stoploss_price
            
            # Maximum loss per contract
            loss_per_contract = abs(entry_price - stoploss_price)
            
            # Assume minimum quantity (1 contract) for risk calculation
            position_risk = loss_per_contract * 75  # NFO contract multiplier
            
            # Cap position risk to reasonable amount
            max_reasonable_risk = account_size * 0.01  # 1% of account as max reasonable risk
            position_risk = min(position_risk, max_reasonable_risk)
            
            return position_risk
            
        except Exception as e:
            logger.error(f"Position risk calculation error: {e}")
            return account_size * 0.01  # Conservative estimate
    
    def _validate_strategy_risk(self, trade_suggestion, strategy_choice) -> Tuple[bool, str]:
        """Validate strategy-specific risk rules"""
        try:
            strategy = trade_suggestion.strategy
            
            if strategy in ["Long Call", "Long Put"]:
                # Directional trades - check for reasonable risk/reward
                risk = abs(trade_suggestion.entry_price - trade_suggestion.stoploss_price)
                reward = abs(trade_suggestion.target_price - trade_suggestion.entry_price)
                
                if reward <= 0:
                    return False, "Invalid reward calculation"
                
                risk_reward_ratio = reward / risk
                
                if risk_reward_ratio < 1.5:
                    return False, f"Risk/reward ratio too low: {risk_reward_ratio:.2f}"
                
            elif strategy in ["Bull Call Spread", "Bear Put Spread"]:
                # Spread trades - check for reasonable width
                if trade_suggestion.entry_price < 10:
                    return False, "Spread premium too low"
                
                if trade_suggestion.entry_price > 100:
                    return False, "Spread premium too high"
                
            elif strategy == "Iron Condor":
                # Iron condor - check for reasonable credit
                if trade_suggestion.entry_price < 15:
                    return False, "Iron condor credit too low"
                
                if trade_suggestion.entry_price > 80:
                    return False, "Iron condor credit too high"
                
            elif strategy in ["Straddle", "Strangle"]:
                # Volatility trades - check premium levels
                if trade_suggestion.entry_price < 30:
                    return False, "Volatility trade premium too low"
                
                if trade_suggestion.entry_price > 200:
                    return False, "Volatility trade premium too high"
            
            return True, "Strategy risk validation passed"
            
        except Exception as e:
            logger.error(f"Strategy risk validation error: {e}")
            return False, "Strategy risk validation error"
    
    def _calculate_risk_score(self, trade_suggestion, position_risk: float, account_size: float) -> float:
        """Calculate overall risk score (0.0 = safe, 1.0 = risky)"""
        try:
            risk_score = 0.0
            
            # Position size risk (0-0.3)
            size_risk = position_risk / account_size
            risk_score += min(size_risk / self.max_risk_per_trade, 1.0) * 0.3
            
            # Confidence risk (0-0.2)
            confidence_risk = 1.0 - trade_suggestion.confidence
            risk_score += confidence_risk * 0.2
            
            # Strategy risk (0-0.2)
            strategy_risk_map = {
                "Long Call": 0.7,
                "Long Put": 0.7,
                "Bull Call Spread": 0.4,
                "Bear Put Spread": 0.4,
                "Iron Condor": 0.3,
                "Straddle": 0.8,
                "Strangle": 0.6
            }
            strategy_risk = strategy_risk_map.get(trade_suggestion.strategy, 0.5)
            risk_score += strategy_risk * 0.2
            
            # Daily performance risk (0-0.2)
            if self.daily_pnl < 0:
                daily_risk = min(abs(self.daily_pnl) / (self.max_daily_loss * account_size), 1.0)
                risk_score += daily_risk * 0.2
            
            # Trade count risk (0-0.1)
            if len(self.daily_trades) >= self.max_positions:
                risk_score += 0.1
            else:
                risk_score += (len(self.daily_trades) / self.max_positions) * 0.1
            
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Risk score calculation error: {e}")
            return 0.8  # Conservative default
    
    def _calculate_max_position_size(self, trade_suggestion, account_size: float) -> float:
        """Calculate maximum position size in number of contracts"""
        try:
            # Maximum risk amount
            max_risk_amount = account_size * self.max_risk_per_trade
            
            # Risk per contract
            risk_per_contract = abs(trade_suggestion.entry_price - trade_suggestion.stoploss_price) * 75
            
            if risk_per_contract <= 0:
                return 0
            
            # Maximum contracts based on risk
            max_contracts = int(max_risk_amount / risk_per_contract)
            
            # Additional limits
            max_contracts = min(max_contracts, 10)  # Max 10 contracts
            max_contracts = max(max_contracts, 1)   # Minimum 1 contract if approved
            
            return max_contracts
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 1  # Conservative default
    
    def calculate_trade_risk(self, trade_suggestion, capital: float = 100000) -> Dict[str, Any]:
        """
        Calculate detailed risk metrics for a trade suggestion
        """
        try:
            # Handle both objects (AITradeOutput) and dicts (trade_calc)
            if isinstance(trade_suggestion, dict):
                entry = trade_suggestion.get("entry", 0)
                target = trade_suggestion.get("target", 0)
                stoploss = trade_suggestion.get("stoploss", 0)
            else:
                entry = getattr(trade_suggestion, "entry_price", getattr(trade_suggestion, "entry", 0))
                target = getattr(trade_suggestion, "target_price", getattr(trade_suggestion, "target", 0))
                stoploss = getattr(trade_suggestion, "stoploss_price", getattr(trade_suggestion, "stoploss", 0))
            
            # Distance from entry
            stoploss_distance = abs(entry - stoploss)
            target_distance = abs(target - entry)
            
            # Risk/Reward
            rr_ratio = target_distance / stoploss_distance if stoploss_distance > 0 else 0
            
            # Lot size calculation (risk 2% of capital)
            risk_per_trade = capital * self.max_risk_per_trade
            
            # Risk per contract (stoploss distance * multiplier)
            risk_per_contract = stoploss_distance * 75
            
            lot_size = int(risk_per_trade / risk_per_contract) if risk_per_contract > 0 else 1
            lot_size = max(1, min(lot_size, 10)) # Reasonable bounds
            
            # Expected PnL (absolute values)
            expected_loss = risk_per_contract * lot_size
            expected_profit = target_distance * 75 * lot_size
            
            return {
                "expected_profit": round(expected_profit, 2),
                "expected_loss": round(expected_loss, 2),
                "risk_reward_ratio": round(rr_ratio, 2),
                "lot_size": lot_size
            }
        except Exception as e:
            logger.error(f"Error calculating detailed trade risk: {e}")
            return {
                "expected_profit": 0,
                "expected_loss": 0,
                "risk_reward_ratio": 0,
                "lot_size": 1
            }

    def update_daily_performance(self, pnl: float):
        """Update daily P&L after trade completion"""
        try:
            self.daily_pnl += pnl
            self.daily_trades.append({
                'timestamp': datetime.now(),
                'pnl': pnl
            })
            
        except Exception as e:
            logger.error(f"Daily performance update error: {e}")
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Get daily trading summary"""
        return {
            'date': self.last_reset_date.isoformat(),
            'trades_count': len(self.daily_trades),
            'daily_pnl': self.daily_pnl,
            'max_daily_loss': self.max_daily_loss * 100000,  # Assuming 1L account
            'loss_utilization': (self.daily_pnl / (self.max_daily_loss * 100000)) * 100 if self.daily_pnl < 0 else 0
        }
