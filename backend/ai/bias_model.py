"""
Institutional Bias Scoring Model for StrikeIQ
Multi-factor bias detection with confidence scoring
"""

from typing import Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class BiasResult:
    """Bias calculation result"""
    bias: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float  # 0.0 to 1.0
    score: float  # 0.0 to 1.0
    components: Dict[str, float]  # Individual component scores

class BiasModel:
    """Multi-factor bias scoring model"""
    
    def __init__(self):
        # Weight configuration
        self.gamma_weight = 0.30
        self.oi_weight = 0.25
        self.liquidity_weight = 0.25
        self.volatility_weight = 0.20
        
        logger.info("BiasModel initialized with weights: gamma=30%, oi=25%, liquidity=25%, volatility=20%")
    
    def calculate_bias(self, features) -> BiasResult:
        """Calculate market bias from features"""
        try:
            # Extract individual component scores
            gamma_bias = self.calculate_gamma_bias(features)
            oi_bias = self.calculate_oi_bias(features)
            liquidity_bias = self.calculate_liquidity_bias(features)
            volatility_bias = self.calculate_volatility_bias(features)
            
            # Weighted ensemble
            weighted_score = (
                gamma_bias * self.gamma_weight +
                oi_bias * self.oi_weight +
                liquidity_bias * self.liquidity_weight +
                volatility_bias * self.volatility_weight
            )
            
            # Determine bias direction
            if weighted_score > 0.6:
                bias = "BULLISH"
            elif weighted_score < 0.4:
                bias = "BEARISH"
            else:
                bias = "NEUTRAL"
            
            # Calculate confidence
            confidence = abs(weighted_score - 0.5) * 2
            
            return BiasResult(
                bias=bias,
                confidence=min(1.0, confidence),
                score=weighted_score,
                components={
                    'gamma': gamma_bias,
                    'oi': oi_bias,
                    'liquidity': liquidity_bias,
                    'volatility': volatility_bias
                }
            )
            
        except Exception as e:
            logger.error(f"Bias calculation failed: {e}")
            return self.get_default_bias()
    
    def calculate_gamma_bias(self, features):
        """Calculate bias from gamma exposure"""
        try:
            gex_profile = features.get('gex_profile', {})
            net_gamma = gex_profile.get('net_gamma', 0)
            gamma_flip = features.get('gamma_flip_probability', 0)
            call_wall_strength = features.get('call_wall_strength', 0)
            put_wall_strength = features.get('put_wall_strength', 0)
            
            # Gamma bias calculation
            gamma_bias = 0.5  # Neutral start
            
            # Net gamma contribution
            if net_gamma > 0:
                gamma_bias += min(0.3, net_gamma / 1000000)
            elif net_gamma < 0:
                gamma_bias -= min(0.3, abs(net_gamma) / 1000000)
            
            # Gamma flip contribution
            if gamma_flip > 0.6:
                gamma_bias += 0.1
            elif gamma_flip < 0.4:
                gamma_bias -= 0.1
            
            # Wall strength contribution
            if call_wall_strength > 0.7:
                gamma_bias += 0.1
            elif put_wall_strength > 0.7:
                gamma_bias -= 0.1
            
            return max(0.0, min(1.0, gamma_bias))
            
        except Exception as e:
            logger.error(f"Gamma bias calculation failed: {e}")
            return 0.5
    
    def calculate_oi_bias(self, features):
        """Calculate bias from OI structure"""
        try:
            pcr_trend = features.get('pcr_trend', 0)
            oi_concentration = features.get('oi_concentration', 0)
            oi_buildup_rate = features.get('oi_buildup_rate', 0)
            
            # OI bias calculation
            oi_bias = 0.5  # Neutral start
            
            # PCR trend contribution
            oi_bias += pcr_trend * 0.4
            
            # OI buildup contribution
            oi_bias += oi_buildup_rate * 0.3
            
            # Concentration adjustment (high concentration reduces confidence)
            if oi_concentration > 0.7:
                oi_bias = 0.5 + (oi_bias - 0.5) * 0.5
            
            return max(0.0, min(1.0, oi_bias))
            
        except Exception as e:
            logger.error(f"OI bias calculation failed: {e}")
            return 0.5
    
    def calculate_liquidity_bias(self, features):
        """Calculate bias from liquidity features"""
        try:
            liquidity_vacuum = features.get('liquidity_vacuum', 0)
            order_flow_imbalance = features.get('order_flow_imbalance', 0)
            market_impact = features.get('market_impact', 0)
            
            # Liquidity bias calculation
            liquidity_bias = 0.5  # Neutral start
            
            # Liquidity vacuum contribution
            liquidity_bias += liquidity_vacuum * 0.4
            
            # Order flow contribution
            liquidity_bias += order_flow_imbalance * 0.4
            
            # Market impact adjustment
            if market_impact > 0.7:
                # High impact reduces confidence
                liquidity_bias = 0.5 + (liquidity_bias - 0.5) * 0.7
            
            return max(0.0, min(1.0, liquidity_bias))
            
        except Exception as e:
            logger.error(f"Liquidity bias calculation failed: {e}")
            return 0.5
    
    def calculate_volatility_bias(self, features):
        """Calculate bias from volatility regime"""
        try:
            iv_regime = features.get('iv_regime', 'MEDIUM')
            volatility_expansion = features.get('volatility_expansion', 0)
            term_structure = features.get('term_structure', 0)
            
            # Volatility bias calculation
            volatility_bias = 0.5  # Neutral start
            
            # IV regime contribution
            if iv_regime == 'LOW':
                volatility_bias += 0.1  # Favorable for options buying
            elif iv_regime == 'HIGH':
                volatility_bias -= 0.1  # Unfavorable for options buying
            
            # Volatility expansion contribution
            if volatility_expansion > 5:
                volatility_bias += 0.1
            elif volatility_expansion < -5:
                volatility_bias -= 0.1
            
            # Term structure contribution
            if term_structure > 0.1:
                volatility_bias += 0.05
            elif term_structure < -0.1:
                volatility_bias -= 0.05
            
            return max(0.0, min(1.0, volatility_bias))
            
        except Exception as e:
            logger.error(f"Volatility bias calculation failed: {e}")
            return 0.5
    
    def get_default_bias(self) -> BiasResult:
        """Default bias for error cases"""
        return BiasResult(
            bias="NEUTRAL",
            confidence=0.0,
            score=0.5,
            components={
                'gamma': 0.5,
                'oi': 0.5,
                'liquidity': 0.5,
                'volatility': 0.5
            }
        )
