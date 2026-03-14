"""
Expected Move Engine
Computes expected price movement based on spot price and implied volatility
"""

import logging

logger = logging.getLogger(__name__)

class ExpectedMoveEngine:
    """Computes expected price movement from spot and IV"""
    
    def compute(self, spot, iv):
        """
        Calculate expected move based on spot price and implied volatility
        
        Args:
            spot: Current spot price
            iv: Implied volatility (as percentage)
            
        Returns:
            Expected move value (float)
        """
        try:
            if not spot or not iv:
                return 0

            return spot * iv * 0.01

        except Exception as e:
            logger.warning(f"Expected move calculation failed: {e}")
            return 0
