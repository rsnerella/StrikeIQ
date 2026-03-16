"""
Smart Money Concepts Detector - Market Structure, BOS, CHOCH, FVG, Order Blocks
Implements advanced SMC pattern detection with confidence scoring.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from .data_foundation import Candle
from .swing_detector import SwingPoint, SwingDetector

logger = logging.getLogger(__name__)

@dataclass
class MarketStructure:
    """Market structure classification"""
    structure_type: str  # "TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "STRUCTURAL_CHANGE"
    confidence: float
    last_higher_high: Optional[int] = None
    last_higher_low: Optional[int] = None
    last_lower_high: Optional[int] = None
    last_lower_low: Optional[int] = None

@dataclass
class BreakOfStructure:
    """Break of Structure detection"""
    bar_index: int
    price: float
    direction: str  # "BULLISH" or "BEARISH"
    structure_level: float
    confidence: float

@dataclass
class ChangeOfCharacter:
    """Change of Character detection"""
    bar_index: int
    price: float
    previous_structure: str
    new_structure: str
    confidence: float

@dataclass
class FairValueGap:
    """Fair Value Gap detection"""
    top: float
    bottom: float
    from_bar: int
    to_bar: int
    mitigation_bar: Optional[int] = None
    filled: bool = False

@dataclass
class OrderBlock:
    """Order Block detection"""
    top: float
    bottom: float
    bar_index: int
    block_type: str  # "BULLISH" or "BEARISH"
    strength: float
    mitigation_bar: Optional[int] = None
    filled: bool = False

class SMCDetector:
    """
    Detects Smart Money Concepts patterns including market structure,
    BOS, CHOCH, FVG, and Order Blocks with confidence scoring.
    """
    
    def __init__(self):
        self.swing_detector = SwingDetector(left_bars=5, right_bars=5)
        self.fvg_min_size = 0.0003  # Minimum FVG size as percentage of price
        self.ob_min_strength = 0.4
        
    def analyze_market_structure(self, candles: List[Candle], swing_points: List[SwingPoint]) -> MarketStructure:
        """
        Analyze market structure based on swing points.
        
        Args:
            candles: List of Candle objects
            swing_points: List of SwingPoint objects
            
        Returns:
            MarketStructure object
        """
        if len(swing_points) < 4:
            return MarketStructure("RANGING", 0.3)
        
        # Get recent swing points
        recent_swings = swing_points[-8:]  # Last 8 swing points
        
        # Analyze sequence of highs and lows
        swing_highs = [sp for sp in recent_swings if sp.point_type == "HIGH"]
        swing_lows = [sp for sp in recent_swings if sp.point_type == "LOW"]
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return MarketStructure("RANGING", 0.4)
        
        # Check for Higher Highs and Higher Lows (Bullish Trend)
        hh_count = 0
        hl_count = 0
        lh_count = 0
        ll_count = 0
        
        # Analyze highs
        for i in range(1, len(swing_highs)):
            if swing_highs[i].price > swing_highs[i-1].price:
                hh_count += 1
            else:
                lh_count += 1
        
        # Analyze lows
        for i in range(1, len(swing_lows)):
            if swing_lows[i].price > swing_lows[i-1].price:
                hl_count += 1
            else:
                ll_count += 1
        
        # Determine structure
        total_highs = len(swing_highs) - 1
        total_lows = len(swing_lows) - 1
        
        bullish_ratio = (hh_count + hl_count) / (total_highs + total_lows) if (total_highs + total_lows) > 0 else 0
        bearish_ratio = (lh_count + ll_count) / (total_highs + total_lows) if (total_highs + total_lows) > 0 else 0
        
        confidence = max(bullish_ratio, bearish_ratio)
        
        if bullish_ratio > 0.7:
            return MarketStructure("TRENDING_BULLISH", confidence, 
                                 swing_highs[-1].bar_index if hh_count > 0 else None,
                                 swing_lows[-1].bar_index if hl_count > 0 else None)
        elif bearish_ratio > 0.7:
            return MarketStructure("TRENDING_BEARISH", confidence,
                                 None, None,
                                 swing_highs[-1].bar_index if lh_count > 0 else None,
                                 swing_lows[-1].bar_index if ll_count > 0 else None)
        else:
            return MarketStructure("RANGING", confidence * 0.6)
    
    def detect_bos(self, candles: List[Candle], swing_points: List[SwingPoint], 
                   market_structure: MarketStructure) -> List[BreakOfStructure]:
        """
        Detect Break of Structure patterns.
        
        Args:
            candles: List of Candle objects
            swing_points: List of SwingPoint objects
            market_structure: Current market structure
            
        Returns:
            List of BreakOfStructure objects
        """
        bos_list = []
        
        if len(swing_points) < 4:
            return bos_list
        
        # Get recent swing points
        recent_swings = swing_points[-6:]
        
        # Detect bullish BOS (break above previous swing high)
        if market_structure.structure_type == "TRENDING_BULLISH":
            swing_highs = [sp for sp in recent_swings if sp.point_type == "HIGH"]
            if len(swing_highs) >= 2:
                for i in range(1, len(swing_highs)):
                    if swing_highs[i].price > swing_highs[i-1].price:
                        # Find the break candle
                        break_candle = self._find_break_candle(candles, swing_highs[i-1].bar_index, 
                                                              swing_highs[i].price, "UP")
                        if break_candle:
                            bos = BreakOfStructure(
                                bar_index=break_candle,
                                price=swing_highs[i].price,
                                direction="BULLISH",
                                structure_level=swing_highs[i-1].price,
                                confidence=min(0.9, swing_highs[i].strength * 1.2)
                            )
                            bos_list.append(bos)
        
        # Detect bearish BOS (break below previous swing low)
        elif market_structure.structure_type == "TRENDING_BEARISH":
            swing_lows = [sp for sp in recent_swings if sp.point_type == "LOW"]
            if len(swing_lows) >= 2:
                for i in range(1, len(swing_lows)):
                    if swing_lows[i].price < swing_lows[i-1].price:
                        # Find the break candle
                        break_candle = self._find_break_candle(candles, swing_lows[i-1].bar_index,
                                                              swing_lows[i].price, "DOWN")
                        if break_candle:
                            bos = BreakOfStructure(
                                bar_index=break_candle,
                                price=swing_lows[i].price,
                                direction="BEARISH",
                                structure_level=swing_lows[i-1].price,
                                confidence=min(0.9, swing_lows[i].strength * 1.2)
                            )
                            bos_list.append(bos)
        
        return bos_list
    
    def detect_choch(self, candles: List[Candle], swing_points: List[SwingPoint],
                    market_structure: MarketStructure) -> List[ChangeOfCharacter]:
        """
        Detect Change of Character patterns.
        
        Args:
            candles: List of Candle objects
            swing_points: List of SwingPoint objects
            market_structure: Current market structure
            
        Returns:
            List of ChangeOfCharacter objects
        """
        choch_list = []
        
        if len(swing_points) < 6:
            return choch_list
        
        # Look for structure changes in recent swings
        recent_swings = swing_points[-8:]
        
        # Detect bullish CHOCH (market changes from bearish to bullish)
        swing_lows = [sp for sp in recent_swings if sp.point_type == "LOW"]
        if len(swing_lows) >= 3:
            # Check if we have a sequence of lower lows followed by a higher low
            for i in range(2, len(swing_lows)):
                if (swing_lows[i-2].price > swing_lows[i-1].price and  # Lower low
                    swing_lows[i].price > swing_lows[i-1].price):     # Higher low after lower low
                    
                    # Find the break candle
                    break_candle = self._find_break_candle(candles, swing_lows[i-1].bar_index,
                                                          swing_lows[i].price, "UP")
                    if break_candle:
                        choch = ChangeOfCharacter(
                            bar_index=break_candle,
                            price=swing_lows[i].price,
                            previous_structure="TRENDING_BEARISH",
                            new_structure="TRENDING_BULLISH",
                            confidence=min(0.8, swing_lows[i].strength)
                        )
                        choch_list.append(choch)
        
        # Detect bearish CHOCH (market changes from bullish to bearish)
        swing_highs = [sp for sp in recent_swings if sp.point_type == "HIGH"]
        if len(swing_highs) >= 3:
            # Check if we have a sequence of higher highs followed by a lower high
            for i in range(2, len(swing_highs)):
                if (swing_highs[i-2].price < swing_highs[i-1].price and  # Higher high
                    swing_highs[i].price < swing_highs[i-1].price):     # Lower high after higher high
                    
                    # Find the break candle
                    break_candle = self._find_break_candle(candles, swing_highs[i-1].bar_index,
                                                          swing_highs[i].price, "DOWN")
                    if break_candle:
                        choch = ChangeOfCharacter(
                            bar_index=break_candle,
                            price=swing_highs[i].price,
                            previous_structure="TRENDING_BULLISH",
                            new_structure="TRENDING_BEARISH",
                            confidence=min(0.8, swing_highs[i].strength)
                        )
                        choch_list.append(choch)
        
        return choch_list
    
    def detect_fvg(self, candles: List[Candle]) -> List[FairValueGap]:
        """
        Detect Fair Value Gaps (imbalances).
        
        Args:
            candles: List of Candle objects
            
        Returns:
            List of FairValueGap objects
        """
        fvg_list = []
        
        for i in range(2, len(candles)):
            # Check for bullish FVG (gap up)
            if candles[i-2].high < candles[i].low:
                gap_size = (candles[i].low - candles[i-2].high) / candles[i].low
                if gap_size >= self.fvg_min_size:
                    fvg = FairValueGap(
                        top=candles[i].low,
                        bottom=candles[i-2].high,
                        from_bar=i-2,
                        to_bar=i
                    )
                    fvg_list.append(fvg)
            
            # Check for bearish FVG (gap down)
            elif candles[i-2].low > candles[i].high:
                gap_size = (candles[i-2].low - candles[i].high) / candles[i].high
                if gap_size >= self.fvg_min_size:
                    fvg = FairValueGap(
                        top=candles[i-2].low,
                        bottom=candles[i].high,
                        from_bar=i-2,
                        to_bar=i
                    )
                    fvg_list.append(fvg)
        
        return fvg_list
    
    def detect_order_blocks(self, candles: List[Candle], swing_points: List[SwingPoint]) -> List[OrderBlock]:
        """
        Detect Order Blocks (last candle before strong move).
        
        Args:
            candles: List of Candle objects
            swing_points: List of SwingPoint objects
            
        Returns:
            List of OrderBlock objects
        """
        order_blocks = []
        
        if len(swing_points) < 2:
            return order_blocks
        
        # Find order blocks at swing points
        for swing in swing_points[-6:]:  # Check last 6 swing points
            if swing.strength < self.ob_min_strength:
                continue
            
            # Get the candle before the swing point
            if swing.bar_index > 0:
                ob_candle = candles[swing.bar_index - 1]
                
                if swing.point_type == "HIGH":
                    # Bearish order block (before swing high)
                    ob = OrderBlock(
                        top=ob_candle.high,
                        bottom=ob_candle.low,
                        bar_index=ob_candle.bar_index,
                        block_type="BEARISH",
                        strength=swing.strength
                    )
                    order_blocks.append(ob)
                
                elif swing.point_type == "LOW":
                    # Bullish order block (before swing low)
                    ob = OrderBlock(
                        top=ob_candle.high,
                        bottom=ob_candle.low,
                        bar_index=ob_candle.bar_index,
                        block_type="BULLISH",
                        strength=swing.strength
                    )
                    order_blocks.append(ob)
        
        return order_blocks
    
    def _find_break_candle(self, candles: List[Candle], start_index: int, 
                          break_price: float, direction: str) -> Optional[int]:
        """
        Find the candle where price breaks a level.
        
        Args:
            candles: List of Candle objects
            start_index: Starting index to search from
            break_price: Price level that was broken
            direction: "UP" for bullish break, "DOWN" for bearish break
            
        Returns:
            Index of break candle or None
        """
        for i in range(start_index + 1, len(candles)):
            if direction == "UP" and candles[i].close > break_price:
                return i
            elif direction == "DOWN" and candles[i].close < break_price:
                return i
        
        return None
