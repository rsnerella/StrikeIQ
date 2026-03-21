"""
Paper Trade Engine for StrikeIQ

Responsibilities:
- Create paper trade entries when predictions are made
- Monitor open trades and exit after configurable time window
- Calculate PnL and update trade status
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ai.ai_db import ai_db

logger = logging.getLogger(__name__)

class PaperTradeEngine:
    def __init__(self):
        self.db = ai_db
        self.trade_duration_minutes = 30  # Configurable trade duration
        self.default_quantity = 75  # Default lot size for NIFTY options
        
    async def get_latest_predictions(self) -> List[Dict]:
        """Get latest predictions that don't have paper trades yet"""
        try:
            query = """
                SELECT p.id, p.formula_id, p.signal, p.confidence, p.spot_price, p.timestamp
                FROM ai_signal_logs p
                LEFT JOIN paper_trade_log pt ON p.id = pt.prediction_id
                WHERE p.timestamp >= NOW() - INTERVAL '1 hour'
                AND pt.prediction_id IS NULL
                ORDER BY p.timestamp DESC
                LIMIT 50
            """
            
            results = await self.db.fetch_query(query)
            
            predictions = []
            for row in results:
                predictions.append({
                    'id': row[0],
                    'formula_id': row[1],
                    'signal': row[2],
                    'confidence': row[3],
                    'nifty_spot': row[4],
                    'prediction_time': row[5]
                })
                
            logger.info(f"Found {len(predictions)} predictions without paper trades")
            return predictions
            
        except Exception as e:
            logger.error(f"Error fetching latest predictions: {e}")
            return []
    
    def get_option_price(self, strike_price: float, option_type: str, spot_price: float) -> float:
        """
        Simulate option pricing based on distance from ATM
        
        In production, this would fetch real option prices from the market
        """
        try:
            # Simple distance-based pricing model
            distance_from_spot = abs(strike_price - spot_price)
            
            # Base price decreases with distance from ATM
            if distance_from_spot <= 100:
                base_price = 50.0
            elif distance_from_spot <= 200:
                base_price = 30.0
            elif distance_from_spot <= 500:
                base_price = 15.0
            else:
                base_price = 5.0
            
            # Add some randomness for realism
            import random
            price_variation = random.uniform(-5.0, 5.0)
            
            final_price = max(1.0, base_price + price_variation)
            
            return round(final_price, 2)
            
        except Exception as e:
            logger.error(f"Error calculating option price: {e}")
            return 50.0  # Default fallback price
    
    def select_strike_price(self, signal: str, spot_price: float) -> Tuple[float, str]:
        """
        Select appropriate strike price and option type based on signal
        
        Returns:
            Tuple of (strike_price, option_type)
        """
        try:
            # Round spot to nearest 50 for NIFTY strikes
            rounded_spot = round(spot_price / 50) * 50
            
            if signal == "BUY":
                # For BUY signals, use Call options
                # Select OTM strike (slightly above current spot)
                strike_price = rounded_spot + 50
                option_type = "CE"
            else:  # SELL
                # For SELL signals, use Put options  
                # Select OTM strike (slightly below current spot)
                strike_price = rounded_spot - 50
                option_type = "PE"
            
            return strike_price, option_type
            
        except Exception as e:
            logger.error(f"Error selecting strike price: {e}")
            return rounded_spot, "CE"  # Fallback
    
    async def create_paper_trade(self, prediction: Dict) -> bool:
        """
        Create a paper trade entry for a prediction
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Select strike price and option type
            strike_price, option_type = self.select_strike_price(
                prediction['signal'], 
                prediction['nifty_spot']
            )
            
            # Get entry price
            entry_price = self.get_option_price(
                strike_price, 
                option_type, 
                prediction['nifty_spot']
            )
            
            # Insert paper trade
            query = """
                INSERT INTO paper_trade_log 
                (prediction_id, symbol, strike_price, entry_price, quantity)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            
            params = (
                prediction['id'],
                'NIFTY',
                strike_price,
                entry_price,
                self.default_quantity
            )
            
            result = await self.db.fetch_one(query, params)
            
            if result:
                trade_id = result[0]
                logger.debug(f"Paper trade created: ID {trade_id}, {option_type} {strike_price} @ {entry_price}")
                
                # Log AI event
                await self.log_ai_event(
                    event_type="PAPER_TRADE_OPENED",
                    description=f"Opened paper trade: {option_type} {strike_price} @ {entry_price} for prediction {prediction['id']}"
                )
                
                return True
            else:
                logger.error(f"Failed to create paper trade for prediction {prediction['id']}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating paper trade: {e}")
            return False
    
    async def get_open_trades(self) -> List[Dict]:
        """Get all open paper trades that need to be monitored"""
        try:
            query = """
                SELECT id, prediction_id, symbol, strike_price, option_type, 
                       entry_price, quantity, timestamp
                FROM paper_trade_log
                WHERE trade_status = 'OPEN'
                AND timestamp <= NOW() - INTERVAL '5 minutes'
                ORDER BY timestamp ASC
                LIMIT 100
            """
            
            results = await self.db.fetch_query(query)
            
            open_trades = []
            for row in results:
                open_trades.append({
                    'id': row[0],
                    'prediction_id': row[1],
                    'symbol': row[2],
                    'strike_price': row[3],
                    'option_type': row[4],
                    'entry_price': row[5],
                    'quantity': row[6],
                    'timestamp': row[7]
                })
                
            logger.debug(f"Found {len(open_trades)} open trades to monitor")
            return open_trades
            
        except Exception as e:
            logger.error(f"Error fetching open trades: {e}")
            return []
    
    async def exit_paper_trade(self, trade: Dict) -> bool:
        """
        Exit a paper trade and calculate PnL
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current market price for exit
            # In production, fetch real market price
            exit_price = self.get_option_price(
                trade['strike_price'],
                trade['option_type'],
                trade['entry_price']  # Use entry price as proxy for spot
            )
            
            # Calculate PnL
            if trade['option_type'] == 'CE':
                # For Call options: profit if price goes up
                pnl = (exit_price - trade['entry_price']) * trade['quantity']
            else:  # PE
                # For Put options: profit if price goes down
                pnl = (trade['entry_price'] - exit_price) * trade['quantity']
            
            # Update trade record
            query = """
                UPDATE paper_trade_log
                SET exit_price = %s, pnl = %s, trade_status = 'CLOSED', exit_time = %s
                WHERE id = %s
            """
            
            params = (exit_price, pnl, datetime.now(), trade['id'])
            success = await self.db.execute_query(query, params)
            
            if success:
                logger.debug(f"Paper trade closed: ID {trade['id']}, PnL: {pnl:.2f}")
                
                # Update ai_trade_history
                await self._update_ai_trade_history(trade, exit_price, pnl)

                # Log AI event
                self.log_ai_event(
                    event_type="PAPER_TRADE_CLOSED",
                    description=f"Closed paper trade {trade['id']} with PnL: {pnl:.2f}"
                )
                
                return True
            else:
                logger.error(f"Failed to close paper trade {trade['id']}")
                return False
                
        except Exception as e:
            logger.error(f"Error exiting paper trade: {e}")
            return False

    async def _update_ai_trade_history(self, trade: Dict, exit_price: float, pnl: float):
        """Update ai_trade_history when a trade closes"""
        try:
            result = "WIN" if pnl > 0 else "LOSS"
            
            # Update the latest open matching trade
            update_query = """
                UPDATE ai_trade_history
                SET exit_price = %s, pnl = %s, result = %s, closed_at = %s
                WHERE symbol = %s AND strike = %s AND closed_at IS NULL
            """
            
            params = (
                exit_price, 
                pnl, 
                result, 
                datetime.now(), 
                trade['symbol'], 
                trade['strike_price']
            )
            
            await self.db.execute_query(update_query, params)
            logger.info(f"Updated ai_trade_history for {trade['symbol']} {trade['strike_price']}")
            
        except Exception as e:
            logger.error(f"Error updating ai_trade_history: {e}")
    
    async def monitor_open_trades(self) -> int:
        """
        Monitor open trades and exit those that have reached their time window
        
        Returns:
            Number of trades closed
        """
        try:
            open_trades = await self.get_open_trades()
            trades_closed = 0
            
            for trade in open_trades:
                # Check if trade has reached its duration
                entry_time = trade['timestamp']
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                
                time_elapsed = datetime.now() - entry_time
                
                if time_elapsed >= timedelta(minutes=self.trade_duration_minutes):
                    # Exit the trade
                    if await self.exit_paper_trade(trade):
                        trades_closed += 1
            
            logger.debug(f"Trade monitoring completed. Closed {trades_closed} trades")
            return trades_closed
            
        except Exception as e:
            logger.error(f"Error monitoring open trades: {e}")
            return 0
    
    async def process_new_predictions(self) -> int:
        """
        Process new predictions and create paper trades
        
        Returns:
            Number of paper trades created
        """
        try:
            predictions = await self.get_latest_predictions()
            trades_created = 0
            
            for prediction in predictions:
                if await self.create_paper_trade(prediction):
                    trades_created += 1
            
            logger.debug(f"New prediction processing completed. Created {trades_created} paper trades")
            return trades_created
            
        except Exception as e:
            logger.error(f"Error processing new predictions: {e}")
            return 0
    
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

# Global paper trade engine instance
paper_trade_engine = PaperTradeEngine()
