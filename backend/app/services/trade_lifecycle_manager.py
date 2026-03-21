"""
Trade Lifecycle Manager for StrikeIQ
Manages active trades and automatic outcome tracking
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)

class TradeLifecycleManager:
    """Manages trade lifecycle from entry to exit"""
    
    def __init__(self):
        self.active_trades = {}  # In-memory store for active trades
        self.db_pool = None
        logger.info("TradeLifecycleManager initialized")
    
    async def initialize_db(self, db_pool):
        """Initialize database connection"""
        self.db_pool = db_pool
        logger.info("TradeLifecycleManager database initialized")
    
    async def insert_trade(self, symbol: str, direction: str, entry_price: float, 
                        stop_loss: float, target: float, confidence: float, 
                        score: float) -> Optional[int]:
        """Insert new trade into outcome_log and track as active"""
        try:
            if not self.db_pool:
                logger.warning("Database not initialized")
                return None
            
            async with self.db_pool.acquire() as conn:
                # Insert trade
                query = """
                INSERT INTO outcome_log (symbol, direction, entry_price, stop_loss, target, 
                                    confidence, evaluation_method)
                VALUES ($1, $2, $3, $4, $5, $6, 'PROBABILISTIC_SCORE')
                RETURNING id
                """
                trade_id = await conn.fetchval(
                    query, symbol, direction, entry_price, stop_loss, 
                    target, confidence, score
                )
                
                # Track as active trade
                self.active_trades[trade_id] = {
                    'symbol': symbol,
                    'direction': direction,
                    'entry': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'confidence': confidence,
                    'score': score,
                    'status': 'OPEN',
                    'created_at': datetime.now()
                }
                
                logger.info(f"[TRADE] INSERTED: {symbol} {direction}")
                
                return trade_id
                
        except Exception as e:
            logger.error(f"Failed to insert trade: {e}")
            return None
    
    async def check_price_updates(self, symbol: str, current_price: float):
        """Check if any active trades hit target or stop loss"""
        try:
            trades_to_close = []
            
            for trade_id, trade in self.active_trades.items():
                if trade['symbol'] != symbol:
                    continue
                
                entry = trade['entry']
                stop_loss = trade['stop_loss']
                target = trade['target']
                direction = trade['direction']
                
                # Check for exit conditions
                result = None
                exit_price = current_price
                
                if direction in ['BUY_CALL', 'BUY_CE']:
                    # For long positions
                    if current_price >= target:
                        result = 'WIN'
                        exit_price = target
                    elif current_price <= stop_loss:
                        result = 'LOSS'
                        exit_price = stop_loss
                elif direction in ['BUY_PUT', 'BUY_PE']:
                    # For short positions (simplified)
                    if current_price <= target:
                        result = 'WIN'
                        exit_price = target
                    elif current_price >= stop_loss:
                        result = 'LOSS'
                        exit_price = stop_loss
                
                if result:
                    trades_to_close.append((trade_id, trade, result, exit_price))
            
            # Close trades
            for trade_id, trade, result, exit_price in trades_to_close:
                await self._close_trade(trade_id, trade, result, exit_price)
                
        except Exception as e:
            logger.error(f"Failed to check price updates: {e}")
    
    async def _close_trade(self, trade_id: int, trade: Dict[str, Any], 
                         result: str, exit_price: float):
        """Close trade and update outcome_log"""
        try:
            if not self.db_pool:
                return
            
            async with self.db_pool.acquire() as conn:
                # Update trade outcome
                query = """
                UPDATE outcome_log 
                SET outcome = $1, evaluation_time = NOW()
                WHERE id = $2
                """
                await conn.execute(query, result, trade_id)
                
                # Calculate PnL (simplified)
                pnl = 0.0
                if result == 'WIN':
                    pnl = abs(exit_price - trade['entry'])
                elif result == 'LOSS':
                    pnl = -abs(trade['entry'] - exit_price)
                
                # Remove from active trades
                if trade_id in self.active_trades:
                    del self.active_trades[trade_id]
                
                logger.info(f"[TRADE CLOSED] {trade['symbol']} {trade['direction']}")
                
        except Exception as e:
            logger.error(f"Failed to close trade {trade_id}: {e}")
    
    def get_active_trades(self) -> Dict[int, Dict[str, Any]]:
        """Get all active trades"""
        return self.active_trades.copy()
    
    def get_active_trade_count(self) -> int:
        """Get count of active trades"""
        return len(self.active_trades)

# Global instance
trade_lifecycle_manager = TradeLifecycleManager()
