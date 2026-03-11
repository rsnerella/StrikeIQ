import math
import logging

logger = logging.getLogger(__name__)

def generate_option_trade(snapshot, chain_data):
    """
    STRICT REPAIR - Phase 6 Options Trade Engine
    Implementation of the professional options trade calculation algorithm.
    """
    try:
        if not snapshot or not chain_data:
            return None

        symbol = snapshot.get("symbol", "NIFTY")
        spot = snapshot.get("spot_price", 0)
        pcr = snapshot.get("pcr", 1.0)
        
        if spot <= 0:
            return None
            
        # 1 detect bias
        if pcr > 1.2:
            bias = "BULLISH"
            option_type = "CE"
        elif pcr < 0.8:
            bias = "BEARISH"
            option_type = "PE"
        else:
            return None # Neutral - skip
            
        # 2 strike selection
        # ATM = round(spot/100)*100
        atm_strike = int(round(spot / 100) * 100)
        
        # 3 fetch option premium
        if hasattr(chain_data, 'strikes'):
            strikes = chain_data.strikes
        else:
            strikes = chain_data.get("strikes", [])

        target_strike_data = None
        for s in strikes:
            s_strike = s.strike if hasattr(s, 'strike') else s.get("strike")
            if s_strike == atm_strike:
                target_strike_data = s
                break
        
        if not target_strike_data:
            # Fallback to nearest if exact 100 not found (though usually is)
            return None
            
        if option_type == "CE":
            option_ltp = target_strike_data.call_ltp if hasattr(target_strike_data, 'call_ltp') else target_strike_data.get("call_ltp", 0)
        else:
            option_ltp = target_strike_data.put_ltp if hasattr(target_strike_data, 'put_ltp') else target_strike_data.get("put_ltp", 0)
        
        if not option_ltp or option_ltp <= 0:
            return None

        # OI check
        if option_type == "CE":
            oi = target_strike_data.call_oi if hasattr(target_strike_data, 'call_oi') else target_strike_data.get("call_oi", 0)
        else:
            oi = target_strike_data.put_oi if hasattr(target_strike_data, 'put_oi') else target_strike_data.get("put_oi", 0)
            
        if not oi or oi <= 0:
            return None
            
        # 4 calculate trade
        entry = option_ltp
        stop_loss = round(entry * 0.85, 2)
        target = round(entry * 1.35, 2)
        
        # 5 lot sizing
        lot_sizes = {
            "NIFTY": 50,
            "BANKNIFTY": 15,
            "FINNIFTY": 40
        }
        lot_size = lot_sizes.get(symbol, 50)
        risk_per_trade = 3000
        
        # lots = floor(risk_per_trade / ((entry-stop_loss) * lot_size))
        diff = entry - stop_loss
        if diff <= 0:
            return None
            
        lots = math.floor(risk_per_trade / (diff * lot_size))
        
        # 6 profit/loss
        max_loss = round((entry - stop_loss) * lot_size * lots, 2)
        expected_profit = round((target - entry) * lot_size * lots, 2)
        
        # Return structure (Phase 6.6)
        return {
            "symbol": symbol,
            "strike": atm_strike,
            "option_type": option_type,
            "option_ltp": option_ltp,
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "lots": lots,
            "max_loss": max_loss,
            "expected_profit": expected_profit,
            "confidence": 0.85
        }
        
    except Exception as e:
        logger.error(f"Error in generate_option_trade: {e}")
        return None
