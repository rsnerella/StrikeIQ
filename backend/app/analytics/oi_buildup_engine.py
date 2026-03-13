"""
OI Buildup Engine - Detects option market positioning based on price and Open Interest change.

Classification logic:
PRICE ↑  +  OI ↑  → LONG BUILDUP
PRICE ↓  +  OI ↑  → SHORT BUILDUP
PRICE ↑  +  OI ↓  → SHORT COVERING
PRICE ↓  +  OI ↓  → LONG UNWINDING
"""

import logging

logger = logging.getLogger(__name__)


class OIBuildupEngine:
    """
    Detects option market positioning based on price and Open Interest changes.
    """
    
    def __init__(self):
        """Initialize the OI Buildup Engine."""
        self.previous_data = {}
        logger.info("OI Buildup Engine initialized")
    
    def detect(self, instrument_key: str, price: float, oi: int):
        """
        Detect OI buildup signal based on price and Open Interest changes.
        
        Args:
            instrument_key: Option instrument key (e.g., 'NSE_FO|NIFTY24MAR24600CE')
            price: Current price of the option
            oi: Current Open Interest of the option
            
        Returns:
            str: Signal type (LONG_BUILDUP, SHORT_BUILDUP, SHORT_COVERING, LONG_UNWINDING)
        """
        prev = self.previous_data.get(instrument_key)
        
        if not prev:
            # First tick for this instrument
            self.previous_data[instrument_key] = (price, oi)
            return None
        
        prev_price, prev_oi = prev
        
        price_change = price - prev_price
        oi_change = oi - prev_oi
        
        signal = None
        
        # Use small epsilon to handle floating point precision
        epsilon = 0.001
        
        if price_change > epsilon and oi_change > 0:
            signal = "LONG_BUILDUP"
            
        elif price_change < -epsilon and oi_change > 0:
            signal = "SHORT_BUILDUP"
            
        elif price_change > epsilon and oi_change < 0:
            signal = "SHORT_COVERING"
            
        elif price_change < -epsilon and oi_change < 0:
            signal = "LONG_UNWINDING"
        
        # Update previous data
        self.previous_data[instrument_key] = (price, oi)
        
        if signal:
            logger.debug(
                f"OI Signal: {instrument_key} | Price: {price_change:+.2f} | OI: {oi_change:+d} | Signal: {signal}"
            )
        
        return signal
