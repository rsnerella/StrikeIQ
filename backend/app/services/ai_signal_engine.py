"""
AI Signal Engine for StrikeIQ

Responsibilities:
- Read latest option chain snapshot
- Evaluate formulas from formula_master
- Generate signals when conditions match
- Insert signals into prediction_log
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from ai.ai_db import ai_db
from ai.prediction_service import prediction_service
from app.core.ai_diagnostics import validate_option_chain, validate_oi, validate_ai_signal

logger = logging.getLogger(__name__)

class AISignalEngine:
    def __init__(self):
        self.db = ai_db
        self.prediction_service = prediction_service
        self.last_spot_prices = {}
        self.last_signal_times = {}
        
    async def get_latest_market_snapshot(self) -> Optional[Dict]:
        """Get the latest market snapshot for AI analysis"""
        try:
            query = """
                SELECT id, symbol, spot_price, pcr, total_call_oi, total_put_oi, atm_strike, gamma_exposure, expected_move, timestamp
                FROM market_snapshots
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            result = await self.db.fetch_one(query)
            
            if result:
                return {
                    'snapshot_id': result[0],
                    'symbol': result[1],
                    'spot_price': result[2],
                    'pcr': result[3],
                    'total_call_oi': result[4],
                    'total_put_oi': result[5],
                    'atm_strike': result[6],
                    'gamma_exposure': result[7],
                    'expected_move': result[8],
                    'timestamp': result[9]
                }
            else:
                logger.warning("No market snapshot found")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching market snapshot: {e}")
            return None
    
    async def get_active_formulas(self) -> List[Dict]:
        """Get all active formulas from formula_master"""
        try:
            query = """
                SELECT id, formula_name, formula_type, conditions, confidence_threshold, is_active
                FROM formula_master
                WHERE is_active = TRUE
                ORDER BY id
            """
            
            results = await self.db.fetch_query(query)
            
            formulas = []
            for row in results:
                formulas.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'conditions': row[3],
                    'confidence_threshold': row[4],
                    'is_active': row[5]
                })
                
            logger.info(f"Found {len(formulas)} active formulas")
            return formulas
            
        except Exception as e:
            logger.error(f"Error fetching active formulas: {e}")
            return []
    
    def evaluate_formula_conditions(self, formula: Dict, market_data: Dict) -> Tuple[bool, str, float, str]:
        """
        Evaluate if formula conditions match current market data
        
        Returns:
            Tuple of (matches, signal, confidence, reason)
        """
        try:
            conditions = formula['conditions'].upper()
            confidence_threshold = formula['confidence_threshold']
            
            matches = False
            signal = "HOLD"
            confidence = 0.0
            reason = ""
            
            # PCR-based signals
            if 'PCR' in conditions:
                pcr = market_data.get('pcr', 0)
                # Enforce numeric conversion
                try:
                    pcr = float(pcr or 0)
                except:
                    pcr = 0.0
                        
                if '>' in conditions and pcr > 1.05:
                    matches = True
                    signal = "BUY"
                    confidence = min(0.9, pcr / 2.0)
                    reason = f"Elevated PCR bullish reversal ({pcr:.2f})"
                elif '<' in conditions and pcr < 0.95:
                    matches = True
                    signal = "SELL"
                    confidence = min(0.9, (0.95 - pcr) / 0.95)
                    reason = f"Low PCR bearish pressure ({pcr:.2f})"
            
            # OI-based signals
            if 'total_call_oi' in conditions and 'total_put_oi' in conditions:
                call_oi = float(market_data.get('total_call_oi', 0) or 0)
                put_oi = float(market_data.get('total_put_oi', 0) or 0)
                
                if call_oi > put_oi * 1.5:
                    matches = True
                    signal = "SELL"
                    confidence = max(confidence, min(0.8, (call_oi - put_oi) / call_oi if call_oi > 0 else 0.0))
                    reason += " | Call-side OI accumulation"
                elif put_oi > call_oi * 1.5:
                    matches = True
                    signal = "BUY"
                    confidence = max(confidence, min(0.8, (put_oi - call_oi) / put_oi if put_oi > 0 else 0.0))
                    reason += " | Put-side OI accumulation"
            
            # Gamma signals
            gamma = market_data.get('gamma_exposure', 0)
            if 'gamma' in conditions.lower():
                if gamma > 1000000:
                    matches = True
                    signal = "BUY"
                    confidence = max(confidence, 0.75)
                    reason += " | High Positive GEX support"
                elif gamma < -1000000:
                    matches = True
                    signal = "SELL"
                    confidence = max(confidence, 0.75)
                    reason += " | High Negative GEX pressure"

            # Apply confidence threshold
            if matches and confidence >= confidence_threshold:
                return True, signal, confidence, reason.strip(" | ")
            else:
                return False, "HOLD", 0.0, ""
                
        except Exception as e:
            logger.error(f"Error evaluating formula conditions: {e}")
            return False, "HOLD", 0.0
    
    async def generate_signals(self) -> int:
        """
        Generate signals based on current market data and active formulas
        
        Returns:
            Number of signals generated
        """
        try:
            # Get latest market data
            market_data = await self.get_latest_market_snapshot()
            if not market_data:
                logger.warning("No market snapshot available — skipping signal generation")
                return 0
            
            # CHECK DATA VALIDITY BEFORE PROCESSING
            if hasattr(market_data, 'is_valid') and not market_data.is_valid:
                logger.warning("Invalid market data — blocking signal generation")
                return 0
            
            # Phase 1: Snapshot Validation (Numerical)
            spot = float(market_data.get('spot_price', 0) or 0)
            expected_move = float(market_data.get('expected_move', 0) or 0)
            total_call_oi = int(market_data.get('total_call_oi', 0) or 0)
            total_put_oi = int(market_data.get('total_put_oi', 0) or 0)
            symbol = market_data.get('symbol', 'NIFTY')
            
            # Phase 1: Snapshot Noise Filter (0.05% price change)
            prev_spot = self.last_spot_prices.get(symbol, 0)
            if prev_spot > 0:
                price_change_pct = abs(spot - prev_spot) / prev_spot
                if price_change_pct < 0.0005:
                    logger.debug(f"Skipping noisy snapshot for {symbol}: change {price_change_pct:.4%}")
                    return 0
            
            self.last_spot_prices[symbol] = spot
            
            # Phase 2: Expected Move Safety (Clamp to min 20)
            expected_move = max(expected_move, 20.0)
            
            # Phase 3: Signal Cooldown (60 seconds to allow steady signal flow)
            now = time.time()
            if symbol in self.last_signal_times:
                if now - self.last_signal_times[symbol] < 60:
                    logger.debug(f"Signal cooldown active for {symbol}")
                    return 0
            
            if spot <= 0:
                logger.warning(f"Rejecting snapshot for {symbol}: spot_price {spot} <= 0")
                return 0
            if expected_move <= 0:
                logger.warning(f"Rejecting snapshot for {symbol}: expected_move {expected_move} <= 0")
                return 0
            if total_call_oi == 0 and total_put_oi == 0:
                logger.warning(f"Rejecting snapshot for {symbol}: both call and put OI are zero")
                return 0

            # Get active formulas
            formulas = await self.get_active_formulas()
            if not formulas:
                logger.warning("No active formulas found")
                return 0
            
            signals_generated = 0
            
            # Evaluate each formula
            for formula in formulas:
                matches, signal, confidence, reason = self.evaluate_formula_conditions(formula, market_data)
                
                if matches and signal in ["BUY", "SELL"]:
                    atm = market_data['atm_strike']
                    
                    # Phase 2: Improved Trade Setup
                    # floor SL distance at 15 points, Target at 30 points
                    sl_dist = max(expected_move * 0.25, 15)
                    tp_dist = max(expected_move * 0.5, 30)
                    # Reward/Risk is at least 30/15 = 2.0 (>= 1.5)
                    
                    strike = atm
                    entry = spot
                    direction = "CALL" if signal == "BUY" else "PUT"
                    
                    if direction == "CALL":
                        stop_loss = entry - sl_dist
                        target = entry + tp_dist
                    else:
                        stop_loss = entry + sl_dist
                        target = entry - tp_dist

                    # Capture option premium
                    entry_premium = 0.0
                    try:
                        from app.services.option_chain_builder import option_chain_builder
                        right = "CE" if direction == "CALL" else "PE"
                        entry_premium = option_chain_builder.get_option_ltp("NIFTY", strike, right)
                    except Exception as ex:
                        logger.error(f"Failed to fetch option premium: {ex}")

                    # Store prediction
                    success = await self.prediction_service.store_prediction(
                        formula_id=str(formula['id']),
                        signal=signal,
                        confidence=confidence,
                        spot=spot,
                        snapshot_id=market_data['snapshot_id'],
                        strike=strike,
                        direction=direction,
                        entry=entry,
                        stop_loss=stop_loss,
                        target=target,
                        reason=reason,
                        entry_premium=entry_premium,
                        expected_move=expected_move # Pass to store in metadata
                    )
                    
                    if success:
                        self.last_signal_times[symbol] = time.time()
                        signals_generated += 1
                        logger.info(f"Signal generated: {formula['name']} -> {signal} @ {spot} (Reason: {reason})")
                        
                        # Log AI event
                        await self.log_ai_event(
                            event_type="SIGNAL_GENERATED",
                            description=f"Formula {formula['name']} generated {signal} signal: {reason}"
                        )
                    else:
                        logger.error(f"Failed to store prediction for formula {formula['id']}")
            logger.info(f"Signal generation completed. Generated {signals_generated} signals")
            return signals_generated
        except Exception as e:
            logger.error(f"Error in signal generation: {e}")
            return 0
            
    async def get_latest_signal(self, symbol: str = "NIFTY") -> Optional[Dict]:
        """Fetch the most recent AI signal for broadcast"""
        try:
            query = """
                SELECT signal, confidence, strike, direction, entry, stop_loss, target, timestamp
                FROM ai_signal_logs
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            result = await self.db.fetch_one(query, (symbol,))
            if result:
                return {
                    'signal': result[0],
                    'confidence': result[1],
                    'strike': result[2],
                    'direction': result[3],
                    'entry': result[4],
                    'stop_loss': result[5],
                    'target': result[6],
                    'timestamp': result[7]
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching latest signal: {e}")
            return None
    
    async def log_ai_event(self, event_type: str, description: str):
        """Log AI events to ai_event_log table"""
        try:
            query = """
                INSERT INTO ai_event_log (event_type, description)
                VALUES (%s, %s)
            """
            
            params = (event_type, description)
            await self.db.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Error logging AI event: {e}")

# Global signal engine instance
ai_signal_engine = AISignalEngine()
