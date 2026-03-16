"""
Chart Intelligence Engine - Main Pattern Detection Engine
Orchestrates all pattern detection modules and produces overlay objects for frontend.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from .data_foundation import DataFoundation, Candle
from .swing_detector import SwingDetector, SwingPoint
from .smc_detector import SMCDetector, MarketStructure, BreakOfStructure, ChangeOfCharacter, FairValueGap, OrderBlock
from .classic_patterns import ClassicPatterns, DoubleTop, DoubleBottom, TrendChannel, LiquiditySweep, EqualHighsLows
from .options_integrator import OptionsIntegrator, OptionsMicrostructure, OptionsLevel

logger = logging.getLogger(__name__)

@dataclass
class OverlayObject:
    """Base overlay object for frontend rendering"""
    type: str  # "marker", "rectangle", "trendline"
    
    # Common properties
    color: str = "#3b82f6"
    label: str = ""
    
    # Position properties
    time: Optional[int] = None
    price: Optional[float] = None
    
    # Rectangle properties
    top: Optional[float] = None
    bottom: Optional[float] = None
    
    # Trendline properties
    points: Optional[List[Dict[str, Any]]] = None  # [{"time": 171..., "price": 23...}]
    
    # Additional metadata for analysis (not sent to frontend)
    confidence: float = 0.0
    width: int = 2

@dataclass
class ChartIntelligenceResult:
    """Complete chart intelligence analysis result"""
    market_structure: str
    pattern_detected: str
    confidence: float
    overlay_objects: List[OverlayObject]
    analysis_summary: Dict[str, Any]
    options_context: Dict[str, Any]
    processing_time_ms: float

class ChartIntelligenceEngine:
    """
    Main engine for chart intelligence analysis.
    Orchestrates all detection modules and produces overlay objects.
    """
    
    def __init__(self, max_bars: int = 200):
        self.max_bars = max_bars
        self.data_foundation = DataFoundation(max_bars)
        self.swing_detector = SwingDetector(left_bars=5, right_bars=5)
        self.smc_detector = SMCDetector()
        self.classic_patterns = ClassicPatterns()
        self.options_integrator = OptionsIntegrator()
        
        logger.info("Chart Intelligence Engine initialized")
    
    def analyze(self, candles_data: List[Dict[str, Any]], options_data: Optional[Dict[str, Any]] = None) -> ChartIntelligenceResult:
        """
        Run complete chart intelligence analysis.
        
        Args:
            candles_data: List of candle data dictionaries
            options_data: Optional options chain data
            
        Returns:
            ChartIntelligenceResult with overlay objects
        """
        start_time = time.monotonic()
        
        try:
            # Step 1: Normalize candles (ATR normalization)
            candles = self.data_foundation.normalize_candles(candles_data)
            if not candles:
                return self._empty_result("Insufficient candle data")
            
            # Step 2: Detect swings
            swing_points = self.swing_detector.detect_swings(candles)
            if not swing_points:
                return self._empty_result("No swing points detected")
            
            # Step 3: Classify market structure
            market_structure = self.smc_detector.analyze_market_structure(candles, swing_points)
            
            # Step 4: Detect BOS / CHOCH
            bos_patterns = self.smc_detector.detect_bos(candles, swing_points, market_structure)
            choch_patterns = self.smc_detector.detect_choch(candles, swing_points, market_structure)
            
            # Step 5: Detect FVG
            fvg_patterns = self.smc_detector.detect_fvg(candles)
            
            # Step 6: Detect Order Blocks
            order_blocks = self.smc_detector.detect_order_blocks(candles, swing_points)
            
            # Step 7: Detect classic patterns
            swing_highs = self.swing_detector.get_swing_highs(swing_points)
            swing_lows = self.swing_detector.get_swing_lows(swing_points)
            
            double_tops = self.classic_patterns.detect_double_tops(candles, swing_highs)
            double_bottoms = self.classic_patterns.detect_double_bottoms(candles, swing_lows)
            trend_channels = self.classic_patterns.detect_trend_channels(candles)
            liquidity_sweeps = self.classic_patterns.detect_liquidity_sweeps(candles, swing_points)
            equal_highs_lows = self.classic_patterns.detect_equal_highs_lows(candles, swing_points)
            
            # Step 8: Integrate options microstructure
            options_context = {}
            if options_data:
                spot_price = candles[-1].close
                microstructure = self.options_integrator.analyze_options_microstructure(options_data, spot_price)
                options_context = {
                    "microstructure": asdict(microstructure),
                    "significant_levels": [asdict(level) for level in 
                                         self.options_integrator.get_significant_levels(microstructure, spot_price)],
                    "gamma_regime": self.options_integrator.assess_gamma_regime(microstructure, spot_price)
                }
            
            # Step 9: Build overlay objects
            overlay_objects = self._build_overlay_objects(
                market_structure, bos_patterns, choch_patterns, fvg_patterns,
                order_blocks, double_tops, double_bottoms, trend_channels,
                liquidity_sweeps, equal_highs_lows, candles
            )
            
            # Step 10: Determine primary pattern and confidence
            primary_pattern, overall_confidence = self._determine_primary_pattern(
                market_structure, bos_patterns, choch_patterns, fvg_patterns,
                order_blocks, double_tops, double_bottoms, trend_channels,
                liquidity_sweeps, equal_highs_lows
            )
            
            # Build analysis summary
            analysis_summary = self._build_analysis_summary(
                market_structure, swing_points, bos_patterns, choch_patterns,
                fvg_patterns, order_blocks, double_tops, double_bottoms,
                trend_channels, liquidity_sweeps, equal_highs_lows
            )
            
            processing_time = (time.monotonic() - start_time) * 1000
            
            result = ChartIntelligenceResult(
                market_structure=market_structure.structure_type,
                pattern_detected=primary_pattern,
                confidence=overall_confidence,
                overlay_objects=overlay_objects,
                analysis_summary=analysis_summary,
                options_context=options_context,
                processing_time_ms=processing_time
            )
            
            if processing_time > 50:
                logger.warning(f"Chart Intelligence processing exceeded 50ms: {processing_time:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Chart Intelligence analysis failed: {e}", exc_info=True)
            return self._empty_result(f"Analysis error: {str(e)}")
    
    def _build_overlay_objects(self, market_structure: MarketStructure,
                             bos_patterns: List[BreakOfStructure],
                             choch_patterns: List[ChangeOfCharacter],
                             fvg_patterns: List[FairValueGap],
                             order_blocks: List[OrderBlock],
                             double_tops: List[DoubleTop],
                             double_bottoms: List[DoubleBottom],
                             trend_channels: List[TrendChannel],
                             liquidity_sweeps: List[LiquiditySweep],
                             equal_highs_lows: List[EqualHighsLows],
                             candles: List[Candle]) -> List[OverlayObject]:
        """Build overlay objects from detected patterns aligning with frontend schema"""
        overlays = []
        
        def bar_to_time(bar_idx: int) -> int:
            if 0 <= bar_idx < len(candles):
                return int(candles[bar_idx].time)
            return int(candles[-1].time)

        # 1. BOS markers
        for bos in bos_patterns:
            overlays.append(OverlayObject(
                type="marker",
                time=bar_to_time(bos.bar_index),
                price=bos.price,
                label="BOS",
                color="#60a5fa" if bos.direction == "BULLISH" else "#f87171",
                confidence=bos.confidence
            ) )
        
        # 2. CHOCH markers
        for choch in choch_patterns:
            overlays.append(OverlayObject(
                type="marker",
                time=bar_to_time(choch.bar_index),
                price=choch.price,
                label="CHOCH",
                color="#fbbf24",
                confidence=choch.confidence
            ) )
        
        # 3. FVG rectangles
        for fvg in fvg_patterns[-5:]:  # Last 5 FVGs
            overlays.append(OverlayObject(
                type="rectangle",
                top=fvg.top,
                bottom=fvg.bottom,
                label="FVG",
                color="#4ade8012",
                confidence=0.7
            ) )
        
        # 4. Order Block rectangles
        for ob in order_blocks[-3:]:  # Last 3 order blocks
            overlays.append(OverlayObject(
                type="rectangle",
                top=ob.top,
                bottom=ob.bottom,
                label=f"OB {ob.block_type[:3]}",
                color="#f59e0b25" if ob.block_type == "BULLISH" else "#ef444425",
                confidence=ob.strength
            ) )
        
        # 5. Liquidity Pools (Equal Highs/Lows) → Rectangles/Zones
        for ehl in equal_highs_lows:
            overlays.append(OverlayObject(
                type="rectangle",
                top=ehl.price_level * 1.001,
                bottom=ehl.price_level * 0.999,
                label=f"LIQ {ehl.pattern_type[-4:]}",
                color="#06b6d420",
                confidence=ehl.confidence
            ) )

        # 6. Trend channels → Trendlines
        for channel in trend_channels:
            if channel.upper_line:
                overlays.append(OverlayObject(
                    type="trendline",
                    points=[{"time": bar_to_time(p[0]), "price": p[1]} for p in channel.upper_line],
                    label="UPPER CHANNEL",
                    color="#8b5cf6",
                    width=2
                ) )
            if channel.lower_line:
                overlays.append(OverlayObject(
                    type="trendline",
                    points=[{"time": bar_to_time(p[0]), "price": p[1]} for p in channel.lower_line],
                    label="LOWER CHANNEL",
                    color="#8b5cf6",
                    width=2
                ) )
        
        # 7. Liquidity Sweeps → Markers
        for sweep in liquidity_sweeps:
            overlays.append(OverlayObject(
                type="marker",
                time=bar_to_time(sweep.sweep_bar),
                price=sweep.sweep_price,
                label=f"SWEEP {sweep.sweep_type[:3]}",
                color="#f59e0b",
                confidence=sweep.confidence
            ) )

        return overlays
    
    def _determine_primary_pattern(self, market_structure: MarketStructure,
                                  bos_patterns: List[BreakOfStructure],
                                  choch_patterns: List[ChangeOfCharacter],
                                  fvg_patterns: List[FairValueGap],
                                  order_blocks: List[OrderBlock],
                                  double_tops: List[DoubleTop],
                                  double_bottoms: List[DoubleBottom],
                                  trend_channels: List[TrendChannel],
                                  liquidity_sweeps: List[LiquiditySweep],
                                  equal_highs_lows: List[EqualHighsLows]) -> tuple[str, float]:
        """Determine the primary pattern and overall confidence"""
        
        # Priority order for pattern selection
        pattern_priority = {
            "CHOCH": 100,
            "BOS": 90,
            "DOUBLE_TOP": 80,
            "DOUBLE_BOTTOM": 80,
            "LIQUIDITY_SWEEP": 70,
            "TREND_CHANNEL": 60,
            "EQUAL_HIGHS_LOWS": 50,
            "FVG": 40,
            "ORDER_BLOCK": 30
        }
        
        best_pattern = "NONE"
        best_confidence = 0.0
        
        # Check CHOCH
        if choch_patterns:
            best_pattern = "CHOCH_BULLISH" if choch_patterns[-1].new_structure == "TRENDING_BULLISH" else "CHOCH_BEARISH"
            best_confidence = choch_patterns[-1].confidence
        
        # Check BOS
        if bos_patterns and bos_patterns[-1].confidence > best_confidence:
            best_pattern = f"BOS_{bos_patterns[-1].direction}"
            best_confidence = bos_patterns[-1].confidence
        
        # Check Double patterns
        if double_tops and double_tops[-1].confidence > best_confidence:
            best_pattern = "DOUBLE_TOP"
            best_confidence = double_tops[-1].confidence
        
        if double_bottoms and double_bottoms[-1].confidence > best_confidence:
            best_pattern = "DOUBLE_BOTTOM"
            best_confidence = double_bottoms[-1].confidence
        
        # Check Liquidity Sweeps
        if liquidity_sweeps and liquidity_sweeps[-1].confidence > best_confidence:
            best_pattern = f"LIQUIDITY_SWEEP_{liquidity_sweeps[-1].sweep_type}"
            best_confidence = liquidity_sweeps[-1].confidence
        
        # Check Trend Channels
        if trend_channels and trend_channels[-1].strength > best_confidence:
            best_pattern = f"TREND_CHANNEL_{trend_channels[-1].channel_type}"
            best_confidence = trend_channels[-1].strength
        
        # Check Equal Highs/Lows
        if equal_highs_lows and equal_highs_lows[-1].confidence > best_confidence:
            best_pattern = equal_highs_lows[-1].pattern_type
            best_confidence = equal_highs_lows[-1].confidence
        
        # If no specific pattern, use market structure
        if best_pattern == "NONE":
            best_pattern = market_structure.structure_type
            best_confidence = market_structure.confidence
        
        return best_pattern, min(1.0, best_confidence)
    
    def _build_analysis_summary(self, market_structure: MarketStructure,
                              swing_points: List[SwingPoint],
                              bos_patterns: List[BreakOfStructure],
                              choch_patterns: List[ChangeOfCharacter],
                              fvg_patterns: List[FairValueGap],
                              order_blocks: List[OrderBlock],
                              double_tops: List[DoubleTop],
                              double_bottoms: List[DoubleBottom],
                              trend_channels: List[TrendChannel],
                              liquidity_sweeps: List[LiquiditySweep],
                              equal_highs_lows: List[EqualHighsLows]) -> Dict[str, Any]:
        """Build comprehensive analysis summary"""
        return {
            "market_structure": {
                "type": market_structure.structure_type,
                "confidence": market_structure.confidence,
                "last_higher_high": market_structure.last_higher_high,
                "last_higher_low": market_structure.last_higher_low,
                "last_lower_high": market_structure.last_lower_high,
                "last_lower_low": market_structure.last_lower_low
            },
            "swing_points": {
                "total_count": len(swing_points),
                "swing_highs": len([sp for sp in swing_points if sp.point_type == "HIGH"]),
                "swing_lows": len([sp for sp in swing_points if sp.point_type == "LOW"])
            },
            "patterns": {
                "bos_count": len(bos_patterns),
                "choch_count": len(choch_patterns),
                "fvg_count": len(fvg_patterns),
                "order_block_count": len(order_blocks),
                "double_top_count": len(double_tops),
                "double_bottom_count": len(double_bottoms),
                "trend_channel_count": len(trend_channels),
                "liquidity_sweep_count": len(liquidity_sweeps),
                "equal_highs_lows_count": len(equal_highs_lows)
            },
            "recent_activity": {
                "latest_bos": bos_patterns[-1].direction if bos_patterns else None,
                "latest_choch": choch_patterns[-1].new_structure if choch_patterns else None,
                "unfilled_fvgs": len([fvg for fvg in fvg_patterns if not fvg.filled]),
                "active_order_blocks": len([ob for ob in order_blocks if not ob.filled])
            }
        }
    
    def _empty_result(self, reason: str) -> ChartIntelligenceResult:
        """Return empty result when analysis cannot be performed"""
        return ChartIntelligenceResult(
            market_structure="UNKNOWN",
            pattern_detected="NONE",
            confidence=0.0,
            overlay_objects=[],
            analysis_summary={"error": reason},
            options_context={},
            processing_time_ms=0.0
        )

# Global singleton
chart_intelligence_engine = ChartIntelligenceEngine()
