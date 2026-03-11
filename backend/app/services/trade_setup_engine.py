import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TradeSetupEngine:
    def compute(self, symbol: str, spot: float, chain_data: Dict[str, Any], analytics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Produce CALL BUY / PUT BUY signal based on:
        - PCR
        - gamma exposure
        - support/resistance levels
        - spot vs ATM positioning
        """
        try:
            if spot <= 0:
                return {"signal": "WAIT"}

            # Safely extract PCR
            bias_data = analytics.get("bias", {})
            pcr = float(bias_data.get("pcr_value", bias_data.get("pcr", 1.0)))

            # Extract structural analytics
            structural = analytics.get("structural", {})
            net_gamma = structural.get("net_gamma", 0)
            support = structural.get("support_level", spot * 0.99)
            resistance = structural.get("resistance_level", spot * 1.01)

            # Determine ATM strike
            step = 50 if symbol == "NIFTY" else 100
            if isinstance(chain_data, dict):
                atm_strike = chain_data.get("atm_strike", round(spot / step) * step)
                strikes = chain_data.get("strikes", [])
            else:
                atm_strike = getattr(chain_data, "atm_strike", round(spot / step) * step)
                strikes = getattr(chain_data, "strikes", [])

            signal = "WAIT"
            selected_strike = atm_strike
            
            # Logic for BUY CALL vs BUY PUT
            # 1. Price is near support, Gamma allows up, PCR is relatively oversold -> BUY CALL
            if spot - support < (spot * 0.002) and net_gamma >= 0 and pcr < 0.9:
                signal = "BUY_CALL"
            # 2. Price is near resistance, Gamma allows down, PCR is relatively overbought -> BUY PUT
            elif resistance - spot < (spot * 0.002) and net_gamma <= 0 and pcr > 1.1:
                signal = "BUY_PUT"

            if signal == "WAIT":
                # Fallback purely on momentum and pcr if not heavily near support/resistance
                if pcr < 0.7 and net_gamma > 0:
                    signal = "BUY_CALL"
                elif pcr > 1.3 and net_gamma < 0:
                    signal = "BUY_PUT"
                else:
                    return {"signal": "WAIT"}

            # Search the option chain for the premium
            entry_price = 0.0
            for s in strikes:
                if isinstance(s, dict) and s.get("strike") == selected_strike:
                    if signal == "BUY_CALL":
                        entry_price = s.get("call_ltp", 0.0)
                    elif signal == "BUY_PUT":
                        entry_price = s.get("put_ltp", 0.0)
                    break

            if entry_price <= 0:
                return {"signal": "WAIT", "note": "Premium not found for ATM strike"}

            # Risk/Reward Calculation (e.g., Target 80% gain, Stop Loss 35% loss)
            target_price = entry_price * 1.8
            stop_loss = entry_price * 0.65
            risk = entry_price - stop_loss
            reward = target_price - entry_price

            risk_reward = round(reward / risk, 1) if risk > 0 else 0.0

            return {
                "signal": signal,
                "strike": selected_strike,
                "entry": round(entry_price, 1),
                "stop_loss": round(stop_loss, 1),
                "target": round(target_price, 1),
                "risk_reward": risk_reward
            }

        except Exception as e:
            logger.error(f"Error in TradeSetupEngine: {e}", exc_info=True)
            return {"signal": "WAIT"}

trade_setup_engine = TradeSetupEngine()
