"""
Strategy Decision Engine for StrikeIQ
Multi-strategy selection based on market regime and bias
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class StrategyDecision:
    """Strategy decision result"""
    strategy: str
    regime: str
    bias_confidence: float
    execution_probability: float
    reasoning: list[str]

class StrategyDecisionEngine:
    """Multi-strategy decision engine"""
    
    def __init__(self):
        self.strategies = {
            'TRENDING_BULLISH': self.execute_trending_bullish,
            'TRENDING_BEARISH': self.execute_trending_bearish,
            'MEAN_REVERSION': self.execute_mean_reversion,
            'BREAKOUT': self.execute_breakout,
            'NO_TRADE': self.execute_no_trade
        }
        
        logger.info("StrategyDecisionEngine initialized")
    
    def decide_strategy(self, bias_result, features) -> StrategyDecision:
        """Decide optimal strategy based on bias and features"""
        try:
            # Classify market regime
            regime = self.classify_market_regime(features)
            
            # Strategy selection logic
            if bias_result.confidence < 0.65:
                strategy = 'NO_TRADE'
                reasoning = ["Low confidence bias", "Insufficient signal strength"]
            elif bias_result.bias == 'BULLISH':
                if regime == 'TRENDING':
                    strategy = 'TRENDING_BULLISH'
                    reasoning = ["Strong bullish bias in trending market", "Momentum play"]
                elif regime == 'RANGING':
                    strategy = 'MEAN_REVERSION'
                    reasoning = ["Bullish bias in ranging market", "Potential reversal to upside"]
                elif regime == 'BREAKOUT':
                    strategy = 'BREAKOUT'
                    reasoning = ["Bullish bias with breakout potential", "High momentum setup"]
                else:
                    strategy = 'NO_TRADE'
                    reasoning = ["Unclear regime", "Avoiding trade"]
            elif bias_result.bias == 'BEARISH':
                if regime == 'TRENDING':
                    strategy = 'TRENDING_BEARISH'
                    reasoning = ["Strong bearish bias in trending market", "Momentum play"]
                elif regime == 'RANGING':
                    strategy = 'MEAN_REVERSION'
                    reasoning = ["Bearish bias in ranging market", "Potential reversal to downside"]
                elif regime == 'BREAKOUT':
                    strategy = 'BREAKOUT'
                    reasoning = ["Bearish bias with breakout potential", "High momentum setup"]
                else:
                    strategy = 'NO_TRADE'
                    reasoning = ["Unclear regime", "Avoiding trade"]
            else:
                strategy = 'NO_TRADE'
                reasoning = ["Neutral bias", "No clear directional edge"]
            
            # Calculate execution probability
            execution_probability = self.calculate_execution_probability(strategy, bias_result, regime)
            
            return StrategyDecision(
                strategy=strategy,
                regime=regime,
                bias_confidence=bias_result.confidence,
                execution_probability=execution_probability,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Strategy decision failed: {e}")
            return self.get_default_strategy()
    
    def classify_market_regime(self, features) -> str:
        """Classify market regime from features"""
        try:
            # Volatility regime
            iv_regime = features.get('iv_regime', 'MEDIUM')
            
            # Gamma flip probability
            gamma_flip = features.get('gamma_flip_probability', 0)
            
            # Liquidity vacuum
            liquidity_vacuum = features.get('liquidity_vacuum', 0)
            
            # OI concentration
            oi_concentration = features.get('oi_concentration', 0)
            
            # Regime classification logic
            if iv_regime == 'HIGH' and gamma_flip > 0.7:
                return 'BREAKOUT'
            elif iv_regime == 'LOW' and liquidity_vacuum < 0.3:
                return 'RANGING'
            elif abs(gamma_flip - 0.5) < 0.2 and oi_concentration > 0.6:
                return 'TRENDING'
            else:
                return 'RANGING'
                
        except Exception as e:
            logger.error(f"Regime classification failed: {e}")
            return 'RANGING'
    
    def calculate_execution_probability(self, strategy, bias_result, regime) -> float:
        """Calculate probability of successful execution"""
        base_probability = 0.5
        
        # Strategy-specific adjustments
        if strategy == 'TRENDING_BULLISH' or strategy == 'TRENDING_BEARISH':
            if regime == 'TRENDING':
                base_probability += 0.3
            else:
                base_probability -= 0.2
        elif strategy == 'MEAN_REVERSION':
            if regime == 'RANGING':
                base_probability += 0.3
            else:
                base_probability -= 0.1
        elif strategy == 'BREAKOUT':
            if regime == 'BREAKOUT':
                base_probability += 0.4
            else:
                base_probability -= 0.3
        
        # Confidence adjustment
        base_probability += (bias_result.confidence - 0.5) * 0.4
        
        return max(0.1, min(0.9, base_probability))
    
    def execute_trending_bullish(self, features) -> Dict[str, Any]:
        """Execute trending bullish strategy"""
        return {
            'action': 'BUY_CE',
            'conviction': 0.8,
            'holding_period': '30-60 minutes',
            'risk_level': 'MEDIUM'
        }
    
    def execute_trending_bearish(self, features) -> Dict[str, Any]:
        """Execute trending bearish strategy"""
        return {
            'action': 'BUY_PE',
            'conviction': 0.8,
            'holding_period': '30-60 minutes',
            'risk_level': 'MEDIUM'
        }
    
    def execute_mean_reversion(self, features) -> Dict[str, Any]:
        """Execute mean reversion strategy"""
        return {
            'action': 'COUNTER_TREND',
            'conviction': 0.6,
            'holding_period': '15-30 minutes',
            'risk_level': 'HIGH'
        }
    
    def execute_breakout(self, features) -> Dict[str, Any]:
        """Execute breakout strategy"""
        return {
            'action': 'MOMENTUM',
            'conviction': 0.9,
            'holding_period': '15-45 minutes',
            'risk_level': 'HIGH'
        }
    
    def execute_no_trade(self, features) -> Dict[str, Any]:
        """Execute no trade strategy"""
        return {
            'action': 'NO_TRADE',
            'conviction': 0.0,
            'holding_period': 'N/A',
            'risk_level': 'NONE'
        }
    
    def get_default_strategy(self) -> StrategyDecision:
        """Default strategy for error cases"""
        return StrategyDecision(
            strategy='NO_TRADE',
            regime='RANGING',
            bias_confidence=0.0,
            execution_probability=0.0,
            reasoning=['Error in strategy decision', 'No trade executed']
        )
