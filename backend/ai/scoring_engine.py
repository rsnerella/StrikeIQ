"""
Simple Scoring Engine for StrikeIQ
Probabilistic trade scoring to replace hard NO_TRADE filtering
"""

import logging

logger = logging.getLogger(__name__)

class SimpleScoreEngine:
    """Minimal probabilistic scoring engine"""
    
    def __init__(self):
        logger.info("SimpleScoreEngine initialized")
    
    def score(self, snap) -> float:
        """
        Calculate trade score from market data
        Returns: -1.0 (strong bearish) to 1.0 (strong bullish)
        """
        try:
            score = 0.0
            
            # OI momentum (enhanced calculation)
            put_oi_change = getattr(snap, "put_oi_change_pct", 0) or 0
            call_oi_change = getattr(snap, "call_oi_change_pct", 0) or 0
            oi_momentum = put_oi_change - call_oi_change
            score += max(-1, min(1, oi_momentum / 5)) * 0.3  # Increased weight
            
            # Price momentum (enhanced)
            vwap_dev = getattr(snap, "vwap_deviation_pct", 0) or 0
            price_momentum = max(-1, min(1, vwap_dev / 1.5))  # More sensitive
            score += price_momentum * 0.3  # Increased weight
            
            # PCR influence
            pcr = getattr(snap, "pcr", 1.0) or 1.0
            if pcr > 1.3:  # Strong put bias
                score -= 0.2
            elif pcr < 0.7:  # Strong call bias
                score += 0.2
            else:  # Neutral PCR
                score += (1.0 - pcr) * 0.1  # Linear adjustment
            
            # Volume analysis
            vol = getattr(snap, "volume_vs_avg_ratio", 1) or 1
            if vol > 1.3:  # High volume
                score += 0.15
            elif vol < 0.7:  # Low volume
                score -= 0.1
            
            # Gamma exposure (if available)
            net_gex = getattr(snap, "net_gex", 0) or 0
            if net_gex > 100000:  # Strong positive gamma
                score += 0.1
            elif net_gex < -100000:  # Strong negative gamma
                score -= 0.1
            
            final_score = max(-1, min(1, score))
            
            # Debug logging
            print("[SCORE DEBUG]", {
                'oi_momentum': oi_momentum,
                'price_momentum': price_momentum,
                'pcr': pcr,
                'volume_ratio': vol,
                'net_gex': net_gex,
                'raw_score': score,
                'final_score': final_score
            })
            
            return final_score
            
        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            return 0.0
