"""
Neo Wave Engine - StrikeIQ Implementation
Based on Glenn Neely's Neo Wave Theory:
- Monowave Analysis
- Pattern Detection (Diametrics, Symmetricals, Neutral Triangles)
- Price/Time Similarity (Institutional Grade)
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class NeoPattern:
    pattern_type: str  # DIAMETRIC, SYMMETRICAL, NEUTRAL_TRIANGLE, MONOWAVE
    waves: List[float]
    confidence: float
    is_complete: bool
    label: str

class NeoWaveEngine:
    """
    Institutional Neo Wave Engine
    Stateless analyzer for complex wave structures.
    """
    
    def __init__(self):
        self.min_waves = 5
        self.similarity_threshold = 0.25  # 25% variance allowed for Diametrics
        
    def analyze(self, symbol: str, prices: List[float], current_price: float) -> Dict[str, Any]:
        """
        Main entry point for Neo Wave analysis.
        """
        try:
            if len(prices) < 15:
                return self._empty_result("Insufficient Data")

            # 1. Identify Monowaves (Directional legs)
            monowaves = self._extract_monowaves(prices)
            
            if not monowaves:
                return self._empty_result("No Monowaves Detected")

            # 2. Pattern Detection
            diametric = self._detect_diametric(monowaves)
            symmetrical = self._detect_symmetrical(monowaves)
            neutral_tri = self._detect_neutral_triangle(monowaves)
            
            # 3. Resolve Best Pattern
            patterns = [diametric, symmetrical, neutral_tri]
            best_pattern = max(patterns, key=lambda p: p.confidence if p else 0, default=None)
            
            if not best_pattern or best_pattern.confidence < 0.4:
                return {
                    "pattern": "MONOWAVE",
                    "label": f"Wave {len(monowaves) % 5}",
                    "confidence": 0.3,
                    "is_complete": False,
                    "monowave_count": len(monowaves)
                }

            return {
                "pattern": best_pattern.pattern_type,
                "label": best_pattern.label,
                "confidence": round(best_pattern.confidence, 2),
                "is_complete": best_pattern.is_complete,
                "wave_points": best_pattern.waves,
                "monowave_count": len(monowaves)
            }

        except Exception as e:
            logger.error(f"NeoWaveEngine error for {symbol}: {e}")
            return self._empty_result(str(e))

    def _extract_monowaves(self, prices: List[float]) -> List[float]:
        """Extract significant price legs (Monowaves)."""
        if not prices: return []
        
        legs = []
        start = prices[0]
        current_dir = 1 if prices[1] > prices[0] else -1
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff == 0: continue
            
            new_dir = 1 if diff > 0 else -1
            if new_dir != current_dir:
                # Direction changed, record leg
                legs.append(prices[i-1])
                current_dir = new_dir
        
        legs.append(prices[-1])
        return legs[-20:] # Keep recent legs

    def _detect_diametric(self, legs: List[float]) -> Optional[NeoPattern]:
        """Detect 7-wave Diametric (A-B-C-D-E-F-G)."""
        if len(legs) < 7: return None
        
        w = legs[-7:]
        moves = [abs(w[i] - w[i-1]) for i in range(1, 7)]
        
        # In a Diametric, waves should have relative similarity in price/time
        # Simplified: check variance of moves
        avg_move = sum(moves) / len(moves)
        variance = sum(abs(m - avg_move) for m in moves) / len(moves)
        
        similarity = 1.0 - (variance / avg_move if avg_move > 0 else 1.0)
        
        if similarity > 0.7:
            return NeoPattern(
                pattern_type="DIAMETRIC",
                waves=w,
                confidence=similarity,
                is_complete=True,
                label="7-Wave Diametric (A-G)"
            )
        return None

    def _detect_symmetrical(self, legs: List[float]) -> Optional[NeoPattern]:
        """Detect 9-wave Symmetrical (A-B-C-D-E-F-G-H-I)."""
        if len(legs) < 9: return None
        
        w = legs[-9:]
        moves = [abs(w[i] - w[i-1]) for i in range(1, 9)]
        
        avg_move = sum(moves) / len(moves)
        variance = sum(abs(m - avg_move) for m in moves) / len(moves)
        
        similarity = 1.0 - (variance / avg_move if avg_move > 0 else 1.0)
        
        if similarity > 0.75:
            return NeoPattern(
                pattern_type="SYMMETRICAL",
                waves=w,
                confidence=similarity,
                is_complete=True,
                label="9-Wave Symmetrical (A-I)"
            )
        return None

    def _detect_neutral_triangle(self, legs: List[float]) -> Optional[NeoPattern]:
        """Detect 5-wave Neutral Triangle where wave C is the longest."""
        if len(legs) < 5: return None
        
        w = legs[-5:]
        moves = [abs(w[i] - w[i-1]) for i in range(1, 5)] # A, B, C, D
        
        # Rule: Wave C is usually the longest in a Neutral Triangle
        if moves[2] > moves[0] and moves[2] > moves[1] and moves[2] > moves[3]:
            return NeoPattern(
                pattern_type="NEUTRAL_TRIANGLE",
                waves=w,
                confidence=0.8,
                is_complete=True,
                label="Neutral Triangle (Wave C Longest)"
            )
        return None

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        return {
            "pattern": "UNKNOWN",
            "label": reason,
            "confidence": 0,
            "is_complete": False
        }

# Singleton
neo_wave_engine = NeoWaveEngine()
