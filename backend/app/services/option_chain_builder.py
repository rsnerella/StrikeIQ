"""
Option Chain Builder for StrikeIQ
Maintains in-memory option chain and produces snapshots
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import bisect

from app.services.oi_buildup_engine import OIBuildupEngine

logger = logging.getLogger(__name__)

@dataclass
class OptionData:
    """Data structure for a single option"""
    strike: float
    ltp: float = 0.0
    oi: int = 0
    volume: int = 0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class ChainSnapshot:
    """Snapshot of option chain for broadcasting"""
    symbol: str
    spot: float
    atm_strike: float
    expiry: str
    strikes: List[Dict[str, Any]]
    timestamp: int

class OptionChainBuilder:
    """Builds and maintains real-time option chains"""
    
    def __init__(self):
        # Symbol -> {strike -> {CE/PE -> OptionData}}
        self.chains: Dict[str, Dict[float, Dict[str, OptionData]]] = {}
        
        # Symbol -> current spot price
        self.spot_prices: Dict[str, float] = {}
        
        # Symbol -> last snapshot timestamp
        self.last_snapshots: Dict[str, datetime] = {}
        
        # Background task for periodic snapshots
        self._snapshot_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Default expiry (next Thursday)
        self.default_expiry = self._get_next_expiry()
        
        # Initialize OI Buildup Engine
        self.oi_buildup_engine = OIBuildupEngine()
        logger.info("Option Chain Builder initialized with OI Buildup Engine")
    
    def _get_next_expiry(self) -> str:
        """Get next Thursday expiry date"""
        today = datetime.now().date()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0:
            days_until_thursday = 7  # Next Thursday if today is Thursday
        
        expiry_date = today + timedelta(days=days_until_thursday)
        return expiry_date.strftime("%Y-%m-%d")
    
    async def start(self):
        """Start the background snapshot task"""
        if self._running:
            return
        
        self._running = True
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())
        logger.info("Option chain builder started")
    
    async def stop(self):
        """Stop the background task"""
        self._running = False
        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
        logger.info("Option chain builder stopped")
    
    async def _snapshot_loop(self):
        """Periodic snapshot generation"""
        while self._running:
            try:
                await asyncio.sleep(0.5)  # 500ms intervals
                await self._generate_snapshots()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in snapshot loop: {e}")
    
    async def _generate_snapshots(self):
        """Generate snapshots for all active symbols"""
        current_time = datetime.now()
        
        for symbol in list(self.spot_prices.keys()):
            # Check if we need to generate snapshot
            last_snapshot = self.last_snapshots.get(symbol, datetime.min)
            if (current_time - last_snapshot).total_seconds() >= 0.5:
                snapshot = self._create_snapshot(symbol)
                if snapshot:
                    self.last_snapshots[symbol] = current_time
                    # Broadcast snapshot
                    await self._broadcast_snapshot(snapshot)
    
    def _create_snapshot(self, symbol: str) -> Optional[ChainSnapshot]:
        """Create a snapshot for the given symbol"""
        try:
            if symbol not in self.chains or symbol not in self.spot_prices:
                return None
            
            spot = self.spot_prices[symbol]
            chain = self.chains[symbol]
            
            if not chain:
                return None
            
            # Find ATM strike
            atm_strike = self._find_atm_strike(spot, list(chain.keys()))
            
            # Build strikes list
            strikes = []
            for strike in sorted(chain.keys()):
                strike_data = chain[strike]
                
                call_data = strike_data.get("CE")
                put_data = strike_data.get("PE")
                
                strike_info = {
                    "strike": strike,
                    "call_oi": call_data.oi if call_data else 0,
                    "call_ltp": call_data.ltp if call_data else 0,
                    "call_volume": call_data.volume if call_data else 0,
                    "put_oi": put_data.oi if put_data else 0,
                    "put_ltp": put_data.ltp if put_data else 0,
                    "put_volume": put_data.volume if put_data else 0
                }
                
                strikes.append(strike_info)
            
            return ChainSnapshot(
                symbol=symbol,
                spot=spot,
                atm_strike=atm_strike,
                expiry=self.default_expiry,
                strikes=strikes,
                timestamp=int(datetime.now().timestamp())
            )
            
        except Exception as e:
            logger.error(f"Error creating snapshot for {symbol}: {e}")
            return None
    
    def _find_atm_strike(self, spot: float, strikes: List[float]) -> float:
        """Find the ATM strike closest to spot"""
        if not strikes:
            return spot
        
        # Use bisect to find insertion point
        sorted_strikes = sorted(strikes)
        idx = bisect.bisect_left(sorted_strikes, spot)
        
        if idx == 0:
            return sorted_strikes[0]
        elif idx >= len(sorted_strikes):
            return sorted_strikes[-1]
        else:
            # Choose closer strike
            lower = sorted_strikes[idx - 1]
            upper = sorted_strikes[idx]
            return lower if (spot - lower) < (upper - spot) else upper
    
    async def _broadcast_snapshot(self, snapshot: ChainSnapshot):
        """Broadcast snapshot to WebSocket clients"""
        try:
            from app.core.ws_manager import manager
            
            message = {
                "type": "option_chain_update",
                "symbol": snapshot.symbol,
                "timestamp": snapshot.timestamp,
                "data": {
                    "symbol": snapshot.symbol,
                    "spot": snapshot.spot,
                    "atm_strike": snapshot.atm_strike,
                    "expiry": snapshot.expiry,
                    "strikes": snapshot.strikes
                }
            }
            
            await manager.broadcast(message)
            logger.debug(f"Broadcasted option chain snapshot for {snapshot.symbol}")
            
        except Exception as e:
            logger.error(f"Error broadcasting snapshot: {e}")
    
    def update_index_price(self, symbol: str, price: float):
        """Update index spot price"""
        self.spot_prices[symbol] = price
        logger.debug(f"Updated {symbol} spot price to {price}")
    
    def update_option_tick(self, symbol: str, strike: float, right: str, ltp: float, oi: int = 0, volume: int = 0):
        """Update option data from tick"""
        try:
            logger.info(f"OPTION TICK → {symbol}_{strike}{right} | LTP={ltp} | OI={oi} | Volume={volume}")
            
            if symbol not in self.chains:
                self.chains[symbol] = {}
            
            if strike not in self.chains[symbol]:
                self.chains[symbol][strike] = {}
            
            if right not in self.chains[symbol][strike]:
                self.chains[symbol][strike][right] = OptionData(strike=strike)
            
            option_data = self.chains[symbol][strike][right]
            option_data.ltp = ltp
            option_data.oi = oi
            option_data.volume = volume
            option_data.last_update = datetime.now()
            
            # Detect OI buildup signal
            instrument_key = f"{symbol}_{strike}{right}"
            signal = self.oi_buildup_engine.detect(instrument_key, ltp, oi)
            
            if signal:
                logger.info(f"OI SIGNAL → {instrument_key} → {signal}")
            
            logger.debug(f"Updated {symbol} {strike} {right}: LTP={ltp}, OI={oi}")
            
        except Exception as e:
            logger.error(f"Error updating option tick: {e}")
    
    def get_chain(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current chain data for a symbol"""
        if symbol not in self.chains or symbol not in self.spot_prices:
            return None
        
        snapshot = self._create_snapshot(symbol)
        if snapshot:
            return {
                "symbol": snapshot.symbol,
                "spot": snapshot.spot,
                "atm_strike": snapshot.atm_strike,
                "expiry": snapshot.expiry,
                "strikes": snapshot.strikes,
                "timestamp": snapshot.timestamp
            }
        
        return None

# Global instance
option_chain_builder = OptionChainBuilder()
