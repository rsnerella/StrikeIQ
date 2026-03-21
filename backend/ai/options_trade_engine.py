import math
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def generate_option_trade(snapshot, chain_data):
    """
    STRICT REPAIR - Phase 6 Options Trade Engine
    Implementation of the professional options trade calculation algorithm.
    """
    try:
        if not snapshot or not chain_data:
            return None

        symbol = snapshot.symbol if hasattr(snapshot, 'symbol') else "NIFTY"
        spot = snapshot.spot if hasattr(snapshot, 'spot') else 0
        pcr = snapshot.pcr if hasattr(snapshot, 'pcr') else 1.0
        
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
        # Dynamic ATM calculation based on symbol-specific steps
        config = {
            "NIFTY": {"step": 50},
            "BANKNIFTY": {"step": 100},
            "FINNIFTY": {"step": 50}
        }
        step = config.get(symbol, {"step": 50})["step"]
        atm_strike = int(round(spot / step) * step)
        
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
            "NIFTY": 25,
            "BANKNIFTY": 15,
            "FINNIFTY": 40
        }
        lot_size = lot_sizes.get(symbol, 25)
        risk_per_trade = 3000
        
        # lots = floor(risk_per_trade / ((entry-stop_loss) * lot_size))
        diff = entry - stop_loss
        if diff <= 0:
            return None
            
        lots = math.floor(risk_per_trade / (diff * lot_size))
        if lots <= 0: lots = 1 # Minimum 1 lot
        
        # 6 profit/loss
        max_loss = round((entry - stop_loss) * lot_size * lots, 2)
        expected_profit = round((target - entry) * lot_size * lots, 2)
        
        # 7 Format formal signal message
        buy_message = f"BUY {symbol} {atm_strike} {option_type}"
        
        # Return structure (Phase 6.6)
        return {
            "symbol": symbol,
            "strike": atm_strike,
            "option_type": option_type,
            "option_ltp": option_ltp,
            "signal_text": buy_message,
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

class OptionsTradeEngine:
    """Enhanced options trade engine with AI-powered strike selection"""
    
    def __init__(self):
        self.feature_engine = None  # Will be initialized
        self.bias_model = None    # Will be initialized
        
    def initialize_ai_components(self):
        """Initialize new AI components"""
        try:
            from ai.feature_engine import FeatureEngine
            from ai.bias_model import BiasModel
            
            self.feature_engine = FeatureEngine()
            self.bias_model = BiasModel()
            logger.info("OptionsTradeEngine AI components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AI components: {e}")
        
    def select_optimal_strike(self, features, spot_price) -> Optional[Dict[str, Any]]:
        """Select optimal strike based on features"""
        try:
            if not features or not spot_price:
                return None
            
            # Generate strike universe
            strike_universe = self.generate_strike_universe(spot_price)
            
            # Score each strike
            scored_strikes = []
            for strike in strike_universe:
                score = self.score_strike(strike, features, spot_price)
                if score > 0:
                    scored_strikes.append({
                        'strike': strike,
                        'score': score,
                        'option_type': self.select_option_type(strike, features),
                        'liquidity_score': self.calculate_liquidity_score(strike, features),
                        'gamma_score': self.calculate_gamma_score(strike, features),
                        'risk_reward': self.calculate_risk_reward(strike, features)
                    })
            
            if not scored_strikes:
                return None
            
            # Select optimal strike
            optimal_strike = max(scored_strikes, key=lambda x: x['score'])
            
            return optimal_strike
            
        except Exception as e:
            logger.error(f"Strike selection failed: {e}")
            return None
    
    def generate_strike_universe(self, spot_price) -> List[float]:
        """Generate strike universe around ATM"""
        strikes = []
        step = 50  # NIFTY step
        
        # Generate strikes from -10 to +10
        for i in range(-10, 11):
            strike = round((spot_price / step) + i) * step
            strikes.append(strike)
        
        return strikes
    
    def score_strike(self, strike, features, spot_price) -> float:
        """Score individual strike"""
        try:
            score = 0.0
            
            # Liquidity score (40% weight)
            liquidity_score = self.calculate_liquidity_score(strike, features)
            score += liquidity_score * 0.4
            
            # Gamma score (25% weight)
            gamma_score = self.calculate_gamma_score(strike, features)
            score += gamma_score * 0.25
            
            # OI score (20% weight)
            oi_score = self.calculate_oi_score(strike, features)
            score += oi_score * 0.20
            
            # Distance score (15% weight)
            distance_score = self.calculate_distance_score(strike, spot_price)
            score += distance_score * 0.15
            
            return score
            
        except Exception as e:
            logger.error(f"Strike scoring failed: {e}")
            return 0.0
    
    def calculate_liquidity_score(self, strike, features) -> float:
        """Calculate liquidity score for strike"""
        try:
            call_oi_dist = features.get('call_oi_distribution', {})
            put_oi_dist = features.get('put_oi_distribution', {})
            
            call_oi = call_oi_dist.get(str(strike), 0)
            put_oi = put_oi_dist.get(str(strike), 0)
            total_oi = call_oi + put_oi
            
            # Liquidity threshold
            if total_oi > 1000000:  # 10 lakh OI
                return 1.0
            elif total_oi > 500000:  # 5 lakh OI
                return 0.7
            elif total_oi > 100000:  # 1 lakh OI
                return 0.4
            else:
                return 0.1
                
        except Exception as e:
            logger.error(f"Liquidity score calculation failed: {e}")
            return 0.0
    
    def calculate_gamma_score(self, strike, features) -> float:
        """Calculate gamma score for strike"""
        try:
            call_wall = features.get('call_wall_strike')
            put_wall = features.get('put_wall_strike')
            gamma_flip = features.get('gamma_flip_probability', 0)
            
            score = 0.0
            
            # Proximity to gamma walls
            if call_wall and abs(strike - call_wall) < 100:
                score += 0.5
            if put_wall and abs(strike - put_wall) < 100:
                score += 0.5
            
            # Gamma flip probability
            score += gamma_flip * 0.3
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Gamma score calculation failed: {e}")
            return 0.0
    
    def calculate_oi_score(self, strike, features) -> float:
        """Calculate OI score for strike"""
        try:
            call_oi_dist = features.get('call_oi_distribution', {})
            put_oi_dist = features.get('put_oi_distribution', {})
            
            call_oi = call_oi_dist.get(str(strike), 0)
            put_oi = put_oi_dist.get(str(strike), 0)
            total_oi = call_oi + put_oi
            
            # OI concentration score
            total_market_oi = sum(call_oi_dist.values()) + sum(put_oi_dist.values())
            if total_market_oi == 0:
                return 0.0
            
            concentration = total_oi / total_market_oi
            return min(1.0, concentration * 10)  # Scale up
            
        except Exception as e:
            logger.error(f"OI score calculation failed: {e}")
            return 0.0
    
    def calculate_distance_score(self, strike, spot_price) -> float:
        """Calculate distance score from ATM"""
        try:
            distance = abs(strike - spot_price)
            
            # Optimal distance is 2-4 strikes from ATM
            if distance <= 200:  # 4 strikes
                return 1.0
            elif distance <= 400:  # 8 strikes
                return 0.7
            elif distance <= 600:  # 12 strikes
                return 0.4
            else:
                return 0.1
                
        except Exception as e:
            logger.error(f"Distance score calculation failed: {e}")
            return 0.0
    
    def calculate_risk_reward(self, strike, features) -> float:
        """Calculate risk-reward ratio for strike"""
        try:
            # Simplified risk-reward calculation
            # In production, this would use actual option pricing models
            return 2.0  # Default 2:1 risk-reward
        except Exception as e:
            logger.error(f"Risk-reward calculation failed: {e}")
            return 1.5
    
    def select_option_type(self, strike, features) -> str:
        """Select CE or PE based on features"""
        try:
            bias_direction = features.get('bias', 'NEUTRAL')
            
            if bias_direction == 'BULLISH':
                return 'CE'
            elif bias_direction == 'BEARISH':
                return 'PE'
            else:
                # For neutral bias, select based on gamma
                call_wall = features.get('call_wall_strike')
                put_wall = features.get('put_wall_strike')
                
                if call_wall and put_wall:
                    return 'CE' if abs(strike - call_wall) < abs(strike - put_wall) else 'PE'
                else:
                    return 'CE'  # Default
                    
        except Exception as e:
            logger.error(f"Option type selection failed: {e}")
            return 'CE'
