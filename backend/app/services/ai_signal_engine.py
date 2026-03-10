"""
AI Signal Engine for StrikeIQ

Responsibilities:
- Read latest option chain snapshot
- Evaluate formulas from formula_master
- Generate signals when conditions match
- Insert signals into prediction_log
"""
import logging
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
        
    def get_latest_market_snapshot(self) -> Optional[Dict]:
        """Get the latest market snapshot for AI analysis"""
        try:
            query = """
                SELECT symbol, spot_price, pcr, total_call_oi, total_put_oi, atm_strike, timestamp
                FROM market_snapshot
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            result = self.db.fetch_one(query)
            
            if result:
                return {
                    'symbol': result[0],
                    'spot_price': result[1],
                    'pcr': result[2],
                    'total_call_oi': result[3],
                    'total_put_oi': result[4],
                    'atm_strike': result[5],
                    'timestamp': result[6]
                }
            else:
                logger.warning("No market snapshot found")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching market snapshot: {e}")
            return None
    
    def get_active_formulas(self) -> List[Dict]:
        """Get all active formulas from formula_master"""
        try:
            query = """
                SELECT id, formula_name, formula_type, conditions, confidence_threshold, is_active
                FROM formula_master
                WHERE is_active = TRUE
                ORDER BY id
            """
            
            results = self.db.fetch_query(query)
            
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
    
    def evaluate_formula_conditions(self, formula: Dict, market_data: Dict) -> Tuple[bool, str, float]:
        """
        Evaluate if formula conditions match current market data
        
        Returns:
            Tuple of (matches, signal, confidence)
        """
        try:
            conditions = formula['conditions']
            confidence_threshold = formula['confidence_threshold']
            
            # Parse conditions (simplified for demo - in production, use proper condition parser)
            # Example conditions: "PCR > 1.2 AND spot_price > 20000"
            
            matches = False
            signal = "HOLD"
            confidence = 0.0
            
            # PCR-based signals
            if 'PCR' in conditions:
                pcr = market_data.get('pcr', 0)
                # Convert to float if string with validation
                if isinstance(pcr, str):
                    try:
                        pcr = float(pcr)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid PCR value: {pcr}, using 0.0")
                        pcr = 0.0
                elif not isinstance(pcr, (int, float)):
                    logger.warning(f"Invalid PCR type: {type(pcr)}, using 0.0")
                    pcr = 0.0
                else:
                    pcr = float(pcr or 0)  # Ensure numeric
                        
                if '>' in conditions and '1.2' in conditions and pcr > 1.2:
                    matches = True
                    signal = "BUY"
                    confidence = min(0.9, pcr / 2.0)  # Scale confidence based on PCR value
                elif '<' in conditions and '0.8' in conditions and pcr < 0.8:
                    matches = True
                    signal = "SELL"
                    confidence = min(0.9, (0.8 - pcr) / 0.8)  # Scale confidence based on distance from 0.8
            
            # OI-based signals
            if 'total_call_oi' in conditions and 'total_put_oi' in conditions:
                call_oi = market_data.get('total_call_oi', 0)
                put_oi = market_data.get('total_put_oi', 0)
                
                # Enforce numeric conversion with validation
                try:
                    call_oi = float(call_oi or 0)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid call_oi value: {call_oi}, using 0.0")
                    call_oi = 0.0
                    
                try:
                    put_oi = float(put_oi or 0)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid put_oi value: {put_oi}, using 0.0")
                    put_oi = 0.0
                
                # Additional validation guards
                if call_oi < 0:
                    logger.warning(f"Negative call_oi detected: {call_oi}, using 0.0")
                    call_oi = 0.0
                    
                if put_oi < 0:
                    logger.warning(f"Negative put_oi detected: {put_oi}, using 0.0")
                    put_oi = 0.0
                
                if call_oi > put_oi * 1.5:  # High call OI relative to put OI
                    matches = True
                    signal = "SELL"
                    confidence = min(0.8, (call_oi - put_oi) / call_oi if call_oi > 0 else 0.0)
                elif put_oi > call_oi * 1.5:  # High put OI relative to call OI
                    matches = True
                    signal = "BUY"
                    confidence = min(0.8, (put_oi - call_oi) / put_oi if put_oi > 0 else 0.0)
            
            # Apply confidence threshold
            if matches and confidence >= confidence_threshold:
                return True, signal, confidence
            else:
                return False, "HOLD", 0.0
                
        except Exception as e:
            logger.error(f"Error evaluating formula conditions: {e}")
            return False, "HOLD", 0.0
    
    def generate_signals(self) -> int:
        """
        Generate signals based on current market data and active formulas
        
        Returns:
            Number of signals generated
        """
        try:
            # Get latest market data
            market_data = self.get_latest_market_snapshot()
            if not market_data:
                logger.warning("No market data available for signal generation")
                return 0
            
            # AI Validation: Check option chain and OI data
            if not validate_option_chain(market_data):
                logger.warning("AI disabled: invalid option chain")
                return 0
            
            if not validate_oi(market_data):
                logger.warning("AI disabled: invalid OI data")
                return 0
            
            # Get active formulas
            formulas = self.get_active_formulas()
            if not formulas:
                logger.warning("No active formulas found")
                return 0
            
            signals_generated = 0
            
            # Evaluate each formula
            for formula in formulas:
                matches, signal, confidence = self.evaluate_formula_conditions(formula, market_data)
                
                if matches and signal in ["BUY", "SELL"]:
                    # Store prediction
                    success = self.prediction_service.store_prediction(
                        formula_id=str(formula['id']),
                        signal=signal,
                        confidence=confidence,
                        spot=market_data['spot_price']
                    )
                    
                    if success:
                        signals_generated += 1
                        logger.info(f"Signal generated: {formula['name']} -> {signal} @ {market_data['spot_price']} (confidence: {confidence})")
                        
                        # Log AI event
                        self.log_ai_event(
                            event_type="SIGNAL_GENERATED",
                            description=f"Formula {formula['name']} generated {signal} signal with confidence {confidence:.2f}"
                        )
                    else:
                        logger.error(f"Failed to store prediction for formula {formula['id']}")
            
            logger.info(f"Signal generation completed. Generated {signals_generated} signals")
            return signals_generated
            
        except Exception as e:
            logger.error(f"Error in signal generation: {e}")
            return 0
    
    def log_ai_event(self, event_type: str, description: str):
        """Log AI events to ai_event_log table"""
        try:
            query = """
                INSERT INTO ai_event_log (event_type, description)
                VALUES (%s, %s)
            """
            
            params = (event_type, description)
            self.db.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Error logging AI event: {e}")

# Global signal engine instance
ai_signal_engine = AISignalEngine()
