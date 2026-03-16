"""
Chart Intelligence Engine - Automatic Price Action Detection
Detects swing highs/lows, market structure, BOS/CHOCH, FVG, Order Blocks, and classic patterns.
Returns overlay objects for frontend chart rendering.
"""

from .engine import ChartIntelligenceEngine

__all__ = ["ChartIntelligenceEngine"]
