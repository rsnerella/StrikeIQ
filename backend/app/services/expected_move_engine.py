"""
Expected Move Engine
Computes expected move from ATM call + put premium and breakout detection
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from ..exceptions.data_unavailable_error import DataUnavailableError, MissingATMError, MissingPremiumError
from app.core.diagnostics import diag
from app.core.ai_health_state import mark_health

logger = logging.getLogger(__name__)

@dataclass
class ExpectedMoveResult:
    """Expected move analysis result"""
    symbol: str
    spot: float
    atm_call_premium: float
    atm_put_premium: float
    combined_premium: float
    expected_move_1sd: float
    expected_move_2sd: float
    breakout_detected: bool
    breakout_direction: str  # "upward", "downward", "none"
    breakout_strength: float  # 0-100
    implied_volatility: float
    time_to_expiry: float  # days
    timestamp: str

class ExpectedMoveEngine:
    """
    Computes expected moves from option premiums and detects breakouts
    """
    
    def __init__(self):
        self.historical_moves = {}  # Store historical expected moves
        
    def compute(self, data: Dict[str, Any]) -> ExpectedMoveResult:
        """
        Compute expected move from option chain data
        """
        # FIX 8: Enhanced validation layer for safe processing
        if not data:
            logger.warning("ExpectedMoveEngine: No data provided, returning safe default")
            return self._get_safe_default_result()
        
        symbol = data.get("symbol", "NIFTY")
        spot = data.get("spot", 0)
        calls = data.get("calls", [])
        puts = data.get("puts", [])
        
        # Validate essential data
        if not spot or spot <= 0:
            logger.warning(f"ExpectedMoveEngine: Invalid spot price {spot}, returning safe default")
            return self._get_safe_default_result(symbol)
        
        if not calls or not puts:
            logger.warning("ExpectedMoveEngine: Empty option chain, returning safe default")
            return self._get_safe_default_result(symbol)
        
        # Validate essential data
        if not calls or not puts:
            raise DataUnavailableError("Empty option chain - no calls or puts data")
        
        if spot <= 0:
            raise DataUnavailableError("Invalid spot price for expected move calculation")
        
        try:
            # Find ATM options
            atm_call, atm_put = self._find_atm_options(calls, puts, spot)
            
            # Validate ATM options
            if not atm_call or not atm_put:
                logger.warning("ExpectedMoveEngine: ATM options not found, returning safe default")
                return self._get_safe_default_result(symbol)
            
            # Calculate premiums
            atm_call_premium = atm_call.get("last_price", 0) if atm_call else 0
            atm_put_premium = atm_put.get("last_price", 0) if atm_put else 0
            combined_premium = atm_call_premium + atm_put_premium
            
            # Validate premiums
            if combined_premium <= 0:
                logger.warning("ExpectedMoveEngine: Invalid ATM premiums, returning safe default")
                return self._get_safe_default_result(symbol)
            
            # Calculate expected moves
            expected_move_1sd, expected_move_2sd = self._calculate_expected_moves(
                combined_premium, spot
            )
            
            # Detect breakout conditions
            breakout_detected, breakout_direction, breakout_strength = self._detect_breakout(
                spot, calls, puts, expected_move_1sd
            )
            
            # Calculate implied volatility
            implied_vol = self._calculate_implied_volatility(
                combined_premium, spot, data.get("expiry", "")
            )
            
            # Calculate time to expiry
            time_to_expiry = self._calculate_time_to_expiry(data.get("expiry", ""))
            
            return ExpectedMoveResult(
                symbol=symbol,
                spot=spot,
                atm_call_premium=atm_call_premium,
                atm_put_premium=atm_put_premium,
                combined_premium=combined_premium,
                expected_move_1sd=expected_move_1sd,
                expected_move_2sd=expected_move_2sd,
                breakout_detected=breakout_detected,
                breakout_direction=breakout_direction,
                breakout_strength=breakout_strength,
                implied_volatility=implied_vol,
                time_to_expiry=time_to_expiry,
                timestamp=data.get("timestamp", "")
            )
            
            # Add diagnostic logging for volatility and expected move
            diag("AI_TEST", f"ATM IV: {implied_vol}")
            diag("AI_TEST", f"Expected move: {expected_move_1sd}")
            
            # Mark volatility engine as healthy
            mark_health("volatility")
            
        except Exception as e:
            logger.error(f"ExpectedMoveEngine: Error computing expected move: {e}")
            return self._get_safe_default_result(symbol)
    
    def _get_safe_default_result(self, symbol: str = "NIFTY") -> ExpectedMoveResult:
        """Return safe default result for error conditions"""
        return ExpectedMoveResult(
            symbol=symbol,
            spot=0.0,
            atm_call_premium=0.0,
            atm_put_premium=0.0,
            combined_premium=0.0,
            expected_move_1sd=0.0,
            expected_move_2sd=0.0,
            breakout_detected=False,
            breakout_direction="none",
            breakout_strength=0.0,
            implied_volatility=0.0,
            time_to_expiry=0.0,
            timestamp=""
        )
    
    def _find_atm_options(self, calls: List[Dict], puts: List[Dict], spot: float) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Find ATM call and put options"""
        try:
            atm_call = None
            atm_put = None
            min_call_distance = float('inf')
            min_put_distance = float('inf')
            
            # Find ATM call
            for call in calls:
                strike = call.get("strike", 0)
                distance = abs(strike - spot)
                if distance < min_call_distance and strike >= spot:
                    min_call_distance = distance
                    atm_call = call
            
            # Find ATM put
            for put in puts:
                strike = put.get("strike", 0)
                distance = abs(strike - spot)
                if distance < min_put_distance and strike <= spot:
                    min_put_distance = distance
                    atm_put = put
            
            return atm_call, atm_put
            
        except Exception as e:
            logger.error(f"Error finding ATM options: {e}")
            return None, None
    
    def _calculate_expected_moves(self, combined_premium: float, spot: float) -> Tuple[float, float]:
        """Calculate 1SD and 2SD expected moves from premium"""
        try:
            # Use combined premium as proxy for expected move
            # 1SD ≈ combined premium * 0.8
            # 2SD ≈ combined premium * 1.6
            expected_move_1sd = combined_premium * 0.8
            expected_move_2sd = combined_premium * 1.6
            
            return expected_move_1sd, expected_move_2sd
            
        except Exception as e:
            logger.error(f"Error calculating expected moves: {e}")
            return 0, 0
    
    def _detect_breakout(self, spot: float, calls: List[Dict], puts: List[Dict], expected_move: float) -> Tuple[bool, str, float]:
        """Detect breakout conditions"""
        try:
            # Calculate support and resistance from option chain
            resistance = self._calculate_resistance(calls, spot)
            support = self._calculate_support(puts, spot)
            
            # Check if price is breaking resistance
            if spot > resistance and (spot - resistance) > expected_move * 0.5:
                strength = min(((spot - resistance) / expected_move) * 100, 100)
                return True, "upward", strength
            
            # Check if price is breaking support
            if spot < support and (support - spot) > expected_move * 0.5:
                strength = min(((support - spot) / expected_move) * 100, 100)
                return True, "downward", strength
            
            return False, "none", 0
            
        except Exception as e:
            logger.error(f"Error detecting breakout: {e}")
            return False, "none", 0
    
    def _calculate_resistance(self, calls: List[Dict], spot: float) -> float:
        """Calculate resistance level from call options"""
        try:
            # Find highest OI call above spot
            max_oi = 0
            resistance_level = spot
            
            for call in calls:
                strike = call.get("strike", 0)
                oi = call.get("open_interest", 0)
                if strike > spot and oi > max_oi:
                    max_oi = oi
                    resistance_level = strike
            
            return resistance_level
            
        except Exception as e:
            logger.error(f"Error calculating resistance: {e}")
            return spot
    
    def _calculate_support(self, puts: List[Dict], spot: float) -> float:
        """Calculate support level from put options"""
        try:
            # Find highest OI put below spot
            max_oi = 0
            support_level = spot
            
            for put in puts:
                strike = put.get("strike", 0)
                oi = put.get("open_interest", 0)
                if strike < spot and oi > max_oi:
                    max_oi = oi
                    support_level = strike
            
            return support_level
            
        except Exception as e:
            logger.error(f"Error calculating support: {e}")
            return spot
    
    def _calculate_implied_volatility(self, combined_premium: float, spot: float, expiry: str) -> float:
        """Calculate implied volatility from premium"""
        try:
            # Simplified IV calculation
            # In reality, this would use Black-Scholes model
            if combined_premium <= 0 or spot <= 0:
                return 0
            
            dte = self._calculate_time_to_expiry(expiry)
            if dte <= 0:
                dte = 0.01  # use small fraction if expires today or in past
            
            # Correct approximation: IV ≈ (premium / spot) * sqrt(365 / DTE_days) * 100
            iv_approx = (combined_premium / spot) * np.sqrt(365 / dte) * 100
            
            return float(min(max(iv_approx, 0), 200))  # Cap between 0-200%
            
        except Exception as e:
            logger.error(f"Error calculating IV: {e}")
            return 0
    
    def _calculate_time_to_expiry(self, expiry: str) -> float:
        """Calculate days to expiry"""
        try:
            from datetime import datetime
            if not expiry:
                return 0
            
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
            current_date = datetime.now()
            
            return max((expiry_date - current_date).days, 0)
            
        except Exception as e:
            logger.error(f"Error calculating time to expiry: {e}")
            return 0
