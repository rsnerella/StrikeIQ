"""
Data Foundation - Candle Normalization and Preparation
Provides normalized candle data for pattern detection with ATR normalization.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Candle:
    """Normalized candle structure"""
    bar_index: int
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # Normalized values (ATR-based)
    normalized_high: float = 0.0
    normalized_low: float = 0.0
    normalized_body: float = 0.0

class DataFoundation:
    """
    Handles candle data normalization and preparation for pattern detection.
    Implements ATR normalization for robust pattern detection across price ranges.
    """
    
    def __init__(self, max_bars: int = 200):
        self.max_bars = max_bars
        self.atr_period = 14
        
    def normalize_candles(self, raw_candles: List[Dict[str, Any]]) -> List[Candle]:
        """
        Convert raw candle data to normalized Candle objects with ATR normalization.
        
        Args:
            raw_candles: List of raw candle dictionaries
            
        Returns:
            List of normalized Candle objects
        """
        if len(raw_candles) < 20:
            logger.warning("Insufficient candles for normalization")
            return []
            
        # Take last max_bars candles
        candles = raw_candles[-self.max_bars:]
        
        # Convert to Candle objects
        normalized_candles = []
        for i, raw in enumerate(candles):
            candle = Candle(
                bar_index=i,
                timestamp=raw.get('timestamp', 0),
                open=float(raw.get('open', 0)),
                high=float(raw.get('high', 0)),
                low=float(raw.get('low', 0)),
                close=float(raw.get('close', 0)),
                volume=float(raw.get('volume', 0))
            )
            normalized_candles.append(candle)
        
        # Calculate ATR for normalization
        atr = self._calculate_atr(normalized_candles)
        
        # Apply ATR normalization
        for candle in normalized_candles:
            if atr > 0:
                candle.normalized_high = (candle.high - candle.close) / atr
                candle.normalized_low = (candle.close - candle.low) / atr
                candle.normalized_body = abs(candle.close - candle.open) / atr
        
        return normalized_candles
    
    def _calculate_atr(self, candles: List[Candle]) -> float:
        """
        Calculate Average True Range for normalization.
        
        Args:
            candles: List of Candle objects
            
        Returns:
            ATR value
        """
        if len(candles) < self.atr_period + 1:
            return 0.0
            
        # Calculate True Ranges
        true_ranges = []
        for i in range(1, len(candles)):
            prev_candle = candles[i-1]
            curr_candle = candles[i]
            
            tr1 = curr_candle.high - curr_candle.low
            tr2 = abs(curr_candle.high - prev_candle.close)
            tr3 = abs(curr_candle.low - prev_candle.close)
            
            true_ranges.append(max(tr1, tr2, tr3))
        
        # Calculate ATR using simple moving average
        if len(true_ranges) >= self.atr_period:
            atr = np.mean(true_ranges[-self.atr_period:])
            return atr
        
        return 0.0
    
    def extract_price_array(self, candles: List[Candle]) -> np.ndarray:
        """Extract close prices as numpy array"""
        return np.array([c.close for c in candles])
    
    def extract_high_array(self, candles: List[Candle]) -> np.ndarray:
        """Extract high prices as numpy array"""
        return np.array([c.high for c in candles])
    
    def extract_low_array(self, candles: List[Candle]) -> np.ndarray:
        """Extract low prices as numpy array"""
        return np.array([c.low for c in candles])
    
    def extract_volume_array(self, candles: List[Candle]) -> np.ndarray:
        """Extract volume as numpy array"""
        return np.array([c.volume for c in candles])
