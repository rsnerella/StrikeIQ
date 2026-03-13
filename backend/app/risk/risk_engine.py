"""
Risk Engine - Unified Risk Management
Consolidates risk_engine.py, position sizing, and risk assessment components
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import json

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class PositionType(Enum):
    LONG = "long"
    SHORT = "short"
    OPTIONS = "options"
    MULTI_LEG = "multi_leg"

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    risk_score: float  # 0-1
    risk_level: RiskLevel
    position_size: float  # As percentage of portfolio
    max_loss: float  # Maximum potential loss
    var_95: float  # Value at Risk 95%
    expected_shortfall: float  # Expected shortfall
    beta: float  # Portfolio beta
    correlation_risk: float  # Correlation with existing positions
    liquidity_risk: float  # Liquidity risk score
    concentration_risk: float  # Concentration risk score
    volatility_risk: float  # Volatility risk score

@dataclass
class PositionLimits:
    """Position risk limits"""
    max_position_size: float
    max_portfolio_risk: float
    max_sector_exposure: float
    max_correlation: float
    var_limit: float
    stop_loss_limit: float

@dataclass
class RiskAssessment:
    """Complete risk assessment result"""
    symbol: str
    strategy: str
    risk_metrics: RiskMetrics
    recommended_position_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_factors: List[str]
    mitigation_strategies: List[str]
    approval_required: bool
    timestamp: datetime

class RiskEngine:
    """
    Unified Risk Engine
    
    Consolidates:
    - Risk assessment (from ai/risk_engine.py)
    - Position sizing
    - Portfolio risk management
    - Risk limit enforcement
    
    Features:
    - Multi-dimensional risk scoring
    - Dynamic position sizing
    - VaR calculation
    - Correlation analysis
    - Stress testing
    - Risk limit enforcement
    """
    
    def __init__(self):
        # Risk parameters
        self.max_portfolio_risk = 0.02  # 2% max portfolio risk
        self.max_position_risk = 0.05  # 5% max single position risk
        self.max_correlation = 0.7  # Max correlation with existing positions
        self.var_confidence = 0.95  # VaR confidence level
        self.liquidity_threshold = 0.1  # 10% of daily volume max
        
        # Portfolio state
        self.current_positions: Dict[str, Dict[str, Any]] = {}
        self.portfolio_value = 1000000  # Default portfolio value
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Risk limits
        self.position_limits = PositionLimits(
            max_position_size=0.1,  # 10% max per position
            max_portfolio_risk=self.max_portfolio_risk,
            max_sector_exposure=0.3,  # 30% max sector exposure
            max_correlation=self.max_correlation,
            var_limit=0.02,  # 2% daily VaR limit
            stop_loss_limit=0.05  # 5% max stop loss
        )
        
        # Risk history
        self.risk_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Market data cache
        self.market_data: Dict[str, Dict[str, Any]] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        
        logger.info("RiskEngine initialized - Unified risk management")
    
    async def assess_position_risk(self, risk_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk for a potential position
        """
        try:
            symbol = risk_context.get("symbol", "")
            strategy = risk_context.get("strategy", "unknown")
            current_price = risk_context.get("current_price", 0)
            proposed_size = risk_context.get("position_size", 0)
            volatility = risk_context.get("volatility", 0.2)
            
            logger.info(f"Assessing risk for {symbol} - {strategy}")
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_risk_metrics(symbol, risk_context)
            
            # Calculate recommended position size
            recommended_size = await self._calculate_optimal_position_size(symbol, risk_metrics, risk_context)
            
            # Determine stop loss and take profit
            stop_loss = self._calculate_stop_loss(current_price, risk_metrics, strategy)
            take_profit = self._calculate_take_profit(current_price, risk_metrics, strategy)
            
            # Identify risk factors
            risk_factors = self._identify_risk_factors(symbol, risk_metrics, risk_context)
            
            # Generate mitigation strategies
            mitigation_strategies = self._generate_mitigation_strategies(risk_factors, risk_metrics)
            
            # Determine if approval is required
            approval_required = self._requires_approval(risk_metrics, risk_context)
            
            # Create risk assessment
            assessment = RiskAssessment(
                symbol=symbol,
                strategy=strategy,
                risk_metrics=risk_metrics,
                recommended_position_size=recommended_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_factors=risk_factors,
                mitigation_strategies=mitigation_strategies,
                approval_required=approval_required,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Store in history
            self._store_risk_assessment(assessment)
            
            result = {
                "risk_score": risk_metrics.risk_score,
                "risk_level": risk_metrics.risk_level.value,
                "position_size": recommended_size,
                "stop_loss": stop_loss,
                "max_loss": risk_metrics.max_loss,
                "var_95": risk_metrics.var_95,
                "risk_factors": risk_factors,
                "mitigation_strategies": mitigation_strategies,
                "approval_required": approval_required,
                "reasoning": f"Risk assessment complete for {symbol}"
            }
            
            logger.info(f"Risk assessment for {symbol}: {risk_metrics.risk_level.value} risk ({risk_metrics.risk_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error assessing risk for {symbol}: {e}")
            return self._create_default_risk_assessment(symbol)
    
    async def _calculate_risk_metrics(self, symbol: str, risk_context: Dict[str, Any]) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            # Extract context variables
            volatility = risk_context.get("volatility", 0.2)
            current_price = risk_context.get("current_price", 1)
            proposed_size = risk_context.get("position_size", 0)
            strategy = risk_context.get("strategy", "unknown")
            
            # Calculate individual risk components
            volatility_risk = self._calculate_volatility_risk(volatility, strategy)
            liquidity_risk = self._calculate_liquidity_risk(symbol, proposed_size)
            concentration_risk = self._calculate_concentration_risk(symbol, proposed_size)
            correlation_risk = self._calculate_correlation_risk(symbol)
            
            # Calculate portfolio-level metrics
            beta = self._calculate_beta(symbol)
            var_95 = self._calculate_var(symbol, volatility, proposed_size)
            expected_shortfall = self._calculate_expected_shortfall(symbol, volatility, proposed_size)
            max_loss = self._calculate_max_loss(current_price, proposed_size, strategy)
            
            # Calculate overall risk score
            risk_score = self._aggregate_risk_score(
                volatility_risk, liquidity_risk, concentration_risk, 
                correlation_risk, var_95, max_loss
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Calculate position size (as percentage of portfolio)
            position_size_pct = proposed_size * current_price / self.portfolio_value
            
            return RiskMetrics(
                risk_score=risk_score,
                risk_level=risk_level,
                position_size=position_size_pct,
                max_loss=max_loss,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                beta=beta,
                correlation_risk=correlation_risk,
                liquidity_risk=liquidity_risk,
                concentration_risk=concentration_risk,
                volatility_risk=volatility_risk
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return self._create_default_risk_metrics()
    
    def _calculate_volatility_risk(self, volatility: float, strategy: str) -> float:
        """Calculate volatility-based risk score"""
        try:
            # Base volatility risk
            vol_risk = min(1.0, volatility / 0.5)  # Normalize to 0-1, 50% vol = max risk
            
            # Strategy adjustment
            if strategy in ["momentum", "breakout"]:
                vol_risk *= 1.2  # Momentum strategies more sensitive to volatility
            elif strategy in ["mean_reversion"]:
                vol_risk *= 0.8  # Mean reversion benefits from volatility
            elif strategy in ["options"]:
                vol_risk *= 1.5  # Options highly sensitive to volatility
            
            return min(1.0, vol_risk)
            
        except Exception as e:
            logger.error(f"Error calculating volatility risk: {e}")
            return 0.5
    
    def _calculate_liquidity_risk(self, symbol: str, position_size: float) -> float:
        """Calculate liquidity risk score"""
        try:
            # Get market data
            market_data = self.market_data.get(symbol, {})
            daily_volume = market_data.get("daily_volume", 1000000)
            avg_spread = market_data.get("avg_spread", 0.001)
            
            # Position size as percentage of daily volume
            position_volume_ratio = (position_size * 1000) / daily_volume  # Rough estimate
            
            # Liquidity risk based on volume ratio and spread
            volume_risk = min(1.0, position_volume_ratio / self.liquidity_threshold)
            spread_risk = min(1.0, avg_spread / 0.01)  # 1% spread = max risk
            
            # Combine risks
            liquidity_risk = (volume_risk + spread_risk) / 2
            
            return min(1.0, liquidity_risk)
            
        except Exception as e:
            logger.error(f"Error calculating liquidity risk: {e}")
            return 0.3
    
    def _calculate_concentration_risk(self, symbol: str, position_size: float) -> float:
        """Calculate concentration risk"""
        try:
            # Current exposure to symbol
            current_exposure = self.current_positions.get(symbol, {}).get("size", 0)
            total_exposure = current_exposure + position_size
            
            # Concentration as percentage of portfolio
            concentration_pct = (total_exposure * 100) / self.portfolio_value
            
            # Risk increases with concentration
            concentration_risk = min(1.0, concentration_pct / 0.2)  # 20% = max risk
            
            return concentration_risk
            
        except Exception as e:
            logger.error(f"Error calculating concentration risk: {e}")
            return 0.2
    
    def _calculate_correlation_risk(self, symbol: str) -> float:
        """Calculate correlation risk with existing positions"""
        try:
            if not self.current_positions:
                return 0.0
            
            max_correlation = 0.0
            
            # Check correlation with existing positions
            for existing_symbol in self.current_positions:
                correlation = self.correlation_matrix.get(symbol, {}).get(existing_symbol, 0.0)
                max_correlation = max(max_correlation, abs(correlation))
            
            # Risk based on maximum correlation
            correlation_risk = min(1.0, max_correlation / self.max_correlation)
            
            return correlation_risk
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0.3
    
    def _calculate_beta(self, symbol: str) -> float:
        """Calculate beta for the symbol"""
        try:
            # Get historical data for beta calculation
            market_data = self.market_data.get(symbol, {})
            beta = market_data.get("beta", 1.0)  # Default to market beta
            
            # Adjust beta based on strategy
            if abs(beta) > 2:
                beta = 2.0 if beta > 0 else -2.0  # Cap extreme betas
            
            return beta
            
        except Exception as e:
            logger.error(f"Error calculating beta: {e}")
            return 1.0
    
    def _calculate_var(self, symbol: str, volatility: float, position_size: float) -> float:
        """Calculate Value at Risk"""
        try:
            # Simplified VaR calculation
            # VaR = position_value * volatility * z_score
            
            position_value = position_size * 100  # Rough estimate
            z_score = 1.645  # 95% confidence
            
            var_95 = position_value * volatility * z_score
            
            # As percentage of portfolio
            var_pct = var_95 / self.portfolio_value
            
            return min(1.0, var_pct / 0.05)  # 5% VaR = max risk
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0.02
    
    def _calculate_expected_shortfall(self, symbol: str, volatility: float, position_size: float) -> float:
        """Calculate expected shortfall"""
        try:
            # Expected shortfall is typically 1.2-1.5 times VaR
            var_95 = self._calculate_var(symbol, volatility, position_size)
            expected_shortfall = var_95 * 1.3
            
            return min(1.0, expected_shortfall / 0.05)  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating expected shortfall: {e}")
            return 0.03
    
    def _calculate_max_loss(self, current_price: float, position_size: float, strategy: str) -> float:
        """Calculate maximum potential loss"""
        try:
            # Base max loss calculation
            if strategy in ["options"]:
                max_loss_pct = 0.3  # Options can lose 100% of premium
            elif strategy in ["short"]:
                max_loss_pct = 0.1  # Short positions have unlimited risk
            else:
                max_loss_pct = 0.05  # Long positions typically 5% stop loss
            
            position_value = position_size * current_price
            max_loss = position_value * max_loss_pct
            
            # As percentage of portfolio
            max_loss_pct_portfolio = max_loss / self.portfolio_value
            
            return min(1.0, max_loss_pct_portfolio / 0.05)  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating max loss: {e}")
            return 0.05
    
    def _aggregate_risk_score(self, *risk_components) -> float:
        """Aggregate individual risk components into overall score"""
        try:
            # Weight different risk components
            weights = {
                0: 0.25,  # volatility_risk
                1: 0.15,  # liquidity_risk
                2: 0.20,  # concentration_risk
                3: 0.15,  # correlation_risk
                4: 0.15,  # var_95
                5: 0.10   # max_loss
            }
            
            weighted_score = sum(comp * weights.get(i, 0.1) for i, comp in enumerate(risk_components))
            
            return min(1.0, weighted_score)
            
        except Exception as e:
            logger.error(f"Error aggregating risk score: {e}")
            return 0.5
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from risk score"""
        if risk_score < 0.2:
            return RiskLevel.LOW
        elif risk_score < 0.4:
            return RiskLevel.MEDIUM
        elif risk_score < 0.7:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME
    
    async def _calculate_optimal_position_size(self, symbol: str, risk_metrics: RiskMetrics, risk_context: Dict[str, Any]) -> float:
        """Calculate optimal position size based on risk metrics"""
        try:
            # Base position size from risk level
            if risk_metrics.risk_level == RiskLevel.LOW:
                base_size = 0.05  # 5%
            elif risk_metrics.risk_level == RiskLevel.MEDIUM:
                base_size = 0.03  # 3%
            elif risk_metrics.risk_level == RiskLevel.HIGH:
                base_size = 0.02  # 2%
            else:  # EXTREME
                base_size = 0.01  # 1%
            
            # Adjust for risk score
            risk_adjustment = 1 - risk_metrics.risk_score * 0.5  # Reduce size for higher risk
            adjusted_size = base_size * risk_adjustment
            
            # Apply limits
            max_size = self.position_limits.max_position_size
            min_size = 0.01  # Minimum 1%
            
            optimal_size = max(min_size, min(max_size, adjusted_size))
            
            return optimal_size
            
        except Exception as e:
            logger.error(f"Error calculating optimal position size: {e}")
            return 0.02  # Default 2%
    
    def _calculate_stop_loss(self, current_price: float, risk_metrics: RiskMetrics, strategy: str) -> Optional[float]:
        """Calculate stop loss level"""
        try:
            if strategy in ["options"]:
                return None  # Options have different stop logic
            
            # Stop loss based on volatility and risk level
            volatility_adjustment = risk_metrics.volatility_risk * 0.02  # 0-2% based on volatility
            
            if risk_metrics.risk_level == RiskLevel.LOW:
                stop_loss_pct = 0.02 + volatility_adjustment
            elif risk_metrics.risk_level == RiskLevel.MEDIUM:
                stop_loss_pct = 0.03 + volatility_adjustment
            elif risk_metrics.risk_level == RiskLevel.HIGH:
                stop_loss_pct = 0.04 + volatility_adjustment
            else:  # EXTREME
                stop_loss_pct = 0.05 + volatility_adjustment
            
            # Cap stop loss at 10%
            stop_loss_pct = min(stop_loss_pct, 0.10)
            
            return current_price * (1 - stop_loss_pct)
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return None
    
    def _calculate_take_profit(self, current_price: float, risk_metrics: RiskMetrics, strategy: str) -> Optional[float]:
        """Calculate take profit level"""
        try:
            if strategy in ["options"]:
                return None  # Options have different profit logic
            
            # Risk-reward ratio based on risk level
            if risk_metrics.risk_level == RiskLevel.LOW:
                risk_reward = 3.0
            elif risk_metrics.risk_level == RiskLevel.MEDIUM:
                risk_reward = 2.5
            elif risk_metrics.risk_level == RiskLevel.HIGH:
                risk_reward = 2.0
            else:  # EXTREME
                risk_reward = 1.5
            
            # Calculate stop loss first to determine take profit
            stop_loss = self._calculate_stop_loss(current_price, risk_metrics, strategy)
            if stop_loss is None:
                return None
            
            # Calculate take profit based on risk-reward ratio
            stop_distance = current_price - stop_loss
            take_profit_distance = stop_distance * risk_reward
            take_profit = current_price + take_profit_distance
            
            return take_profit
            
        except Exception as e:
            logger.error(f"Error calculating take profit: {e}")
            return None
    
    def _identify_risk_factors(self, symbol: str, risk_metrics: RiskMetrics, risk_context: Dict[str, Any]) -> List[str]:
        """Identify specific risk factors"""
        risk_factors = []
        
        # High volatility
        if risk_metrics.volatility_risk > 0.7:
            risk_factors.append(f"High volatility risk ({risk_metrics.volatility_risk:.1%})")
        
        # Liquidity concerns
        if risk_metrics.liquidity_risk > 0.6:
            risk_factors.append(f"Liquidity risk ({risk_metrics.liquidity_risk:.1%})")
        
        # Concentration risk
        if risk_metrics.concentration_risk > 0.5:
            risk_factors.append(f"High concentration ({risk_metrics.concentration_risk:.1%})")
        
        # Correlation risk
        if risk_metrics.correlation_risk > 0.6:
            risk_factors.append(f"High correlation with existing positions ({risk_metrics.correlation_risk:.1%})")
        
        # High beta
        if abs(risk_metrics.beta) > 1.5:
            risk_factors.append(f"High beta ({risk_metrics.beta:.1f})")
        
        # VaR concerns
        if risk_metrics.var_95 > 0.8:
            risk_factors.append(f"High VaR ({risk_metrics.var_95:.1%})")
        
        # Strategy-specific risks
        strategy = risk_context.get("strategy", "")
        if strategy == "options":
            risk_factors.append("Options time decay risk")
        elif strategy == "short":
            risk_factors.append("Unlimited loss potential")
        
        return risk_factors
    
    def _generate_mitigation_strategies(self, risk_factors: List[str], risk_metrics: RiskMetrics) -> List[str]:
        """Generate risk mitigation strategies"""
        strategies = []
        
        # General strategies
        if risk_metrics.risk_score > 0.5:
            strategies.append("Reduce position size")
            strategies.append("Set tighter stop loss")
        
        # Specific mitigation based on risk factors
        for factor in risk_factors:
            if "volatility" in factor.lower():
                strategies.append("Use volatility-adjusted position sizing")
            elif "liquidity" in factor.lower():
                strategies.append("Monitor market depth")
                strategies.append("Use limit orders")
            elif "concentration" in factor.lower():
                strategies.append("Diversify across symbols")
                strategies.append("Consider hedging")
            elif "correlation" in factor.lower():
                strategies.append("Add uncorrelated positions")
                strategies.append("Use sector diversification")
            elif "beta" in factor.lower():
                strategies.append("Adjust portfolio beta")
                strategies.append("Consider beta hedging")
            elif "options" in factor.lower():
                strategies.append("Monitor time decay")
                strategies.append("Consider spread strategies")
            elif "short" in factor.lower():
                strategies.append("Set hard stop loss")
                strategies.append("Monitor short interest")
        
        return list(set(strategies))  # Remove duplicates
    
    def _requires_approval(self, risk_metrics: RiskMetrics, risk_context: Dict[str, Any]) -> bool:
        """Determine if position requires approval"""
        # High risk positions require approval
        if risk_metrics.risk_level == RiskLevel.EXTREME:
            return True
        
        # Large positions require approval
        if risk_metrics.position_size > 0.05:  # 5% of portfolio
            return True
        
        # High VaR requires approval
        if risk_metrics.var_95 > 0.8:
            return True
        
        # Strategies with unlimited risk
        strategy = risk_context.get("strategy", "")
        if strategy in ["short", "options"]:
            return True
        
        return False
    
    def _store_risk_assessment(self, assessment: RiskAssessment) -> None:
        """Store risk assessment in history"""
        self.risk_history.append({
            "symbol": assessment.symbol,
            "strategy": assessment.strategy,
            "risk_score": assessment.risk_metrics.risk_score,
            "risk_level": assessment.risk_metrics.risk_level.value,
            "position_size": assessment.recommended_position_size,
            "timestamp": assessment.timestamp.isoformat(),
            "approval_required": assessment.approval_required
        })
        
        # Limit history size
        if len(self.risk_history) > self.max_history_size:
            self.risk_history = self.risk_history[-self.max_history_size:]
    
    def _create_default_risk_metrics(self) -> RiskMetrics:
        """Create default risk metrics for error cases"""
        return RiskMetrics(
            risk_score=0.5,
            risk_level=RiskLevel.MEDIUM,
            position_size=0.02,
            max_loss=0.02,
            var_95=0.02,
            expected_shortfall=0.025,
            beta=1.0,
            correlation_risk=0.3,
            liquidity_risk=0.3,
            concentration_risk=0.2,
            volatility_risk=0.5
        )
    
    def _create_default_risk_assessment(self, symbol: str) -> Dict[str, Any]:
        """Create default risk assessment for error cases"""
        return {
            "risk_score": 0.5,
            "risk_level": "medium",
            "position_size": 0.02,
            "stop_loss": None,
            "max_loss": 0.02,
            "var_95": 0.02,
            "risk_factors": ["Error in risk calculation"],
            "mitigation_strategies": ["Use conservative position sizing"],
            "approval_required": True,
            "reasoning": f"Error in risk assessment for {symbol}"
        }
    
    # Portfolio risk management
    def update_position(self, symbol: str, position_data: Dict[str, Any]) -> None:
        """Update current position data"""
        self.current_positions[symbol] = position_data
        logger.info(f"Updated position for {symbol}: {position_data.get('size', 0)}")
    
    def close_position(self, symbol: str) -> None:
        """Close position for symbol"""
        if symbol in self.current_positions:
            del self.current_positions[symbol]
            logger.info(f"Closed position for {symbol}")
    
    def update_market_data(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Update market data for risk calculations"""
        self.market_data[symbol] = market_data
    
    def update_correlation_matrix(self, correlation_matrix: Dict[str, Dict[str, float]]) -> None:
        """Update correlation matrix"""
        self.correlation_matrix = correlation_matrix
    
    def calculate_portfolio_risk(self) -> Dict[str, Any]:
        """Calculate overall portfolio risk"""
        try:
            if not self.current_positions:
                return {
                    "portfolio_risk": 0.0,
                    "risk_level": "low",
                    "positions_count": 0,
                    "max_drawdown": self.current_drawdown,
                    "var_95": 0.0
                }
            
            # Calculate portfolio metrics
            total_position_size = sum(pos.get("size", 0) for pos in self.current_positions.values())
            portfolio_risk = total_position_size / self.portfolio_value
            
            # Calculate portfolio VaR
            portfolio_var = 0.0
            for symbol, position in self.current_positions.items():
                symbol_var = self._calculate_var(
                    symbol, 
                    position.get("volatility", 0.2), 
                    position.get("size", 0)
                )
                portfolio_var += symbol_var
            
            # Determine risk level
            if portfolio_risk < 0.1:
                risk_level = "low"
            elif portfolio_risk < 0.2:
                risk_level = "medium"
            elif portfolio_risk < 0.3:
                risk_level = "high"
            else:
                risk_level = "extreme"
            
            return {
                "portfolio_risk": portfolio_risk,
                "risk_level": risk_level,
                "positions_count": len(self.current_positions),
                "max_drawdown": self.current_drawdown,
                "var_95": portfolio_var,
                "positions": list(self.current_positions.keys())
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {
                "portfolio_risk": 0.5,
                "risk_level": "medium",
                "positions_count": 0,
                "max_drawdown": self.current_drawdown,
                "var_95": 0.0
            }
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """Get risk engine statistics"""
        return {
            "current_positions": len(self.current_positions),
            "risk_assessments": len(self.risk_history),
            "portfolio_value": self.portfolio_value,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "risk_limits": {
                "max_portfolio_risk": self.position_limits.max_portfolio_risk,
                "max_position_size": self.position_limits.max_position_size,
                "var_limit": self.position_limits.var_limit
            }
        }
    
    # Cleanup methods
    def clear_risk_data(self) -> None:
        """Clear all risk data"""
        self.current_positions.clear()
        self.risk_history.clear()
        self.market_data.clear()
        self.correlation_matrix.clear()
        logger.info("Cleared all risk data")
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down RiskEngine")
        self.clear_risk_data()
        logger.info("RiskEngine shutdown complete")
