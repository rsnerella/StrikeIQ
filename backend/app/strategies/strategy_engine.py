"""
Strategy Engine - Unified Trading Strategy Management
Consolidates strategy_engine.py, trade_decision_engine.py, and related strategy components
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    OPTIONS = "options"
    STRUCTURAL = "structural"
    VOLATILITY = "volatility"
    INSTITUTIONAL = "institutional"
    COMPOSITE = "composite"

class Action(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    INCREASE = "INCREASE"

@dataclass
class StrategySignal:
    """Unified strategy signal"""
    strategy_type: StrategyType
    action: Action
    confidence: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    target_price: Optional[float]
    position_size: float
    timeframe: str  # intraday, swing, positional
    reasoning: List[str]
    risk_reward_ratio: float
    expiration: Optional[datetime]
    conditions: List[str]

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    strategy_type: StrategyType
    parameters: Dict[str, Any]
    risk_limits: Dict[str, float]
    timeframes: List[str]
    symbols: List[str]
    enabled: bool
    priority: int

class StrategyEngine:
    """
    Unified Strategy Engine
    
    Consolidates:
    - Strategy generation (from ai/strategy_engine.py)
    - Trade decision making (from ai/trade_decision_engine.py)
    - Strategy execution logic
    
    Features:
    - Multiple strategy types
    - Dynamic strategy selection
    - Risk-aware position sizing
    - Multi-timeframe analysis
    - Strategy performance tracking
    """
    
    def __init__(self):
        # Strategy configurations
        self.strategy_configs: Dict[StrategyType, StrategyConfig] = {}
        self.active_strategies: Dict[str, StrategySignal] = {}  # symbol -> active strategy
        
        # Strategy parameters
        self.min_confidence_threshold = 0.6
        self.max_position_size = 0.1  # 10% max per strategy
        self.default_risk_reward = 2.0
        
        # Performance tracking
        self.strategy_performance: Dict[StrategyType, Dict[str, float]] = {}
        self.signal_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Risk management
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_concurrent_positions = 5
        self.position_timeout = 24  # hours
        
        # Initialize default strategies
        self._initialize_default_strategies()
        
        logger.info("StrategyEngine initialized - Unified strategy management")
    
    def _initialize_default_strategies(self) -> None:
        """Initialize default strategy configurations"""
        # Momentum strategy
        self.strategy_configs[StrategyType.MOMENTUM] = StrategyConfig(
            strategy_type=StrategyType.MOMENTUM,
            parameters={
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "momentum_threshold": 0.02,
                "volume_confirmation": True
            },
            risk_limits={
                "max_position_size": 0.05,
                "stop_loss_pct": 0.02,
                "risk_reward_ratio": 2.0
            },
            timeframes=["5m", "15m", "1h"],
            symbols=["NIFTY", "BANKNIFTY"],
            enabled=True,
            priority=1
        )
        
        # Mean reversion strategy
        self.strategy_configs[StrategyType.MEAN_REVERSION] = StrategyConfig(
            strategy_type=StrategyType.MEAN_REVERSION,
            parameters={
                "bb_period": 20,
                "bb_std": 2,
                "rsi_period": 14,
                "oversold_threshold": 20,
                "overbought_threshold": 80
            },
            risk_limits={
                "max_position_size": 0.03,
                "stop_loss_pct": 0.015,
                "risk_reward_ratio": 1.5
            },
            timeframes=["15m", "1h"],
            symbols=["NIFTY", "BANKNIFTY"],
            enabled=True,
            priority=2
        )
        
        # Breakout strategy
        self.strategy_configs[StrategyType.BREAKOUT] = StrategyConfig(
            strategy_type=StrategyType.BREAKOUT,
            parameters={
                "breakout_period": 20,
                "volume_multiplier": 1.5,
                "confirmation_candles": 2,
                "false_breakout_filter": True
            },
            risk_limits={
                "max_position_size": 0.04,
                "stop_loss_pct": 0.025,
                "risk_reward_ratio": 2.5
            },
            timeframes=["15m", "1h", "4h"],
            symbols=["NIFTY", "BANKNIFTY"],
            enabled=True,
            priority=3
        )
        
        # Options strategy
        self.strategy_configs[StrategyType.OPTIONS] = StrategyConfig(
            strategy_type=StrategyType.OPTIONS,
            parameters={
                "min_oi": 10000,
                "volume_threshold": 1000,
                "iv_percentile_threshold": 0.7,
                "gamma_threshold": 50000
            },
            risk_limits={
                "max_position_size": 0.02,
                "stop_loss_pct": 0.3,
                "risk_reward_ratio": 3.0
            },
            timeframes=["5m", "15m"],
            symbols=["NIFTY", "BANKNIFTY"],
            enabled=True,
            priority=4
        )
        
        # Initialize performance tracking
        for strategy_type in self.strategy_configs:
            self.strategy_performance[strategy_type] = {
                "total_signals": 0,
                "successful_signals": 0,
                "success_rate": 0.0,
                "avg_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0
            }
    
    async def generate_strategies(
        self,
        symbol: str,
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate strategy recommendations based on market context
        """
        try:
            logger.info(f"Generating strategies for {symbol}")
            
            # Analyze market context
            regime = market_context.get("regime", "unknown")
            volatility = market_context.get("volatility_regime", "normal")
            institutional_bias = market_context.get("institutional_bias", "NEUTRAL")
            
            # Generate signals for each enabled strategy
            all_signals = []
            
            for strategy_type, config in self.strategy_configs.items():
                if not config.enabled or symbol not in config.symbols:
                    continue
                
                try:
                    signal = await self._generate_strategy_signal(strategy_type, symbol, market_context, config)
                    if signal and signal.confidence >= self.min_confidence_threshold:
                        all_signals.append(signal)
                        
                except Exception as e:
                    logger.error(f"Error generating {strategy_type.value} signal for {symbol}: {e}")
            
            # Rank signals by confidence and priority
            ranked_signals = self._rank_signals(all_signals)
            
            # Select primary strategy
            primary_signal = ranked_signals[0] if ranked_signals else None
            
            # Generate recommendations
            recommendations = []
            for signal in ranked_signals[:3]:  # Top 3 strategies
                recommendations.append({
                    "strategy_type": signal.strategy_type.value,
                    "action": signal.action.value,
                    "confidence": signal.confidence,
                    "risk_reward_ratio": signal.risk_reward_ratio,
                    "reasoning": signal.reasoning
                })
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "primary_strategy": primary_signal.strategy_type.value if primary_signal else "HOLD",
                "primary_action": primary_signal.action.value if primary_signal else "HOLD",
                "strategy_confidence": primary_signal.confidence if primary_signal else 0.0,
                "recommended_strategies": recommendations,
                "market_context": {
                    "regime": regime,
                    "volatility": volatility,
                    "institutional_bias": institutional_bias
                },
                "entry_conditions": primary_signal.conditions if primary_signal else [],
                "exit_conditions": self._generate_exit_conditions(primary_signal) if primary_signal else [],
                "reasoning": primary_signal.reasoning if primary_signal else ["No clear strategy identified"]
            }
            
            # Store primary strategy if actionable
            if primary_signal and primary_signal.action in [Action.LONG, Action.SHORT]:
                self.active_strategies[symbol] = primary_signal
            
            logger.info(f"Generated {len(recommendations)} strategy recommendations for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating strategies for {symbol}: {e}")
            return self._create_default_strategy_result(symbol)
    
    async def _generate_strategy_signal(
        self,
        strategy_type: StrategyType,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate signal for specific strategy type"""
        try:
            if strategy_type == StrategyType.MOMENTUM:
                return await self._generate_momentum_signal(symbol, market_context, config)
            elif strategy_type == StrategyType.MEAN_REVERSION:
                return await self._generate_mean_reversion_signal(symbol, market_context, config)
            elif strategy_type == StrategyType.BREAKOUT:
                return await self._generate_breakout_signal(symbol, market_context, config)
            elif strategy_type == StrategyType.OPTIONS:
                return await self._generate_options_signal(symbol, market_context, config)
            elif strategy_type == StrategyType.STRUCTURAL:
                return await self._generate_structural_signal(symbol, market_context, config)
            elif strategy_type == StrategyType.INSTITUTIONAL:
                return await self._generate_institutional_signal(symbol, market_context, config)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error generating {strategy_type.value} signal: {e}")
            return None
    
    async def _generate_momentum_signal(
        self,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate momentum-based strategy signal"""
        try:
            params = config.parameters
            current_price = market_context.get("current_price", 0)
            
            if current_price == 0:
                return None
            
            # Extract momentum indicators
            rsi = market_context.get("rsi", 50)
            momentum_score = market_context.get("momentum_score", 0)
            volume_trend = market_context.get("volume_trend", 0)
            
            # Generate signal logic
            action = None
            confidence = 0.0
            reasoning = []
            
            # Bullish momentum
            if (rsi < params["rsi_overbought"] and 
                momentum_score > params["momentum_threshold"] and
                volume_trend > 0):
                
                action = Action.LONG
                confidence = min(0.9, (momentum_score + (70 - rsi) / 40) / 2)
                reasoning.append(f"Strong momentum (score: {momentum_score:.2f})")
                reasoning.append(f"RSI not overbought ({rsi:.1f})")
                if volume_trend > 0:
                    reasoning.append(f"Volume confirmation (trend: {volume_trend:.2f})")
            
            # Bearish momentum
            elif (rsi > params["rsi_oversold"] and 
                  momentum_score < -params["momentum_threshold"] and
                  volume_trend < 0):
                
                action = Action.SHORT
                confidence = min(0.9, (abs(momentum_score) + (rsi - 30) / 40) / 2)
                reasoning.append(f"Strong negative momentum (score: {momentum_score:.2f})")
                reasoning.append(f"RSI not oversold ({rsi:.1f})")
                if volume_trend < 0:
                    reasoning.append(f"Volume confirmation (trend: {volume_trend:.2f})")
            
            if action and confidence >= self.min_confidence_threshold:
                # Calculate position details
                stop_loss_pct = config.risk_limits["stop_loss_pct"]
                risk_reward = config.risk_limits["risk_reward_ratio"]
                
                if action == Action.LONG:
                    stop_loss = current_price * (1 - stop_loss_pct)
                    target_price = current_price * (1 + stop_loss_pct * risk_reward)
                else:  # SHORT
                    stop_loss = current_price * (1 + stop_loss_pct)
                    target_price = current_price * (1 - stop_loss_pct * risk_reward)
                
                position_size = min(config.risk_limits["max_position_size"], confidence * 0.1)
                
                return StrategySignal(
                    strategy_type=StrategyType.MOMENTUM,
                    action=action,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    target_price=target_price,
                    position_size=position_size,
                    timeframe="intraday",
                    reasoning=reasoning,
                    risk_reward_ratio=risk_reward,
                    expiration=None,
                    conditions=[f"RSI between {params['rsi_oversold']}-{params['rsi_overbought']}", 
                             f"Momentum score > {params['momentum_threshold']}"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating momentum signal: {e}")
            return None
    
    async def _generate_mean_reversion_signal(
        self,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate mean reversion strategy signal"""
        try:
            params = config.parameters
            current_price = market_context.get("current_price", 0)
            
            if current_price == 0:
                return None
            
            # Extract mean reversion indicators
            bb_position = market_context.get("bb_position", 0.5)  # 0-1, 0.5 = middle
            rsi = market_context.get("rsi", 50)
            distance_to_support = market_context.get("distance_to_support", 0)
            distance_to_resistance = market_context.get("distance_to_resistance", 0)
            
            action = None
            confidence = 0.0
            reasoning = []
            
            # Oversold conditions (buy signal)
            if (bb_position < 0.2 and  # Near lower Bollinger Band
                rsi < params["oversold_threshold"] and
                distance_to_support < 0.02):  # Within 2% of support
                
                action = Action.LONG
                confidence = min(0.85, (0.5 - bb_position) + (30 - rsi) / 50 + (0.02 - distance_to_support) / 0.04)
                reasoning.append(f"Oversold conditions (BB position: {bb_position:.2f})")
                reasoning.append(f"Low RSI ({rsi:.1f})")
                reasoning.append(f"Near support level ({distance_to_support:.2%})")
            
            # Overbought conditions (sell signal)
            elif (bb_position > 0.8 and  # Near upper Bollinger Band
                  rsi > params["overbought_threshold"] and
                  distance_to_resistance < 0.02):  # Within 2% of resistance
                
                action = Action.SHORT
                confidence = min(0.85, (bb_position - 0.5) + (rsi - 70) / 50 + (0.02 - distance_to_resistance) / 0.04)
                reasoning.append(f"Overbought conditions (BB position: {bb_position:.2f})")
                reasoning.append(f"High RSI ({rsi:.1f})")
                reasoning.append(f"Near resistance level ({distance_to_resistance:.2%})")
            
            if action and confidence >= self.min_confidence_threshold:
                # Calculate position details
                stop_loss_pct = config.risk_limits["stop_loss_pct"]
                risk_reward = config.risk_limits["risk_reward_ratio"]
                
                if action == Action.LONG:
                    stop_loss = current_price * (1 - stop_loss_pct)
                    target_price = current_price * (1 + stop_loss_pct * risk_reward)
                else:  # SHORT
                    stop_loss = current_price * (1 + stop_loss_pct)
                    target_price = current_price * (1 - stop_loss_pct * risk_reward)
                
                position_size = min(config.risk_limits["max_position_size"], confidence * 0.08)
                
                return StrategySignal(
                    strategy_type=StrategyType.MEAN_REVERSION,
                    action=action,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    target_price=target_price,
                    position_size=position_size,
                    timeframe="swing",
                    reasoning=reasoning,
                    risk_reward_ratio=risk_reward,
                    expiration=None,
                    conditions=[f"BB position {'<' if action == Action.LONG else '>'} {0.2 if action == Action.LONG else 0.8}",
                             f"RSI {'<' if action == Action.LONG else '>'} {params['oversold_threshold'] if action == Action.LONG else params['overbought_threshold']}"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating mean reversion signal: {e}")
            return None
    
    async def _generate_breakout_signal(
        self,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate breakout strategy signal"""
        try:
            params = config.parameters
            current_price = market_context.get("current_price", 0)
            
            if current_price == 0:
                return None
            
            # Extract breakout indicators
            breakout_detected = market_context.get("breakout_detected", False)
            breakout_direction = market_context.get("breakout_direction", "neutral")
            volume_spike = market_context.get("volume_spike", False)
            trend_strength = market_context.get("trend_strength_20", 0)
            
            action = None
            confidence = 0.0
            reasoning = []
            
            # Bullish breakout
            if (breakout_detected and 
                breakout_direction == "bullish" and
                volume_spike and
                trend_strength > 0.6):
                
                action = Action.LONG
                confidence = min(0.9, trend_strength * 0.7 + 0.3)
                reasoning.append("Bullish breakout detected")
                reasoning.append(f"Strong trend (strength: {trend_strength:.2f})")
                reasoning.append("Volume confirmation")
            
            # Bearish breakout
            elif (breakout_detected and 
                  breakout_direction == "bearish" and
                  volume_spike and
                  trend_strength > 0.6):
                
                action = Action.SHORT
                confidence = min(0.9, trend_strength * 0.7 + 0.3)
                reasoning.append("Bearish breakout detected")
                reasoning.append(f"Strong trend (strength: {trend_strength:.2f})")
                reasoning.append("Volume confirmation")
            
            if action and confidence >= self.min_confidence_threshold:
                # Calculate position details
                stop_loss_pct = config.risk_limits["stop_loss_pct"]
                risk_reward = config.risk_limits["risk_reward_ratio"]
                
                if action == Action.LONG:
                    stop_loss = current_price * (1 - stop_loss_pct)
                    target_price = current_price * (1 + stop_loss_pct * risk_reward)
                else:  # SHORT
                    stop_loss = current_price * (1 + stop_loss_pct)
                    target_price = current_price * (1 - stop_loss_pct * risk_reward)
                
                position_size = min(config.risk_limits["max_position_size"], confidence * 0.06)
                
                return StrategySignal(
                    strategy_type=StrategyType.BREAKOUT,
                    action=action,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    target_price=target_price,
                    position_size=position_size,
                    timeframe="swing",
                    reasoning=reasoning,
                    risk_reward_ratio=risk_reward,
                    expiration=None,
                    conditions=["Breakout detected", "Volume confirmation", f"Trend strength > 0.6"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating breakout signal: {e}")
            return None
    
    async def _generate_options_signal(
        self,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate options-based strategy signal"""
        try:
            params = config.parameters
            options_data = market_context.get("options_data", {})
            
            if not options_data:
                return None
            
            # Extract options indicators
            total_oi = options_data.get("total_oi", 0)
            total_volume = options_data.get("total_volume", 0)
            iv_percentile = options_data.get("iv_percentile", 0.5)
            net_gamma = options_data.get("net_gamma", 0)
            
            action = None
            confidence = 0.0
            reasoning = []
            
            # High IV options selling (credit strategies)
            if (total_oi > params["min_oi"] and
                total_volume > params["volume_threshold"] and
                iv_percentile > params["iv_percentile_threshold"]):
                
                action = Action.SHORT  # Sell options (credit spread)
                confidence = min(0.8, (iv_percentile - 0.5) * 2)
                reasoning.append(f"High implied volatility ({iv_percentile:.1%} percentile)")
                reasoning.append(f"High open interest ({total_oi:,})")
                reasoning.append(f"High volume ({total_volume:,})")
            
            # Gamma squeeze potential
            elif (abs(net_gamma) > params["gamma_threshold"] and
                  total_volume > params["volume_threshold"]):
                
                direction = "bullish" if net_gamma > 0 else "bearish"
                action = Action.LONG if direction == "bullish" else Action.SHORT
                confidence = min(0.75, abs(net_gamma) / params["gamma_threshold"])
                reasoning.append(f"Gamma squeeze detected (gamma: {net_gamma:,})")
                reasoning.append(f"High volume ({total_volume:,})")
                reasoning.append(f"Direction: {direction}")
            
            if action and confidence >= self.min_confidence_threshold:
                # Options-specific position sizing
                position_size = min(config.risk_limits["max_position_size"], confidence * 0.04)
                
                # Options have wider stops
                stop_loss_pct = config.risk_limits["stop_loss_pct"]
                
                return StrategySignal(
                    strategy_type=StrategyType.OPTIONS,
                    action=action,
                    confidence=confidence,
                    entry_price=None,  # Options use strike prices
                    stop_loss=None,
                    target_price=None,
                    position_size=position_size,
                    timeframe="swing",
                    reasoning=reasoning,
                    risk_reward_ratio=config.risk_limits["risk_reward_ratio"],
                    expiration=datetime.now(timezone.utc) + timedelta(days=7),  # Weekly expiry
                    conditions=[f"OI > {params['min_oi']}", f"Volume > {params['volume_threshold']}"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating options signal: {e}")
            return None
    
    async def _generate_structural_signal(
        self,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate structural analysis-based signal"""
        try:
            structure_data = market_context.get("structure_analysis", {})
            
            if not structure_data:
                return None
            
            trend = structure_data.get("trend", "CHOPPY")
            pattern = structure_data.get("pattern", "CHOPPY")
            confidence = structure_data.get("confidence", 0)
            
            action = None
            reasoning = []
            
            # Follow structural trend
            if trend == "BULLISH" and confidence > 0.7:
                action = Action.LONG
                reasoning.append(f"Bullish structure ({pattern})")
                reasoning.append(f"High confidence ({confidence:.1%})")
            elif trend == "BEARISH" and confidence > 0.7:
                action = Action.SHORT
                reasoning.append(f"Bearish structure ({pattern})")
                reasoning.append(f"High confidence ({confidence:.1%})")
            
            if action and confidence >= self.min_confidence_threshold:
                return StrategySignal(
                    strategy_type=StrategyType.STRUCTURAL,
                    action=action,
                    confidence=confidence,
                    entry_price=market_context.get("current_price"),
                    stop_loss=None,
                    target_price=None,
                    position_size=min(config.risk_limits["max_position_size"], confidence * 0.05),
                    timeframe="positional",
                    reasoning=reasoning,
                    risk_reward_ratio=1.5,
                    expiration=None,
                    conditions=[f"Structure: {trend}", f"Pattern: {pattern}"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating structural signal: {e}")
            return None
    
    async def _generate_institutional_signal(
        self,
        symbol: str,
        market_context: Dict[str, Any],
        config: StrategyConfig
    ) -> Optional[StrategySignal]:
        """Generate institutional flow-based signal"""
        try:
            institutional_data = market_context.get("institutional_analysis", {})
            
            if not institutional_data:
                return None
            
            signal = institutional_data.get("signal", "NEUTRAL")
            inst_confidence = institutional_data.get("confidence", 0)
            strength = institutional_data.get("strength", 0)
            
            action = None
            reasoning = []
            
            # Follow institutional flow
            if signal == "BULLISH" and inst_confidence > 0.6 and strength > 0.5:
                action = Action.LONG
                reasoning.append(f"Bullish institutional flow")
                reasoning.append(f"High confidence ({inst_confidence:.1%})")
                reasoning.append(f"Strong flow ({strength:.1%})")
            elif signal == "BEARISH" and inst_confidence > 0.6 and strength > 0.5:
                action = Action.SHORT
                reasoning.append(f"Bearish institutional flow")
                reasoning.append(f"High confidence ({inst_confidence:.1%})")
                reasoning.append(f"Strong flow ({strength:.1%})")
            
            if action and inst_confidence >= self.min_confidence_threshold:
                return StrategySignal(
                    strategy_type=StrategyType.INSTITUTIONAL,
                    action=action,
                    confidence=inst_confidence,
                    entry_price=market_context.get("current_price"),
                    stop_loss=None,
                    target_price=None,
                    position_size=min(config.risk_limits["max_position_size"], strength * 0.08),
                    timeframe="swing",
                    reasoning=reasoning,
                    risk_reward_ratio=2.0,
                    expiration=None,
                    conditions=[f"Institutional signal: {signal}"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating institutional signal: {e}")
            return None
    
    def _rank_signals(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Rank signals by confidence and strategy priority"""
        if not signals:
            return []
        
        # Sort by confidence (descending) and priority (ascending)
        sorted_signals = sorted(
            signals,
            key=lambda s: (
                s.confidence,
                -self.strategy_configs[s.strategy_type].priority
            ),
            reverse=True
        )
        
        return sorted_signals
    
    def _generate_exit_conditions(self, signal: StrategySignal) -> List[str]:
        """Generate exit conditions for a strategy signal"""
        conditions = []
        
        if signal.stop_loss:
            conditions.append(f"Stop loss at {signal.stop_loss:.2f}")
        
        if signal.target_price:
            conditions.append(f"Target at {signal.target_price:.2f}")
        
        if signal.expiration:
            conditions.append(f"Expires on {signal.expiration.strftime('%Y-%m-%d')}")
        
        # Strategy-specific conditions
        if signal.strategy_type == StrategyType.MOMENTUM:
            conditions.append("Momentum reverses")
        elif signal.strategy_type == StrategyType.MEAN_REVERSION:
            conditions.append("Price returns to mean")
        elif signal.strategy_type == StrategyType.BREAKOUT:
            conditions.append("Breakout fails")
        
        return conditions
    
    def _create_default_strategy_result(self, symbol: str) -> Dict[str, Any]:
        """Create default strategy result for error cases"""
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "primary_strategy": "HOLD",
            "primary_action": "HOLD",
            "strategy_confidence": 0.0,
            "recommended_strategies": [],
            "market_context": {},
            "entry_conditions": [],
            "exit_conditions": [],
            "reasoning": ["Error in strategy generation - defaulting to hold"]
        }
    
    # Strategy management methods
    def update_strategy_performance(self, strategy_type: StrategyType, success: bool, return_pct: float) -> None:
        """Update strategy performance metrics"""
        if strategy_type not in self.strategy_performance:
            self.strategy_performance[strategy_type] = {
                "total_signals": 0,
                "successful_signals": 0,
                "success_rate": 0.0,
                "avg_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0
            }
        
        perf = self.strategy_performance[strategy_type]
        perf["total_signals"] += 1
        
        if success:
            perf["successful_signals"] += 1
        
        perf["success_rate"] = perf["successful_signals"] / perf["total_signals"]
        
        # Update average return
        total_return = perf.get("avg_return", 0) * (perf["total_signals"] - 1) + return_pct
        perf["avg_return"] = total_return / perf["total_signals"]
    
    def get_active_strategy(self, symbol: str) -> Optional[StrategySignal]:
        """Get active strategy for symbol"""
        return self.active_strategies.get(symbol)
    
    def close_strategy(self, symbol: str, reason: str = "Manual close") -> None:
        """Close active strategy for symbol"""
        if symbol in self.active_strategies:
            logger.info(f"Closed strategy for {symbol}: {reason}")
            del self.active_strategies[symbol]
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get strategy performance statistics"""
        return {
            "performance_by_strategy": self.strategy_performance,
            "total_signals": sum(p["total_signals"] for p in self.strategy_performance.values()),
            "overall_success_rate": (
                sum(p["successful_signals"] for p in self.strategy_performance.values()) /
                max(sum(p["total_signals"] for p in self.strategy_performance.values()), 1)
            ),
            "best_performing_strategy": max(
                self.strategy_performance.items(),
                key=lambda x: x[1]["success_rate"]
            )[0].value if self.strategy_performance else None
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy engine statistics"""
        return {
            "active_strategies": len(self.active_strategies),
            "total_strategies_configured": len(self.strategy_configs),
            "enabled_strategies": len([s for s in self.strategy_configs.values() if s.enabled]),
            "signal_history_size": len(self.signal_history),
            "performance_summary": self.get_strategy_performance()
        }
    
    # Cleanup methods
    def clear_strategies(self, symbol: Optional[str] = None) -> None:
        """Clear strategies for symbol or all symbols"""
        if symbol:
            if symbol in self.active_strategies:
                del self.active_strategies[symbol]
                logger.info(f"Cleared strategy for {symbol}")
        else:
            self.active_strategies.clear()
            logger.info("Cleared all strategies")
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down StrategyEngine")
        self.clear_strategies()
        self.signal_history.clear()
        logger.info("StrategyEngine shutdown complete")
