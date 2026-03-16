"""
Swing Detector - Identifies Swing Highs and Swing Lows
Implements fractal-based swing point detection with configurable parameters.
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

from .data_foundation import Candle

logger = logging.getLogger(__name__)

@dataclass
class SwingPoint:
    """Represents a swing high or swing low"""
    bar_index: int
    price: float
    point_type: str  # "HIGH" or "LOW"
    strength: float  # 0.0 to 1.0
    timestamp: float

class SwingDetector:
    """
    Detects swing highs and swing lows using fractal analysis.
    Higher strength values indicate more significant swing points.
    """
    
    def __init__(self, left_bars: int = 5, right_bars: int = 5, min_strength: float = 0.3):
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.min_strength = min_strength
        
    def detect_swings(self, candles: List[Candle]) -> List[SwingPoint]:
        """
        Detect swing highs and lows in candle data.
        
        Args:
            candles: List of normalized Candle objects
            
        Returns:
            List of SwingPoint objects
        """
        if len(candles) < self.left_bars + self.right_bars + 1:
            logger.warning("Insufficient candles for swing detection")
            return []
        
        swing_points = []
        
        # Detect swing highs
        for i in range(self.left_bars, len(candles) - self.right_bars):
            if self._is_swing_high(candles, i):
                strength = self._calculate_swing_strength(candles, i, "HIGH")
                if strength >= self.min_strength:
                    swing_point = SwingPoint(
                        bar_index=i,
                        price=candles[i].high,
                        point_type="HIGH",
                        strength=strength,
                        timestamp=candles[i].timestamp
                    )
                    swing_points.append(swing_point)
        
        # Detect swing lows
        for i in range(self.left_bars, len(candles) - self.right_bars):
            if self._is_swing_low(candles, i):
                strength = self._calculate_swing_strength(candles, i, "LOW")
                if strength >= self.min_strength:
                    swing_point = SwingPoint(
                        bar_index=i,
                        price=candles[i].low,
                        point_type="LOW",
                        strength=strength,
                        timestamp=candles[i].timestamp
                    )
                    swing_points.append(swing_point)
        
        # Sort by bar index
        swing_points.sort(key=lambda x: x.bar_index)
        
        return swing_points
    
    def _is_swing_high(self, candles: List[Candle], index: int) -> bool:
        """Check if candle at index is a swing high"""
        current_high = candles[index].high
        
        # Check left bars
        for i in range(index - self.left_bars, index):
            if candles[i].high >= current_high:
                return False
        
        # Check right bars
        for i in range(index + 1, index + self.right_bars + 1):
            if candles[i].high >= current_high:
                return False
        
        return True
    
    def _is_swing_low(self, candles: List[Candle], index: int) -> bool:
        """Check if candle at index is a swing low"""
        current_low = candles[index].low
        
        # Check left bars
        for i in range(index - self.left_bars, index):
            if candles[i].low <= current_low:
                return False
        
        # Check right bars
        for i in range(index + 1, index + self.right_bars + 1):
            if candles[i].low <= current_low:
                return False
        
        return True
    
    def _calculate_swing_strength(self, candles: List[Candle], index: int, point_type: str) -> float:
        """
        Calculate strength of swing point based on price differential.
        
        Args:
            candles: List of Candle objects
            index: Index of swing point
            point_type: "HIGH" or "LOW"
            
        Returns:
            Strength value between 0.0 and 1.0
        """
        if point_type == "HIGH":
            current_price = candles[index].high
            # Find lowest point in the window
            window_start = max(0, index - self.left_bars)
            window_end = min(len(candles), index + self.right_bars + 1)
            
            lowest_price = min(candles[i].low for i in range(window_start, window_end) if i != index)
            price_range = current_price - lowest_price
            
        else:  # LOW
            current_price = candles[index].low
            # Find highest point in the window
            window_start = max(0, index - self.left_bars)
            window_end = min(len(candles), index + self.right_bars + 1)
            
            highest_price = max(candles[i].high for i in range(window_start, window_end) if i != index)
            price_range = highest_price - current_price
        
        # Normalize strength using ATR from the candle
        atr = max(candles[index].normalized_high, candles[index].normalized_low, 0.001)
        strength = min(1.0, price_range / (atr * candles[index].close))
        
        return strength
    
    def get_recent_swings(self, swing_points: List[SwingPoint], count: int = 10) -> List[SwingPoint]:
        """Get the most recent swing points"""
        return swing_points[-count:] if len(swing_points) >= count else swing_points
    
    def get_swing_highs(self, swing_points: List[SwingPoint]) -> List[SwingPoint]:
        """Filter swing points to get only highs"""
        return [sp for sp in swing_points if sp.point_type == "HIGH"]
    
    def get_swing_lows(self, swing_points: List[SwingPoint]) -> List[SwingPoint]:
        """Filter swing points to get only lows"""
        return [sp for sp in swing_points if sp.point_type == "LOW"]
