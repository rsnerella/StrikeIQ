"""
Live Market State Manager
Manages in-memory market data state for real-time processing
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class InstrumentData:
    """Data structure for individual instrument"""
    instrument_key: str
    ltp: Optional[float] = None
    ltt: Optional[str] = None
    ltq: Optional[int] = None
    cp: Optional[float] = None  # Close price
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    iv: Optional[float] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    last_update: Optional[datetime] = None

@dataclass
class StrikeData:
    """Data structure for option strike (both CE and PE)"""
    strike: float
    call: Optional[InstrumentData] = None
    put: Optional[InstrumentData] = None
    last_update: Optional[datetime] = None

@dataclass
class SymbolMarketState:
    """Data structure for symbol market state with separated REST and WS data"""
    symbol: str
    
    # REST snapshot data (from API calls)
    rest_spot_price: Optional[float] = None
    rest_spot_instrument_key: Optional[str] = None
    rest_spot_change: Optional[float] = 0
    rest_spot_change_percent: Optional[float] = 0
    rest_option_chain: Dict[float, StrikeData] = field(default_factory=dict)
    rest_ltp_snapshot: Dict[str, float] = field(default_factory=dict)
    rest_last_update: Optional[datetime] = None
    
    # WebSocket tick data (from live streaming)
    ws_tick_price: Optional[float] = None
    ws_last_update_ts: Optional[datetime] = None
    ws_strikes: Dict[float, StrikeData] = field(default_factory=dict)
    ws_tick_count: int = 0  # Track number of WebSocket ticks received
    
    # Sticky ATM calculation
    current_atm_strike: Optional[float] = None
    atm_last_updated: Optional[datetime] = None
    
    # Combined/aggregated data
    strikes: Dict[float, StrikeData] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    total_oi_calls: int = 0
    total_oi_puts: int = 0
    
    # Legacy compatibility field for LiveStructuralEngine
    spot: Optional[float] = None
    
    # Current expiry for option chain
    expiry: Optional[str] = None
    
    def get_atm_strike(self) -> Optional[float]:
        """Get sticky ATM strike (prevents oscillation from frequent WS ticks)"""
        # Use WebSocket tick price if available, otherwise fallback to REST spot price
        current_spot = self.ws_tick_price if self.ws_tick_price is not None else self.rest_spot_price
        
        if not current_spot:
            return None
        
        # If we already have a sticky ATM strike, check if we need to update it
        if self.current_atm_strike is not None:
            # Calculate strike gap from REST option chain
            strike_gap = self._calculate_strike_gap()
            
            # Only update ATM if price moved more than half the strike gap
            if abs(current_spot - self.current_atm_strike) > (strike_gap / 2):
                # Find new ATM from REST option chain
                new_atm = self._find_nearest_strike(current_spot)
                if new_atm != self.current_atm_strike:
                    self.current_atm_strike = new_atm
                    self.atm_last_updated = datetime.now(timezone.utc)
                    logger.debug(f"ATM strike updated: {self.current_atm_strike} (spot: {current_spot})")
            
            return self.current_atm_strike
        
        # First time calculation - find nearest strike from REST option chain
        self.current_atm_strike = self._find_nearest_strike(current_spot)
        self.atm_last_updated = datetime.now(timezone.utc)
        logger.debug(f"Initial ATM strike set: {self.current_atm_strike} (spot: {current_spot})")
        
        return self.current_atm_strike
    
    def _calculate_strike_gap(self) -> float:
        """Calculate the difference between adjacent strikes in REST option chain"""
        if not self.rest_option_chain or len(self.rest_option_chain) < 2:
            return 50.0  # Default strike gap for NIFTY/BANKNIFTY
        
        # Get sorted strikes from REST option chain
        sorted_strikes = sorted(self.rest_option_chain.keys())
        
        # Find minimum difference between adjacent strikes
        min_gap = float('inf')
        for i in range(len(sorted_strikes) - 1):
            gap = abs(sorted_strikes[i + 1] - sorted_strikes[i])
            if gap > 0:  # Ignore duplicate strikes
                min_gap = min(min_gap, gap)
        
        return min_gap if min_gap != float('inf') else 50.0
    
    def _find_nearest_strike(self, spot_price: float) -> Optional[float]:
        """Find nearest strike to spot price from REST option chain"""
        if not self.rest_option_chain:
            return None
        
        # Find strike with minimum absolute difference from spot price
        return min(self.rest_option_chain.keys(), key=lambda x: abs(x - spot_price))
    
    def get_strike_range(self, count: int = 10) -> List[float]:
        """Get range of strikes around ATM"""
        atm = self.get_atm_strike()
        if not atm:
            return []
        
        all_strikes = sorted(self.strikes.keys())
        atm_idx = all_strikes.index(atm)
        
        start_idx = max(0, atm_idx - count)
        end_idx = min(len(all_strikes), atm_idx + count + 1)
        
        return all_strikes[start_idx:end_idx]

class MarketStateManager:
    """
    Manages live market state across all symbols
    Thread-safe and optimized for real-time updates
    """
    
    def __init__(self):
        self.market_states: Dict[str, SymbolMarketState] = {}
        self._lock = asyncio.Lock()
        
    async def get_symbol_state(self, symbol: str) -> Optional[SymbolMarketState]:
        """Get market state for a symbol"""
        async with self._lock:
            return self.market_states.get(symbol)
    
    async def initialize_symbol(self, symbol: str) -> None:
        """
        Initialize symbol state to prevent None returns during WebSocket bootstrap
        """
        async with self._lock:
            if symbol not in self.market_states:
                self.market_states[symbol] = SymbolMarketState(symbol=symbol)
                logger.info(f"Initialized market state for {symbol}")
            else:
                logger.debug(f"Market state already exists for {symbol}")
    
    async def update_instrument_data(self, symbol: str, instrument_key: str, data: Dict[str, Any]) -> None:
        """
        Update data for a specific instrument
        """
        async with self._lock:
            # Get or create symbol state
            if symbol not in self.market_states:
                self.market_states[symbol] = SymbolMarketState(symbol=symbol)
            
            state = self.market_states[symbol]
            state.last_update = datetime.now(timezone.utc)
            
            # Increment WebSocket tick counter for live data updates
            if data.get("ltp") or data.get("last_price"):
                state.ws_tick_count += 1
            
            # Parse instrument key to determine type
            instrument_type = self._parse_instrument_type(instrument_key)
            
            if instrument_type == "spot":
                # Update spot price - handle both ltp and last_price formats
                spot_price = data.get("ltp") or data.get("last_price")
                if spot_price:
                    # Calculate change from previous spot price
                    old_spot = state.spot
                    change = spot_price - old_spot if old_spot else 0
                    change_percent = (change / old_spot * 100) if old_spot and old_spot != 0 else 0
                    
                    state.spot = float(spot_price)
                    state.spot_instrument_key = instrument_key
                    state.spot_change = change
                    state.spot_change_percent = change_percent
                    state.last_update = datetime.now(timezone.utc)
                    logger.debug(f"Updated spot price for {symbol}: {spot_price} (change: {change:+.2f}, {change_percent:+.2f}%)")
                else:
                    logger.warning(f"No spot price found in data for {symbol}: {data}")
                
            elif instrument_type in ["call", "put"]:
                # Update option data
                strike = self._extract_strike_from_key(instrument_key)
                if strike:
                    # Create strike data if not exists
                    if strike not in state.strikes:
                        state.strikes[strike] = StrikeData(strike=strike)
                    
                    strike_data = state.strikes[strike]
                    
                    # Create instrument data
                    instrument_data = InstrumentData(
                        instrument_key=instrument_key,
                        ltp=data.get("ltp"),
                        ltt=data.get("ltt"),
                        ltq=data.get("ltq"),
                        cp=data.get("cp"),
                        delta=data.get("delta"),
                        gamma=data.get("gamma"),
                        theta=data.get("theta"),
                        vega=data.get("vega"),
                        iv=data.get("iv"),
                        last_update=datetime.now(timezone.utc)
                    )
                    
                    # Update call or put data
                    if instrument_type == "call":
                        strike_data.call = instrument_data
                    else:
                        strike_data.put = instrument_data
                    
                    strike_data.last_update = datetime.now(timezone.utc)
            
            # Recalculate totals
            self._recalculate_totals(state)
    
    def _parse_instrument_type(self, instrument_key: str) -> str:
        """Parse instrument type from key supporting V2 and V3 formats"""
        if "INDEX" in instrument_key:
            return "spot"
        
        # Support V2 (-CE) and V3 (CE)
        key_upper = instrument_key.upper()
        if key_upper.endswith("CE") or key_upper.endswith("-CE"):
            return "call"
        elif key_upper.endswith("PE") or key_upper.endswith("-PE"):
            return "put"
        return "unknown"
    
    def _extract_strike_from_key(self, instrument_key: str) -> Optional[float]:
        """Extract strike price from instrument key supporting V2 and V3"""
        try:
            # Support V2: NFO_FO|25500-CE
            if "-" in instrument_key:
                parts = instrument_key.split("|")
                if len(parts) >= 2:
                    return float(parts[1].split("-")[0])
            
            # Support V3: NSE_FO|NIFTY26FEB22000CE
            # Regex to find numbers immediately preceding CE or PE at the end
            match = re.search(r'(\d+)(?:CE|PE)$', instrument_key.upper())
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None
    
    def _recalculate_totals(self, state: SymbolMarketState) -> None:
        """Recalculate total OI and other aggregates"""
        total_calls = 0
        total_puts = 0
        
        for strike_data in state.strikes.values():
            if strike_data.call and strike_data.call.oi:
                total_calls += strike_data.call.oi
            if strike_data.put and strike_data.put.oi:
                total_puts += strike_data.put.oi
        
        state.total_oi_calls = total_calls
        state.total_oi_puts = total_puts
    
    async def update_spot_price(self, symbol: str, spot_price: float) -> None:
        """
        Update spot price for a symbol
        """
        await self.update_instrument_data(symbol, f"NSE_INDEX|{symbol}", {"ltp": spot_price})
    
    async def update_option_chain(self, symbol: str, option_data: Dict[str, Any]) -> None:
        """
        Update option chain data for a symbol
        """
        # Update each instrument in the option chain
        for instrument_key, data in option_data.items():
            await self.update_instrument_data(symbol, instrument_key, data)
    
    async def update_ltp(self, symbol: str, instrument_key: str, ltp: float) -> None:
        """
        Update LTP for a specific instrument
        """
        await self.update_instrument_data(symbol, instrument_key, {"ltp": ltp})
    
    async def update_expiry(self, symbol: str, new_expiry: str) -> None:
        """
        Update the current expiry for a symbol
        """
        try:
            async with self._lock:
                # Get or create symbol state
                if symbol not in self.market_states:
                    self.market_states[symbol] = SymbolMarketState(symbol=symbol)
                
                state = self.market_states[symbol]
                old_expiry = state.expiry
                state.expiry = new_expiry
                
                logger.info(f"Updated expiry for {symbol}: {old_expiry} -> {new_expiry}")
                
        except Exception as e:
            logger.error(f"Failed to update expiry for {symbol}: {e}")

    async def update_ws_tick_price(self, symbol: str, instrument_key: str, data: Dict[str, Any]) -> None:
        """
        Update market state specifically from internal WebSocket tick events (SINGLETON SYNC)
        """
        async with self._lock:
            if symbol not in self.market_states:
                self.market_states[symbol] = SymbolMarketState(symbol=symbol)
            
            state = self.market_states[symbol]
            state.ws_last_update_ts = datetime.now(timezone.utc)
            state.ws_tick_count += 1
            
            inst_type = self._parse_instrument_type(instrument_key)
            
            if inst_type == "spot":
                val = data.get("ltp")
                if val:
                    state.ws_tick_price = float(val)
                    state.spot = state.ws_tick_price # Compatibility
            elif inst_type in ["call", "put"]:
                strike = self._extract_strike_from_key(instrument_key)
                if strike:
                    if strike not in state.ws_strikes:
                        state.ws_strikes[strike] = StrikeData(strike=strike)
                    
                    strike_data = state.ws_strikes[strike]
                    
                    # Create instrument snapshot
                    inst_data = InstrumentData(
                        instrument_key=instrument_key,
                        ltp=data.get("ltp"),
                        oi=data.get("oi"),
                        volume=data.get("volume"),
                        delta=data.get("delta"),
                        gamma=data.get("gamma"),
                        theta=data.get("theta"),
                        vega=data.get("vega"),
                        iv=data.get("iv"),
                        last_update=datetime.now(timezone.utc)
                    )
                    
                    if inst_type == "call":
                        strike_data.call = inst_data
                    else:
                        strike_data.put = inst_data
                    
                    # Update combined strikes map for builder
                    if strike not in state.strikes:
                        state.strikes[strike] = StrikeData(strike=strike)
                    
                    combined = state.strikes[strike]
                    if inst_type == "call": combined.call = inst_data
                    else: combined.put = inst_data
                    
            state.last_update = datetime.now(timezone.utc)
    
    async def wait_for_snapshot_tick(self, symbol: str, timeout: float = 10.0) -> bool:
        """
        Wait for the second snapshot tick after expiry change
        """
        try:
            state = await self.get_symbol_state(symbol)
            if not state:
                logger.warning(f"No market state for {symbol}")
                return False
            
            # Wait for at least 2 WebSocket ticks to ensure new data is received
            initial_tick_count = getattr(state, 'ws_tick_count', 0)
            target_tick_count = initial_tick_count + 2
            
            start_time = datetime.now(timezone.utc)
            while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
                current_tick_count = getattr(state, 'ws_tick_count', 0)
                if current_tick_count >= target_tick_count:
                    logger.info(f"Received {current_tick_count} ticks for {symbol}, ready for rebuild")
                    return True
                
                await asyncio.sleep(0.5)  # Check every 500ms
            
            logger.warning(f"Timeout waiting for snapshot ticks for {symbol}")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for snapshot tick: {e}")
            return False
    
    async def update_rest_option_chain(self, symbol: str, option_data: Dict[str, Any]) -> None:
        """
        Update REST snapshot option chain data for a symbol
        """
        try:
            async with self._lock:
                # Get or create symbol state
                if symbol not in self.market_states:
                    self.market_states[symbol] = SymbolMarketState(symbol=symbol)
                
                state = self.market_states[symbol]
                state.rest_last_update = datetime.now(timezone.utc)
                
                # Update REST option chain
                for instrument_key, data in option_data.items():
                    instrument_type = self._parse_instrument_type(instrument_key)
                    
                    if instrument_type in ["call", "put"]:
                        strike = self._extract_strike_from_key(instrument_key)
                        if strike:
                            # Create strike data if not exists in REST chain
                            if strike not in state.rest_option_chain:
                                state.rest_option_chain[strike] = StrikeData(strike=strike)
                            
                            strike_data = state.rest_option_chain[strike]
                            
                            # Create instrument data for REST snapshot
                            instrument_data = InstrumentData(
                                instrument_key=instrument_key,
                                ltp=data.get("ltp"),
                                ltt=data.get("ltt"),
                                ltq=data.get("ltq"),
                                cp=data.get("cp"),
                                delta=data.get("delta"),
                                gamma=data.get("gamma"),
                                theta=data.get("theta"),
                                vega=data.get("vega"),
                                iv=data.get("iv"),
                                volume=data.get("volume"),
                                oi=data.get("oi"),
                                last_update=datetime.now(timezone.utc)
                            )
                            
                            # Update call or put data in REST chain
                            if instrument_type == "call":
                                strike_data.call = instrument_data
                            else:
                                strike_data.put = instrument_data
                            
                            strike_data.last_update = datetime.now(timezone.utc)
                
                # Trigger resync notification for any active WebSocket feeds
                # This will cause WebSocket to resubscribe with new instrument list
                logger.info(f"REST option chain updated for {symbol}, triggering WebSocket resync")
                
        except Exception as e:
            logger.error(f"Error updating REST option chain for {symbol}: {e}")

    async def get_live_data_for_frontend(self, symbol: str) -> Dict[str, Any]:
        """
        Get processed data ready for frontend consumption with separated REST and WS data
        """
        state = await self.get_symbol_state(symbol)
        if not state:
            return {}
        
        # Get ATM and surrounding strikes using sticky ATM calculation
        atm_strike = state.get_atm_strike()  # This now uses the sticky ATM logic
        if not atm_strike:
            return {}
        
        # Determine data source: WebSocket stream or REST snapshot fallback
        # Use REST fallback only if WS has no recent ticks (older than 5 seconds)
        ws_fresh = (
            state.ws_last_update_ts is not None and
            (datetime.now(timezone.utc) - state.ws_last_update_ts).seconds <= 5
        )
        
        if not ws_fresh and len(state.rest_option_chain) > 0:
            use_data_source = "rest_snapshot"
            strike_source = state.rest_option_chain
            logger.info(f"Using REST snapshot for {symbol} analytics (WS idle > 5s)")
            
            # Recalculate OI totals from REST snapshot when WS is idle
            rest_total_call_oi = sum(
                strike.call.oi for strike in strike_source.values()
                if strike.call and strike.call.oi
            )
            rest_total_put_oi = sum(
                strike.put.oi for strike in strike_source.values()
                if strike.put and strike.put.oi
            )
            
            # Use REST-derived totals for analytics
            analytics_total_calls = rest_total_call_oi
            analytics_total_puts = rest_total_put_oi
            
            logger.info(f"REST OI totals - Calls: {analytics_total_calls}, Puts: {analytics_total_puts}")
            
        else:
            use_data_source = "websocket_stream"
            strike_source = state.ws_strikes
            logger.debug(f"Using WebSocket stream for {symbol} analytics (fresh ticks)")
            
            # Use WS-driven totals for analytics
            analytics_total_calls = state.total_oi_calls
            analytics_total_puts = state.total_oi_puts
        
        # Calculate PCR safely using appropriate data source totals
        analytics_total_oi = analytics_total_calls + analytics_total_puts
        pcr_value = (analytics_total_calls / analytics_total_oi) if analytics_total_oi > 0 else 0
        
        # Build frontend data structure with separated REST and WS data
        frontend_data = {
            "symbol": symbol,
            # REST snapshot data
            "rest_spot_price": state.rest_spot_price,
            "rest_spot_change": state.rest_spot_change,
            "rest_spot_change_percent": state.rest_spot_change_percent,
            "rest_last_update": state.rest_last_update.isoformat() if state.rest_last_update else None,
            # WebSocket tick data
            "ws_tick_price": state.ws_tick_price,
            "ws_last_update_ts": state.ws_last_update_ts.isoformat() if state.ws_last_update_ts else None,
            # Sticky ATM calculation
            "current_atm_strike": state.current_atm_strike,
            "atm_last_updated": state.atm_last_updated.isoformat() if state.atm_last_updated else None,
            # Combined data for frontend
            "spot_price": state.ws_tick_price if state.ws_tick_price is not None else state.rest_spot_price,
            "atm_strike": state.current_atm_strike,  # Use sticky ATM
            "timestamp": state.ws_last_update_ts or state.rest_last_update,
            # Analytics totals (use appropriate data source)
            "total_oi_calls": analytics_total_calls,  # REST-derived when WS idle
            "total_oi_puts": analytics_total_puts,     # REST-derived when WS idle
            "pcr": pcr_value,                         # Calculated from appropriate source
            "data_source": use_data_source,           # Track data source for debugging
            "strikes": {}
        }
        
        # Add strike data using determined data source
        active_strikes = state.get_strike_range(15)  # ATM ± 15 strikes
        
        for strike in active_strikes:
            strike_info = {"strike": strike}
            
            # Get strike data from determined source
            if use_data_source == "rest_snapshot":
                # Use REST snapshot data
                source_strike_data = state.rest_option_chain.get(strike)
                ws_strike_data = None
                rest_strike_data = source_strike_data
            else:
                # Use WebSocket stream data
                source_strike_data = state.ws_strikes.get(strike)
                ws_strike_data = source_strike_data
                rest_strike_data = state.rest_option_chain.get(strike)
            
            # Process call data
            call_data = ws_strike_data.call if ws_strike_data and ws_strike_data.call else (rest_strike_data.call if rest_strike_data else None)
            if call_data:
                strike_info["call"] = {
                    "ltp": call_data.ltp,
                    "oi": call_data.oi,
                    "delta": call_data.delta,
                    "gamma": call_data.gamma,
                    "theta": call_data.theta,
                    "vega": call_data.vega,
                    "iv": call_data.iv,
                    "volume": call_data.volume,
                    "change": self._calculate_change(call_data)
                }
            
            # Process put data
            put_data = ws_strike_data.put if ws_strike_data and ws_strike_data.put else (rest_strike_data.put if rest_strike_data else None)
            if put_data:
                strike_info["put"] = {
                    "ltp": put_data.ltp,
                    "oi": put_data.oi,
                    "delta": put_data.delta,
                    "gamma": put_data.gamma,
                    "theta": put_data.theta,
                    "vega": put_data.vega,
                    "iv": put_data.iv,
                    "volume": put_data.volume,
                    "change": self._calculate_change(put_data)
                }
            
            frontend_data["strikes"][strike] = strike_info
        
        return frontend_data
    
    def _calculate_change(self, instrument: InstrumentData) -> float:
        """Calculate price change from close price"""
        if instrument.ltp and instrument.cp:
            return round(instrument.ltp - instrument.cp, 2)
        return 0.0
    
    async def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get market snapshot for analytics processing
        """
        state = await self.get_symbol_state(symbol)
        if not state:
            return {}
        
        return {
            "symbol": symbol,
            "spot": state.spot,
            "total_oi_calls": state.total_oi_calls,
            "total_oi_puts": state.total_oi_puts,
            "pcr": state.total_oi_calls / (state.total_oi_calls + state.total_oi_puts) if (state.total_oi_calls + state.total_oi_puts) > 0 else 0,
            "atm_strike": state.get_atm_strike(),
            "active_strikes": len(state.strikes),
            "last_update": state.last_update.isoformat() if state.last_update else None
        }
    
    async def cleanup_old_data(self, max_age_minutes: int = 30) -> None:
        """
        Clean up old data to prevent memory leaks
        """
        async with self._lock:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_minutes * 60)
            
            for symbol, state in self.market_states.items():
                # Clean old strike data
                strikes_to_remove = []
                for strike, strike_data in state.strikes.items():
                    if (strike_data.last_update and 
                        strike_data.last_update.timestamp() < cutoff_time):
                        strikes_to_remove.append(strike)
                
                for strike in strikes_to_remove:
                    del state.strikes[strike]
                
                # Remove symbol if no recent data
                if (state.last_update and 
                    state.last_update.timestamp() < cutoff_time and
                    len(state.strikes) == 0):
                    del self.market_states[symbol]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get market state statistics
        """
        async with self._lock:
            total_symbols = len(self.market_states)
            total_strikes = sum(len(state.strikes) for state in self.market_states.values())
            
            return {
                "total_symbols": total_symbols,
                "total_strikes": total_strikes,
                "symbols": list(self.market_states.keys()),
                "last_update": max((state.last_update for state in self.market_states.values() if state.last_update), default=None)
            }
    
    async def update_rest_spot_price(self, symbol: str, spot_price: float) -> None:
        """
        Update REST spot price for a symbol
        """
        async with self._lock:
            # Get or create symbol state
            if symbol not in self.market_states:
                self.market_states[symbol] = SymbolMarketState(symbol=symbol)
            
            state = self.market_states[symbol]
            state.rest_spot_price = spot_price
            state.spot_price = spot_price
            state.spot = spot_price
            state.rest_last_update = datetime.now(timezone.utc)
            
            logger.debug(f"[MarketStateManager] Updated REST spot for {symbol}: {spot_price}")


# Singleton instance
_market_state_manager = MarketStateManager()

def get_market_state_manager() -> MarketStateManager:
    """Get the singleton MarketStateManager instance"""
    return _market_state_manager
