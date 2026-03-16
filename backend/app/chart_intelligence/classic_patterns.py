"""
Classic Patterns Detector - Double Top/Bottom, Trend Channels, Liquidity Sweeps
Implements traditional technical analysis patterns with confidence scoring.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from .data_foundation import Candle
from .swing_detector import SwingPoint

logger = logging.getLogger(__name__)

@dataclass
class DoubleTop:
    """Double Top pattern"""
    left_peak: int
    right_peak: int
    neckline: float
    peak_price: float
    confidence: float
    volume_confirmation: bool

@dataclass
class DoubleBottom:
    """Double Bottom pattern"""
    left_trough: int
    right_trough: int
    neckline: float
    trough_price: float
    confidence: float
    volume_confirmation: bool

@dataclass
class TrendChannel:
    """Trend Channel pattern"""
    start_bar: int
    end_bar: int
    upper_line: List[Tuple[int, float]]
    lower_line: List[Tuple[int, float]]
    channel_type: str  # "ASCENDING", "DESCENDING", "HORIZONTAL"
    strength: float
    touches: int

@dataclass
class LiquiditySweep:
    """Liquidity Sweep pattern"""
    sweep_bar: int
    sweep_price: float
    target_level: float
    sweep_type: str  # "BUY_SIDE" or "SELL_SIDE"
    liquidity_level: str  # "SWING_HIGH" or "SWING_LOW"
    confidence: float

@dataclass
class EqualHighsLows:
    """Equal Highs/Lows pattern"""
    bars: List[int]
    price_level: float
    pattern_type: str  # "EQUAL_HIGHS" or "EQUAL_LOWS"
    tolerance: float
    confidence: float

class ClassicPatterns:
    """
    Detects classic technical analysis patterns including double tops/bottoms,
    trend channels, liquidity sweeps, and equal highs/lows.
    """
    
    def __init__(self):
        self.price_tolerance = 0.005  # 0.5% tolerance for equal highs/lows
        self.min_channel_touches = 3
        self.min_sweep_distance = 0.002  # 0.2% minimum sweep distance
        
    def detect_double_tops(self, candles: List[Candle], swing_highs: List[SwingPoint]) -> List[DoubleTop]:
        """
        Detect Double Top patterns.
        
        Args:
            candles: List of Candle objects
            swing_highs: List of swing high points
            
        Returns:
            List of DoubleTop patterns
        """
        double_tops = []
        
        if len(swing_highs) < 2:
            return double_tops
        
        # Check pairs of swing highs
        for i in range(len(swing_highs) - 1):
            left_peak = swing_highs[i]
            right_peak = swing_highs[i + 1]
            
            # Check if peaks are at similar price levels
            price_diff = abs(left_peak.price - right_peak.price) / left_peak.price
            if price_diff > self.price_tolerance:
                continue
            
            # Check time between peaks (not too close, not too far)
            bar_distance = right_peak.bar_index - left_peak.bar_index
            if bar_distance < 5 or bar_distance > 50:
                continue
            
            # Find neckline (lowest low between peaks)
            neckline = min(candles[j].low for j in range(left_peak.bar_index, right_peak.bar_index + 1))
            
            # Calculate confidence based on symmetry and volume
            confidence = self._calculate_double_top_confidence(candles, left_peak, right_peak, neckline)
            
            if confidence > 0.6:
                pattern = DoubleTop(
                    left_peak=left_peak.bar_index,
                    right_peak=right_peak.bar_index,
                    neckline=neckline,
                    peak_price=(left_peak.price + right_peak.price) / 2,
                    confidence=confidence,
                    volume_confirmation=self._check_volume_confirmation(candles, left_peak.bar_index, right_peak.bar_index)
                )
                double_tops.append(pattern)
        
        return double_tops
    
    def detect_double_bottoms(self, candles: List[Candle], swing_lows: List[SwingPoint]) -> List[DoubleBottom]:
        """
        Detect Double Bottom patterns.
        
        Args:
            candles: List of Candle objects
            swing_lows: List of swing low points
            
        Returns:
            List of DoubleBottom patterns
        """
        double_bottoms = []
        
        if len(swing_lows) < 2:
            return double_bottoms
        
        # Check pairs of swing lows
        for i in range(len(swing_lows) - 1):
            left_trough = swing_lows[i]
            right_trough = swing_lows[i + 1]
            
            # Check if troughs are at similar price levels
            price_diff = abs(left_trough.price - right_trough.price) / left_trough.price
            if price_diff > self.price_tolerance:
                continue
            
            # Check time between troughs
            bar_distance = right_trough.bar_index - left_trough.bar_index
            if bar_distance < 5 or bar_distance > 50:
                continue
            
            # Find neckline (highest high between troughs)
            neckline = max(candles[j].high for j in range(left_trough.bar_index, right_trough.bar_index + 1))
            
            # Calculate confidence
            confidence = self._calculate_double_bottom_confidence(candles, left_trough, right_trough, neckline)
            
            if confidence > 0.6:
                pattern = DoubleBottom(
                    left_trough=left_trough.bar_index,
                    right_trough=right_trough.bar_index,
                    neckline=neckline,
                    trough_price=(left_trough.price + right_trough.price) / 2,
                    confidence=confidence,
                    volume_confirmation=self._check_volume_confirmation(candles, left_trough.bar_index, right_trough.bar_index)
                )
                double_bottoms.append(pattern)
        
        return double_bottoms
    
    def detect_trend_channels(self, candles: List[Candle]) -> List[TrendChannel]:
        """
        Detect Trend Channel patterns.
        
        Args:
            candles: List of Candle objects
            
        Returns:
            List of TrendChannel patterns
        """
        channels = []
        
        # Try different channel lengths
        for channel_length in [20, 30, 40]:
            if len(candles) < channel_length:
                continue
            
            # Analyze recent candles
            recent_candles = candles[-channel_length:]
            
            # Try to fit ascending channel
            ascending_channel = self._fit_ascending_channel(recent_candles)
            if ascending_channel and ascending_channel.strength > 0.7:
                channels.append(ascending_channel)
            
            # Try to fit descending channel
            descending_channel = self._fit_descending_channel(recent_candles)
            if descending_channel and descending_channel.strength > 0.7:
                channels.append(descending_channel)
            
            # Try to fit horizontal channel
            horizontal_channel = self._fit_horizontal_channel(recent_candles)
            if horizontal_channel and horizontal_channel.strength > 0.6:
                channels.append(horizontal_channel)
        
        return channels
    
    def detect_liquidity_sweeps(self, candles: List[Candle], swing_points: List[SwingPoint]) -> List[LiquiditySweep]:
        """
        Detect Liquidity Sweep patterns.
        
        Args:
            candles: List of Candle objects
            swing_points: List of SwingPoint objects
            
        Returns:
            List of LiquiditySweep patterns
        """
        sweeps = []
        
        if len(swing_points) < 3:
            return sweeps
        
        # Check recent candles for sweeps beyond swing points
        recent_swings = swing_points[-6:]
        
        for swing in recent_swings[:-1]:  # Exclude the most recent swing
            # Look for candles that sweep beyond the swing point
            for i in range(swing.bar_index + 1, min(swing.bar_index + 10, len(candles))):
                candle = candles[i]
                
                if swing.point_type == "HIGH":
                    # Check for sell-side liquidity sweep (above swing high)
                    if candle.high > swing.price:
                        sweep_distance = (candle.high - swing.price) / swing.price
                        if sweep_distance >= self.min_sweep_distance:
                            # Find target level (usually the opposite side)
                            target_level = self._find_sweep_target(candles, swing_points, swing, "SELL_SIDE")
                            
                            sweep = LiquiditySweep(
                                sweep_bar=i,
                                sweep_price=candle.high,
                                target_level=target_level,
                                sweep_type="SELL_SIDE",
                                liquidity_level="SWING_HIGH",
                                confidence=min(0.9, sweep_distance * 10)
                            )
                            sweeps.append(sweep)
                            break
                
                elif swing.point_type == "LOW":
                    # Check for buy-side liquidity sweep (below swing low)
                    if candle.low < swing.price:
                        sweep_distance = (swing.price - candle.low) / swing.price
                        if sweep_distance >= self.min_sweep_distance:
                            # Find target level
                            target_level = self._find_sweep_target(candles, swing_points, swing, "BUY_SIDE")
                            
                            sweep = LiquiditySweep(
                                sweep_bar=i,
                                sweep_price=candle.low,
                                target_level=target_level,
                                sweep_type="BUY_SIDE",
                                liquidity_level="SWING_LOW",
                                confidence=min(0.9, sweep_distance * 10)
                            )
                            sweeps.append(sweep)
                            break
        
        return sweeps
    
    def detect_equal_highs_lows(self, candles: List[Candle], swing_points: List[SwingPoint]) -> List[EqualHighsLows]:
        """
        Detect Equal Highs/Lows patterns.
        
        Args:
            candles: List of Candle objects
            swing_points: List of SwingPoint objects
            
        Returns:
            List of EqualHighsLows patterns
        """
        equal_patterns = []
        
        # Group swing points by type
        swing_highs = [sp for sp in swing_points if sp.point_type == "HIGH"]
        swing_lows = [sp for sp in swing_points if sp.point_type == "LOW"]
        
        # Check for equal highs
        if len(swing_highs) >= 2:
            for i in range(len(swing_highs)):
                for j in range(i + 1, len(swing_highs)):
                    price_diff = abs(swing_highs[i].price - swing_highs[j].price) / swing_highs[i].price
                    if price_diff <= self.price_tolerance:
                        # Look for more equal highs
                        equal_highs = [swing_highs[i], swing_highs[j]]
                        for k in range(j + 1, len(swing_highs)):
                            if abs(swing_highs[k].price - swing_highs[i].price) / swing_highs[i].price <= self.price_tolerance:
                                equal_highs.append(swing_highs[k])
                        
                        if len(equal_highs) >= 2:
                            pattern = EqualHighsLows(
                                bars=[sp.bar_index for sp in equal_highs],
                                price_level=sum(sp.price for sp in equal_highs) / len(equal_highs),
                                pattern_type="EQUAL_HIGHS",
                                tolerance=self.price_tolerance,
                                confidence=min(0.9, len(equal_highs) * 0.2)
                            )
                            equal_patterns.append(pattern)
        
        # Check for equal lows
        if len(swing_lows) >= 2:
            for i in range(len(swing_lows)):
                for j in range(i + 1, len(swing_lows)):
                    price_diff = abs(swing_lows[i].price - swing_lows[j].price) / swing_lows[i].price
                    if price_diff <= self.price_tolerance:
                        # Look for more equal lows
                        equal_lows = [swing_lows[i], swing_lows[j]]
                        for k in range(j + 1, len(swing_lows)):
                            if abs(swing_lows[k].price - swing_lows[i].price) / swing_lows[i].price <= self.price_tolerance:
                                equal_lows.append(swing_lows[k])
                        
                        if len(equal_lows) >= 2:
                            pattern = EqualHighsLows(
                                bars=[sp.bar_index for sp in equal_lows],
                                price_level=sum(sp.price for sp in equal_lows) / len(equal_lows),
                                pattern_type="EQUAL_LOWS",
                                tolerance=self.price_tolerance,
                                confidence=min(0.9, len(equal_lows) * 0.2)
                            )
                            equal_patterns.append(pattern)
        
        return equal_patterns
    
    def _calculate_double_top_confidence(self, candles: List[Candle], left_peak: SwingPoint, 
                                        right_peak: SwingPoint, neckline: float) -> float:
        """Calculate confidence score for double top pattern"""
        confidence = 0.0
        
        # Price symmetry (40%)
        price_symmetry = 1.0 - (abs(left_peak.price - right_peak.price) / left_peak.price)
        confidence += price_symmetry * 0.4
        
        # Time symmetry (20%)
        ideal_time_distance = 20
        actual_time_distance = right_peak.bar_index - left_peak.bar_index
        time_symmetry = 1.0 - abs(actual_time_distance - ideal_time_distance) / ideal_time_distance
        confidence += max(0, time_symmetry) * 0.2
        
        # Volume confirmation (20%)
        volume_confirmation = self._check_volume_confirmation(candles, left_peak.bar_index, right_peak.bar_index)
        confidence += (0.2 if volume_confirmation else 0.0)
        
        # Depth from neckline (20%)
        depth = (left_peak.price - neckline) / left_peak.price
        depth_score = min(1.0, depth * 20)  # Normalize depth
        confidence += depth_score * 0.2
        
        return min(1.0, confidence)
    
    def _calculate_double_bottom_confidence(self, candles: List[Candle], left_trough: SwingPoint,
                                          right_trough: SwingPoint, neckline: float) -> float:
        """Calculate confidence score for double bottom pattern"""
        confidence = 0.0
        
        # Price symmetry (40%)
        price_symmetry = 1.0 - (abs(left_trough.price - right_trough.price) / left_trough.price)
        confidence += price_symmetry * 0.4
        
        # Time symmetry (20%)
        ideal_time_distance = 20
        actual_time_distance = right_trough.bar_index - left_trough.bar_index
        time_symmetry = 1.0 - abs(actual_time_distance - ideal_time_distance) / ideal_time_distance
        confidence += max(0, time_symmetry) * 0.2
        
        # Volume confirmation (20%)
        volume_confirmation = self._check_volume_confirmation(candles, left_trough.bar_index, right_trough.bar_index)
        confidence += (0.2 if volume_confirmation else 0.0)
        
        # Height from neckline (20%)
        height = (neckline - left_trough.price) / left_trough.price
        height_score = min(1.0, height * 20)
        confidence += height_score * 0.2
        
        return min(1.0, confidence)
    
    def _check_volume_confirmation(self, candles: List[Candle], start_bar: int, end_bar: int) -> bool:
        """Check if volume confirms the pattern"""
        if start_bar >= len(candles) or end_bar >= len(candles):
            return False
        
        # Calculate average volume in the pattern
        pattern_volume = np.mean([candles[i].volume for i in range(start_bar, end_bar + 1)])
        
        # Calculate average volume before the pattern
        if start_bar > 10:
            before_volume = np.mean([candles[i].volume for i in range(start_bar - 10, start_bar)])
            return pattern_volume > before_volume * 1.2
        
        return False
    
    def _fit_ascending_channel(self, candles: List[Candle]) -> Optional[TrendChannel]:
        """Fit ascending trend channel"""
        if len(candles) < 10:
            return None
        
        # Find potential channel lines using linear regression
        bar_indices = np.array([i for i in range(len(candles))])
        highs = np.array([c.high for c in candles])
        lows = np.array([c.low for c in candles])
        
        # Fit upper line to highs
        upper_slope, upper_intercept = np.polyfit(bar_indices, highs, 1)
        upper_line = [(i, upper_slope * i + upper_intercept) for i in range(len(candles))]
        
        # Fit lower line to lows
        lower_slope, lower_intercept = np.polyfit(bar_indices, lows, 1)
        lower_line = [(i, lower_slope * i + lower_intercept) for i in range(len(candles))]
        
        # Check if this forms a valid ascending channel
        if upper_slope > 0 and lower_slope > 0:
            # Count touches
            upper_touches = sum(1 for i, (bar, price) in enumerate(upper_line) 
                              if abs(candles[i].high - price) / price < 0.01)
            lower_touches = sum(1 for i, (bar, price) in enumerate(lower_line) 
                              if abs(candles[i].low - price) / price < 0.01)
            
            total_touches = upper_touches + lower_touches
            strength = total_touches / (len(candles) * 0.3)  # Normalize
            
            if total_touches >= self.min_channel_touches:
                return TrendChannel(
                    start_bar=candles[0].bar_index,
                    end_bar=candles[-1].bar_index,
                    upper_line=upper_line,
                    lower_line=lower_line,
                    channel_type="ASCENDING",
                    strength=min(1.0, strength),
                    touches=total_touches
                )
        
        return None
    
    def _fit_descending_channel(self, candles: List[Candle]) -> Optional[TrendChannel]:
        """Fit descending trend channel"""
        if len(candles) < 10:
            return None
        
        bar_indices = np.array([i for i in range(len(candles))])
        highs = np.array([c.high for c in candles])
        lows = np.array([c.low for c in candles])
        
        # Fit upper line to highs
        upper_slope, upper_intercept = np.polyfit(bar_indices, highs, 1)
        upper_line = [(i, upper_slope * i + upper_intercept) for i in range(len(candles))]
        
        # Fit lower line to lows
        lower_slope, lower_intercept = np.polyfit(bar_indices, lows, 1)
        lower_line = [(i, lower_slope * i + lower_intercept) for i in range(len(candles))]
        
        # Check if this forms a valid descending channel
        if upper_slope < 0 and lower_slope < 0:
            # Count touches
            upper_touches = sum(1 for i, (bar, price) in enumerate(upper_line) 
                              if abs(candles[i].high - price) / price < 0.01)
            lower_touches = sum(1 for i, (bar, price) in enumerate(lower_line) 
                              if abs(candles[i].low - price) / price < 0.01)
            
            total_touches = upper_touches + lower_touches
            strength = total_touches / (len(candles) * 0.3)
            
            if total_touches >= self.min_channel_touches:
                return TrendChannel(
                    start_bar=candles[0].bar_index,
                    end_bar=candles[-1].bar_index,
                    upper_line=upper_line,
                    lower_line=lower_line,
                    channel_type="DESCENDING",
                    strength=min(1.0, strength),
                    touches=total_touches
                )
        
        return None
    
    def _fit_horizontal_channel(self, candles: List[Candle]) -> Optional[TrendChannel]:
        """Fit horizontal trend channel"""
        if len(candles) < 10:
            return None
        
        # Find support and resistance levels
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        
        resistance = np.percentile(highs, 90)
        support = np.percentile(lows, 10)
        
        # Count touches
        resistance_touches = sum(1 for c in candles if abs(c.high - resistance) / resistance < 0.01)
        support_touches = sum(1 for c in candles if abs(c.low - support) / support < 0.01)
        
        total_touches = resistance_touches + support_touches
        strength = total_touches / (len(candles) * 0.3)
        
        if total_touches >= self.min_channel_touches:
            # Create horizontal lines
            upper_line = [(c.bar_index, resistance) for c in candles]
            lower_line = [(c.bar_index, support) for c in candles]
            
            return TrendChannel(
                start_bar=candles[0].bar_index,
                end_bar=candles[-1].bar_index,
                upper_line=upper_line,
                lower_line=lower_line,
                channel_type="HORIZONTAL",
                strength=min(1.0, strength),
                touches=total_touches
            )
        
        return None
    
    def _find_sweep_target(self, candles: List[Candle], swing_points: List[SwingPoint],
                          current_swing: SwingPoint, sweep_type: str) -> float:
        """Find target level after liquidity sweep"""
        if sweep_type == "SELL_SIDE":
            # Look for support levels below
            support_levels = [sp.price for sp in swing_points 
                            if sp.point_type == "LOW" and sp.price < current_swing.price]
            if support_levels:
                return max(support_levels)
        else:
            # Look for resistance levels above
            resistance_levels = [sp.price for sp in swing_points 
                               if sp.point_type == "HIGH" and sp.price > current_swing.price]
            if resistance_levels:
                return min(resistance_levels)
        
        # Fallback to recent price levels
        recent_prices = [c.close for c in candles[-10:]]
        return np.mean(recent_prices)
