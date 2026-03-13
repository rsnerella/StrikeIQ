"""
AI Orchestrator - Unified AI Engine Coordinator
Consolidates and coordinates all AI engines for intelligent trading decisions
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from .regime_engine import RegimeEngine
from .smart_money_engine import SmartMoneyEngine
from .risk_engine import RiskEngine
from .strategy_engine import StrategyEngine
from .learning_engine import LearningEngine
from .probability_engine import ProbabilityEngine

logger = logging.getLogger(__name__)

class SignalType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

@dataclass
class AISignal:
    """Unified AI trading signal"""
    symbol: str
    signal_type: SignalType
    confidence: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    target_price: Optional[float]
    position_size: float
    reasoning: List[str]
    risk_reward_ratio: float
    regime: str
    institutional_bias: str
    probability_score: float
    risk_assessment: Dict[str, Any]
    strategy_recommendations: List[str]

class AIOrchestrator:
    """
    Unified AI Orchestrator
    
    Coordinates all AI engines:
    - RegimeEngine: Market regime detection
    - SmartMoneyEngine: Institutional flow analysis
    - RiskEngine: Risk assessment and position sizing
    - StrategyEngine: Strategy recommendation
    - LearningEngine: Adaptive learning
    - ProbabilityEngine: Outcome probability calculation
    
    Pipeline:
    Market Features → AI Engine Analysis → Probability Prediction → Strategy Decision → Risk Validation
    """
    
    def __init__(self):
        # Initialize all AI engines
        self.regime_engine = RegimeEngine()
        self.smart_money_engine = SmartMoneyEngine()
        self.risk_engine = RiskEngine()
        self.strategy_engine = StrategyEngine()
        self.learning_engine = LearningEngine()
        self.probability_engine = ProbabilityEngine()
        
        # Analysis cache
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Signal generation parameters
        self.min_confidence_threshold = 0.6
        self.max_risk_per_trade = 0.02  # 2% max risk
        
        logger.info("AI Orchestrator initialized - Unified AI coordination")
    
    async def generate_trading_signal(
        self, 
        symbol: str,
        market_data: Dict[str, Any],
        live_metrics: Optional[Dict[str, Any]] = None,
        db_session=None
    ) -> AISignal:
        """
        Generate comprehensive trading signal using all AI engines
        """
        try:
            logger.info(f"Generating AI trading signal for {symbol}")
            
            # Step 1: Regime Analysis
            regime_analysis = await self._analyze_regime(symbol, market_data, live_metrics)
            
            # Step 2: Institutional Flow Analysis
            institutional_analysis = await self._analyze_institutional_flow(symbol, market_data, live_metrics, db_session)
            
            # Step 3: Probability Assessment
            probability_analysis = await self._calculate_probabilities(symbol, market_data, regime_analysis, institutional_analysis)
            
            # Step 4: Strategy Recommendation
            strategy_recommendations = await self._generate_strategies(symbol, regime_analysis, institutional_analysis, probability_analysis)
            
            # Step 5: Risk Assessment
            risk_assessment = await self._assess_risk(symbol, market_data, strategy_recommendations)
            
            # Step 6: Learning Integration
            learning_insights = await self._apply_learning(symbol, regime_analysis, institutional_analysis, probability_analysis)
            
            # Step 7: Signal Synthesis
            signal = self._synthesize_signal(
                symbol, regime_analysis, institutional_analysis, 
                probability_analysis, strategy_recommendations, 
                risk_assessment, learning_insights
            )
            
            # Step 8: Cache results
            self._cache_analysis(symbol, {
                "regime": regime_analysis,
                "institutional": institutional_analysis,
                "probability": probability_analysis,
                "strategy": strategy_recommendations,
                "risk": risk_assessment,
                "learning": learning_insights,
                "signal": signal
            })
            
            logger.info(f"AI signal generated for {symbol}: {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating AI signal for {symbol}: {e}")
            return self._create_default_signal(symbol)
    
    async def _analyze_regime(self, symbol: str, market_data: Dict[str, Any], live_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze market regime using RegimeEngine"""
        try:
            if live_metrics:
                # Use enhanced dynamics analysis
                regime_dynamics = await self.regime_engine.analyze_regime_dynamics(symbol, live_metrics)
                return {
                    "type": "dynamics",
                    "regime": regime_dynamics.regime.value,
                    "confidence": regime_dynamics.confidence,
                    "stability": regime_dynamics.stability_score,
                    "acceleration": regime_dynamics.acceleration_index,
                    "transition_probability": regime_dynamics.transition_probability,
                    "reasoning": regime_dynamics.reasoning,
                    "indicators": regime_dynamics.indicators
                }
            else:
                # Use basic regime detection
                regime_detection = self.regime_engine.detect_regime(market_data)
                return {
                    "type": "basic",
                    "regime": regime_detection.regime,
                    "confidence": regime_detection.confidence,
                    "reasoning": regime_detection.reasoning,
                    "indicators": regime_detection.indicators
                }
                
        except Exception as e:
            logger.error(f"Regime analysis error: {e}")
            return {"type": "error", "regime": "unknown", "confidence": 0.0, "reasoning": str(e)}
    
    async def _analyze_institutional_flow(self, symbol: str, market_data: Dict[str, Any], live_metrics: Optional[Dict[str, Any]], db_session) -> Dict[str, Any]:
        """Analyze institutional flow using SmartMoneyEngine"""
        try:
            institutional_signal = await self.smart_money_engine.analyze_institutional_flow(
                symbol, db_session, live_metrics
            )
            
            return {
                "signal": institutional_signal.signal,
                "confidence": institutional_signal.confidence,
                "direction": institutional_signal.direction,
                "strength": institutional_signal.strength,
                "reasoning": institutional_signal.reasoning,
                "metrics": institutional_signal.metrics
            }
            
        except Exception as e:
            logger.error(f"Institutional flow analysis error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0.0, "reasoning": str(e), "metrics": {}}
    
    async def _calculate_probabilities(self, symbol: str, market_data: Dict[str, Any], regime_analysis: Dict[str, Any], institutional_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate outcome probabilities using ProbabilityEngine"""
        try:
            # Combine features from multiple analyses
            combined_features = {
                "regime": regime_analysis.get("regime", "unknown"),
                "regime_confidence": regime_analysis.get("confidence", 0.0),
                "institutional_signal": institutional_analysis.get("signal", "NEUTRAL"),
                "institutional_confidence": institutional_analysis.get("confidence", 0.0),
                "market_data": market_data
            }
            
            # Calculate probabilities
            probabilities = await self.probability_engine.calculate_outcome_probabilities(symbol, combined_features)
            
            return {
                "bullish_probability": probabilities.get("bullish", 0.33),
                "bearish_probability": probabilities.get("bearish", 0.33),
                "neutral_probability": probabilities.get("neutral", 0.34),
                "expected_return": probabilities.get("expected_return", 0.0),
                "confidence": probabilities.get("confidence", 0.5),
                "reasoning": probabilities.get("reasoning", "Insufficient data")
            }
            
        except Exception as e:
            logger.error(f"Probability calculation error: {e}")
            return {
                "bullish_probability": 0.33,
                "bearish_probability": 0.33,
                "neutral_probability": 0.34,
                "expected_return": 0.0,
                "confidence": 0.0,
                "reasoning": str(e)
            }
    
    async def _generate_strategies(self, symbol: str, regime_analysis: Dict[str, Any], institutional_analysis: Dict[str, Any], probability_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategy recommendations using StrategyEngine"""
        try:
            # Combine analysis results for strategy input
            strategy_context = {
                "regime": regime_analysis.get("regime", "unknown"),
                "regime_stability": regime_analysis.get("stability", 50),
                "institutional_bias": institutional_analysis.get("signal", "NEUTRAL"),
                "institutional_strength": institutional_analysis.get("strength", 0.0),
                "bullish_probability": probability_analysis.get("bullish_probability", 0.33),
                "bearish_probability": probability_analysis.get("bearish_probability", 0.33),
                "expected_return": probability_analysis.get("expected_return", 0.0)
            }
            
            # Generate strategies
            strategies = await self.strategy_engine.generate_strategies(symbol, strategy_context)
            
            return {
                "recommended_strategies": strategies.get("strategies", []),
                "primary_strategy": strategies.get("primary", "HOLD"),
                "strategy_confidence": strategies.get("confidence", 0.5),
                "entry_conditions": strategies.get("entry_conditions", []),
                "exit_conditions": strategies.get("exit_conditions", []),
                "reasoning": strategies.get("reasoning", "No clear strategy identified")
            }
            
        except Exception as e:
            logger.error(f"Strategy generation error: {e}")
            return {
                "recommended_strategies": [],
                "primary_strategy": "HOLD",
                "strategy_confidence": 0.0,
                "entry_conditions": [],
                "exit_conditions": [],
                "reasoning": str(e)
            }
    
    async def _assess_risk(self, symbol: str, market_data: Dict[str, Any], strategy_recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk using RiskEngine"""
        try:
            risk_context = {
                "symbol": symbol,
                "current_price": market_data.get("spot", 0),
                "volatility": market_data.get("volatility", 0.2),
                "strategy": strategy_recommendations.get("primary_strategy", "HOLD"),
                "strategy_confidence": strategy_recommendations.get("strategy_confidence", 0.5)
            }
            
            risk_assessment = await self.risk_engine.assess_position_risk(risk_context)
            
            return {
                "risk_score": risk_assessment.get("risk_score", 0.5),
                "position_size": risk_assessment.get("position_size", 0.0),
                "stop_loss": risk_assessment.get("stop_loss"),
                "max_loss": risk_assessment.get("max_loss", 0.0),
                "risk_factors": risk_assessment.get("risk_factors", []),
                "risk_level": risk_assessment.get("risk_level", "medium"),
                "reasoning": risk_assessment.get("reasoning", "Standard risk assessment")
            }
            
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            return {
                "risk_score": 0.5,
                "position_size": 0.0,
                "stop_loss": None,
                "max_loss": 0.0,
                "risk_factors": [],
                "risk_level": "high",
                "reasoning": str(e)
            }
    
    async def _apply_learning(self, symbol: str, regime_analysis: Dict[str, Any], institutional_analysis: Dict[str, Any], probability_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Apply learning insights using LearningEngine"""
        try:
            learning_context = {
                "regime": regime_analysis.get("regime", "unknown"),
                "institutional_signal": institutional_analysis.get("signal", "NEUTRAL"),
                "probabilities": probability_analysis,
                "timestamp": datetime.now(timezone.utc)
            }
            
            learning_insights = await self.learning_engine.get_insights(symbol, learning_context)
            
            return {
                "historical_performance": learning_insights.get("performance", {}),
                "pattern_recognition": learning_insights.get("patterns", []),
                "adaptation_score": learning_insights.get("adaptation_score", 0.5),
                "confidence_adjustment": learning_insights.get("confidence_adjustment", 0.0),
                "recommendations": learning_insights.get("recommendations", []),
                "reasoning": learning_insights.get("reasoning", "No learning data available")
            }
            
        except Exception as e:
            logger.error(f"Learning application error: {e}")
            return {
                "historical_performance": {},
                "pattern_recognition": [],
                "adaptation_score": 0.5,
                "confidence_adjustment": 0.0,
                "recommendations": [],
                "reasoning": str(e)
            }
    
    def _synthesize_signal(
        self,
        symbol: str,
        regime_analysis: Dict[str, Any],
        institutional_analysis: Dict[str, Any],
        probability_analysis: Dict[str, Any],
        strategy_recommendations: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        learning_insights: Dict[str, Any]
    ) -> AISignal:
        """Synthesize final trading signal from all analyses"""
        try:
            # Determine signal type based on weighted analysis
            bullish_weight = (
                probability_analysis.get("bullish_probability", 0.33) * 0.4 +
                (1.0 if institutional_analysis.get("signal") == "BULLISH" else 0.0) * 0.3 +
                (1.0 if strategy_recommendations.get("primary_strategy") in ["LONG", "BUY"] else 0.0) * 0.3
            )
            
            bearish_weight = (
                probability_analysis.get("bearish_probability", 0.33) * 0.4 +
                (1.0 if institutional_analysis.get("signal") == "BEARISH" else 0.0) * 0.3 +
                (1.0 if strategy_recommendations.get("primary_strategy") in ["SHORT", "SELL"] else 0.0) * 0.3
            )
            
            # Determine signal type
            if bullish_weight > bearish_weight and bullish_weight > 0.6:
                signal_type = SignalType.BULLISH
            elif bearish_weight > bullish_weight and bearish_weight > 0.6:
                signal_type = SignalType.BEARISH
            else:
                signal_type = SignalType.NEUTRAL
            
            # Calculate overall confidence
            base_confidence = max(bullish_weight, bearish_weight)
            learning_adjustment = learning_insights.get("confidence_adjustment", 0.0)
            confidence = min(1.0, max(0.0, base_confidence + learning_adjustment))
            
            # Extract key metrics
            current_price = regime_analysis.get("indicators", {}).get("spot", 0)
            stop_loss = risk_assessment.get("stop_loss")
            position_size = risk_assessment.get("position_size", 0.0)
            
            # Calculate target based on expected return
            expected_return = probability_analysis.get("expected_return", 0.0)
            if signal_type == SignalType.BULLISH and expected_return > 0:
                target_price = current_price * (1 + expected_return)
            elif signal_type == SignalType.BEARISH and expected_return < 0:
                target_price = current_price * (1 + expected_return)
            else:
                target_price = None
            
            # Calculate risk-reward ratio
            if stop_loss and target_price and current_price:
                if signal_type == SignalType.BULLISH:
                    risk = current_price - stop_loss
                    reward = target_price - current_price
                elif signal_type == SignalType.BEARISH:
                    risk = stop_loss - current_price
                    reward = current_price - target_price
                else:
                    risk = reward = 0
                
                risk_reward_ratio = reward / risk if risk > 0 else 0
            else:
                risk_reward_ratio = 0
            
            # Compile reasoning
            reasoning = [
                f"Regime: {regime_analysis.get('regime', 'unknown')} ({regime_analysis.get('confidence', 0):.1%} confidence)",
                f"Institutional bias: {institutional_analysis.get('signal', 'NEUTRAL')} ({institutional_analysis.get('confidence', 0):.1%} confidence)",
                f"Probability: {probability_analysis.get('bullish_probability', 0):.1%} bullish, {probability_analysis.get('bearish_probability', 0):.1%} bearish",
                f"Strategy: {strategy_recommendations.get('primary_strategy', 'HOLD')}",
                f"Risk level: {risk_assessment.get('risk_level', 'medium')}",
                f"Learning adjustment: {learning_adjustment:+.2f}"
            ]
            
            # Add strategy recommendations
            strategy_recommendations_list = strategy_recommendations.get("recommended_strategies", [])
            
            # Compile risk assessment
            risk_factors = risk_assessment.get("risk_factors", [])
            
            return AISignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                entry_price=current_price if signal_type != SignalType.NEUTRAL else None,
                stop_loss=stop_loss,
                target_price=target_price,
                position_size=position_size,
                reasoning=reasoning,
                risk_reward_ratio=risk_reward_ratio,
                regime=regime_analysis.get("regime", "unknown"),
                institutional_bias=institutional_analysis.get("signal", "NEUTRAL"),
                probability_score=probability_analysis.get("bullish_probability", 0.33) if signal_type == SignalType.BULLISH else probability_analysis.get("bearish_probability", 0.33),
                risk_assessment={
                    "risk_score": risk_assessment.get("risk_score", 0.5),
                    "risk_level": risk_assessment.get("risk_level", "medium"),
                    "max_loss": risk_assessment.get("max_loss", 0.0),
                    "risk_factors": risk_factors
                },
                strategy_recommendations=strategy_recommendations_list
            )
            
        except Exception as e:
            logger.error(f"Signal synthesis error: {e}")
            return self._create_default_signal(symbol)
    
    def _create_default_signal(self, symbol: str) -> AISignal:
        """Create default signal for error cases"""
        return AISignal(
            symbol=symbol,
            signal_type=SignalType.NEUTRAL,
            confidence=0.0,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            position_size=0.0,
            reasoning=["Error in signal generation - defaulting to neutral"],
            risk_reward_ratio=0.0,
            regime="unknown",
            institutional_bias="NEUTRAL",
            probability_score=0.5,
            risk_assessment={
                "risk_score": 0.5,
                "risk_level": "high",
                "max_loss": 0.0,
                "risk_factors": ["Analysis error"]
            },
            strategy_recommendations=["HOLD"]
        )
    
    def _cache_analysis(self, symbol: str, analysis: Dict[str, Any]):
        """Cache analysis results"""
        self.analysis_cache[symbol] = {
            "data": analysis,
            "timestamp": datetime.now(timezone.utc)
        }
    
    def get_cached_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis if valid"""
        if symbol in self.analysis_cache:
            cached = self.analysis_cache[symbol]
            age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
            if age < self.cache_ttl:
                return cached["data"]
        return None
    
    async def get_market_overview(self, symbols: List[str], market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Get market overview for multiple symbols"""
        overview = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals": {},
            "market_sentiment": {"bullish": 0, "bearish": 0, "neutral": 0},
            "average_confidence": 0.0,
            "high_conviction_signals": []
        }
        
        for symbol in symbols:
            if symbol in market_data:
                signal = await self.generate_trading_signal(symbol, market_data[symbol])
                overview["signals"][symbol] = {
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "regime": signal.regime,
                    "institutional_bias": signal.institutional_bias
                }
                
                # Update sentiment counts
                if signal.signal_type == SignalType.BULLISH:
                    overview["market_sentiment"]["bullish"] += 1
                elif signal.signal_type == SignalType.BEARISH:
                    overview["market_sentiment"]["bearish"] += 1
                else:
                    overview["market_sentiment"]["neutral"] += 1
                
                # Track high conviction signals
                if signal.confidence > 0.8 and signal.signal_type != SignalType.NEUTRAL:
                    overview["high_conviction_signals"].append({
                        "symbol": symbol,
                        "signal_type": signal.signal_type.value,
                        "confidence": signal.confidence,
                        "risk_reward_ratio": signal.risk_reward_ratio
                    })
        
        # Calculate average confidence
        if overview["signals"]:
            confidences = [s["confidence"] for s in overview["signals"].values()]
            overview["average_confidence"] = sum(confidences) / len(confidences)
        
        return overview
    
    def format_signal_for_frontend(self, signal: AISignal) -> Dict[str, Any]:
        """Format AI signal for frontend consumption"""
        return {
            "symbol": signal.symbol,
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "target_price": signal.target_price,
            "position_size": signal.position_size,
            "reasoning": signal.reasoning,
            "risk_reward_ratio": signal.risk_reward_ratio,
            "regime": signal.regime,
            "institutional_bias": signal.institutional_bias,
            "probability_score": signal.probability_score,
            "risk_assessment": signal.risk_assessment,
            "strategy_recommendations": signal.strategy_recommendations,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
