import math
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GreeksEngine:
    """
    Options Greeks Calculator for StrikeIQ
    Computes Delta, Gamma, Theta, Vega for European options
    """

    def __init__(self):
        self.risk_free_rate = 0.06  # 6% risk-free rate
        self.days_in_year = 365.0

    def compute(self, option: Dict) -> Dict[str, float]:
        """
        Compute Greeks for an option
        
        Args:
            option: Dict containing:
                - spot: Current spot price
                - strike: Strike price
                - iv: Implied volatility (as decimal, e.g., 0.25 for 25%)
                - time_to_expiry: Days to expiry
                - option_type: "CE" or "PE"
        
        Returns:
            Dict with greeks: delta, gamma, theta, vega
        """
        try:
            S = option.get("spot", 0)
            K = option.get("strike", 0)
            IV = option.get("iv", 0)
            days_to_expiry = option.get("time_to_expiry", 30)
            option_type = option.get("option_type", "CE")
            
            if S <= 0 or K <= 0 or IV <= 0 or days_to_expiry <= 0:
                return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
            
            # Convert to years
            T = days_to_expiry / self.days_in_year
            
            # Calculate d1 and d2
            d1 = (math.log(S / K) + (self.risk_free_rate + 0.5 * IV ** 2) * T) / (IV * math.sqrt(T))
            d2 = d1 - IV * math.sqrt(T)
            
            # Calculate Greeks
            if option_type == "CE":
                delta = self._normal_cdf(d1)
                theta = (-S * self._normal_pdf(d1) * IV / (2 * math.sqrt(T)) 
                         - self.risk_free_rate * K * math.exp(-self.risk_free_rate * T) * self._normal_cdf(d2)) / self.days_in_year
            else:  # PE
                delta = self._normal_cdf(d1) - 1
                theta = (-S * self._normal_pdf(d1) * IV / (2 * math.sqrt(T)) 
                         + self.risk_free_rate * K * math.exp(-self.risk_free_rate * T) * self._normal_cdf(-d2)) / self.days_in_year
            
            gamma = self._normal_pdf(d1) / (S * IV * math.sqrt(T))
            vega = S * self._normal_pdf(d1) * math.sqrt(T) / 100  # Vega per 1% change in IV
            
            return {
                "delta": round(delta, 4),
                "gamma": round(gamma, 4),
                "theta": round(theta, 4),
                "vega": round(vega, 4)
            }
            
        except Exception as e:
            logger.error(f"Error computing greeks: {e}")
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    def _normal_cdf(self, x: float) -> float:
        """Cumulative distribution function for standard normal distribution"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _normal_pdf(self, x: float) -> float:
        """Probability density function for standard normal distribution"""
        return (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)

    def compute_chain_greeks(self, chain: Dict, spot: float, days_to_expiry: int = 30) -> Dict:
        """
        Compute Greeks for entire option chain
        
        Args:
            chain: Option chain data structure
            spot: Current spot price
            days_to_expiry: Days to expiry
        
        Returns:
            Chain with greeks added to each option
        """
        try:
            enhanced_chain = {}
            
            for strike, options in chain.items():
                enhanced_chain[strike] = {}
                
                for option_type, option_data in options.items():
                    if not option_data or not option_data.get("ltp"):
                        enhanced_chain[strike][option_type] = option_data
                        continue
                    
                    # Prepare option data for greeks calculation
                    option_for_greeks = {
                        "spot": spot,
                        "strike": int(strike),
                        "iv": option_data.get("iv", 0.25) / 100 if option_data.get("iv") else 0.25,  # Convert to decimal
                        "time_to_expiry": days_to_expiry,
                        "option_type": option_type
                    }
                    
                    # Compute greeks
                    greeks = self.compute(option_for_greeks)
                    
                    # Add greeks to option data
                    enhanced_option = option_data.copy()
                    enhanced_option.update(greeks)
                    enhanced_chain[strike][option_type] = enhanced_option
            
            return enhanced_chain
            
        except Exception as e:
            logger.error(f"Error computing chain greeks: {e}")
            return chain


# Singleton instance
greeks_engine = GreeksEngine()
