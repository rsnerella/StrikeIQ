"""
Market Feed Engine - Unified Market Data Processing
Consolidates market data ingestion, protobuf parsing, tick processing, and message routing
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class MarketTick:
    """Unified market tick representation"""
    symbol: str
    instrument_key: str
    ltp: float
    oi: Optional[float]
    volume: Optional[float]
    timestamp: datetime
    tick_type: str  # index_tick, option_tick, market_tick

@dataclass
class OptionData:
    """Unified option data representation"""
    symbol: str
    strike: float
    option_type: str  # CE or PE
    ltp: float
    oi: Optional[float]
    volume: Optional[float]
    iv: Optional[float]
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]
    timestamp: datetime

class MarketFeedEngine:
    """
    Unified Market Feed Engine
    
    Consolidates:
    - Market data ingestion
    - Protobuf parsing
    - Tick processing
    - Message routing
    - Option chain building
    
    Features:
    - Real-time tick processing
    - Automatic option chain updates
    - Efficient message routing
    - Data validation and normalization
    """
    
    def __init__(self):
        # Data storage
        self.latest_ticks: Dict[str, MarketTick] = {}
        self.option_chain: Dict[str, Dict[float, Dict[str, OptionData]]] = {}  # symbol -> strike -> {CE, PE}
        self.index_prices: Dict[str, float] = {}
        
        # Processing callbacks
        self.tick_handlers: List[Callable[[MarketTick], None]] = []
        self.option_chain_handlers: List[Callable[[str, Dict], None]] = []
        self.error_handlers: List[Callable[[Exception, Dict[str, Any]], None]] = []
        
        # Processing parameters
        self.max_chain_size = 50  # Maximum strikes per option chain
        self.update_interval = 1.0  # Seconds between chain updates
        self.last_chain_update: Dict[str, datetime] = {}
        
        # Statistics
        self.ticks_processed = 0
        self.errors_count = 0
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("MarketFeedEngine initialized - Unified market data processing")
    
    async def process_protobuf_message(self, symbol: str, protobuf_data: bytes) -> None:
        """
        Process incoming protobuf message
        Unified entry point for all market data
        """
        try:
            # Parse protobuf message
            parsed_data = await self._parse_protobuf(protobuf_data)
            
            # Route to appropriate processor
            message_type = parsed_data.get("type", "unknown")
            
            if message_type == "index_tick":
                await self._process_index_tick(symbol, parsed_data)
            elif message_type == "option_tick":
                await self._process_option_tick(symbol, parsed_data)
            elif message_type == "market_tick":
                await self._process_market_tick(symbol, parsed_data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error processing protobuf message for {symbol}: {e}")
            await self._handle_error(e, {"symbol": symbol, "data_type": "protobuf"})
    
    async def _parse_protobuf(self, protobuf_data: bytes) -> Dict[str, Any]:
        """Parse protobuf message into structured format"""
        try:
            # This would integrate with the actual protobuf parser
            # For now, simulate parsing
            import struct
            
            # Simple parsing simulation
            if len(protobuf_data) < 20:
                return {"type": "unknown", "error": "Data too short"}
            
            # Extract basic fields (simplified)
            # In production, this would use the actual protobuf definitions
            parsed = {
                "type": "option_tick",  # Default
                "instrument_key": "UNKNOWN",
                "ltp": 0.0,
                "oi": 0,
                "volume": 0,
                "timestamp": datetime.now(timezone.utc)
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Protobuf parsing error: {e}")
            return {"type": "error", "error": str(e)}
    
    async def _process_index_tick(self, symbol: str, data: Dict[str, Any]) -> None:
        """Process index tick data"""
        try:
            # Extract index data
            instrument_key = data.get("instrument_key", "")
            ltp = float(data.get("ltp", 0))
            timestamp = data.get("timestamp", datetime.now(timezone.utc))
            
            # Create market tick
            tick = MarketTick(
                symbol=symbol,
                instrument_key=instrument_key,
                ltp=ltp,
                oi=None,
                volume=None,
                timestamp=timestamp,
                tick_type="index_tick"
            )
            
            # Update index price
            self.index_prices[symbol] = ltp
            
            # Store tick
            self.latest_ticks[f"{symbol}_index"] = tick
            
            # Notify handlers
            await self._notify_tick_handlers(tick)
            
            self.ticks_processed += 1
            logger.debug(f"Processed index tick for {symbol}: {ltp}")
            
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error processing index tick for {symbol}: {e}")
            await self._handle_error(e, {"symbol": symbol, "tick_type": "index"})
    
    async def _process_option_tick(self, symbol: str, data: Dict[str, Any]) -> None:
        """Process option tick data"""
        try:
            # Extract option data
            instrument_key = data.get("instrument_key", "")
            ltp = float(data.get("ltp", 0))
            oi = float(data.get("oi", 0))
            volume = float(data.get("volume", 0))
            timestamp = data.get("timestamp", datetime.now(timezone.utc))
            
            # Parse instrument key to get strike and type
            strike, option_type = self._parse_instrument_key(instrument_key)
            if not strike or not option_type:
                logger.warning(f"Could not parse instrument key: {instrument_key}")
                return
            
            # Create option data
            option_data = OptionData(
                symbol=symbol,
                strike=strike,
                option_type=option_type,
                ltp=ltp,
                oi=oi,
                volume=volume,
                iv=None,  # Would be extracted from protobuf if available
                delta=None,
                gamma=None,
                theta=None,
                vega=None,
                timestamp=timestamp
            )
            
            # Update option chain
            await self._update_option_chain(symbol, option_data)
            
            # Create market tick
            tick = MarketTick(
                symbol=symbol,
                instrument_key=instrument_key,
                ltp=ltp,
                oi=oi,
                volume=volume,
                timestamp=timestamp,
                tick_type="option_tick"
            )
            
            # Store tick
            self.latest_ticks[instrument_key] = tick
            
            # Notify handlers
            await self._notify_tick_handlers(tick)
            
            # Check if chain update is needed
            await self._check_chain_update(symbol)
            
            self.ticks_processed += 1
            logger.debug(f"Processed option tick for {symbol}: {strike} {option_type} @ {ltp}")
            
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error processing option tick for {symbol}: {e}")
            await self._handle_error(e, {"symbol": symbol, "tick_type": "option"})
    
    async def _process_market_tick(self, symbol: str, data: Dict[str, Any]) -> None:
        """Process general market tick data"""
        try:
            # Extract market data
            instrument_key = data.get("instrument_key", "")
            ltp = float(data.get("ltp", 0))
            oi = float(data.get("oi", 0))
            volume = float(data.get("volume", 0))
            timestamp = data.get("timestamp", datetime.now(timezone.utc))
            
            # Create market tick
            tick = MarketTick(
                symbol=symbol,
                instrument_key=instrument_key,
                ltp=ltp,
                oi=oi,
                volume=volume,
                timestamp=timestamp,
                tick_type="market_tick"
            )
            
            # Store tick
            self.latest_ticks[instrument_key] = tick
            
            # Notify handlers
            await self._notify_tick_handlers(tick)
            
            self.ticks_processed += 1
            logger.debug(f"Processed market tick for {symbol}: {instrument_key} @ {ltp}")
            
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error processing market tick for {symbol}: {e}")
            await self._handle_error(e, {"symbol": symbol, "tick_type": "market"})
    
    def _parse_instrument_key(self, instrument_key: str) -> tuple[Optional[float], Optional[str]]:
        """Parse instrument key to extract strike and option type"""
        try:
            # Example format: "NSE_OPT|NIFTY|2024-03-28|19500|CE"
            parts = instrument_key.split("|")
            
            if len(parts) >= 5 and parts[4] in ["CE", "PE"]:
                strike = float(parts[3])
                option_type = parts[4]
                return strike, option_type
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error parsing instrument key {instrument_key}: {e}")
            return None, None
    
    async def _update_option_chain(self, symbol: str, option_data: OptionData) -> None:
        """Update option chain with new option data"""
        try:
            # Initialize symbol chain if needed
            if symbol not in self.option_chain:
                self.option_chain[symbol] = {}
            
            # Initialize strike if needed
            if option_data.strike not in self.option_chain[symbol]:
                self.option_chain[symbol][option_data.strike] = {}
            
            # Update option data
            self.option_chain[symbol][option_data.strike][option_data.option_type] = option_data
            
            # Limit chain size
            if len(self.option_chain[symbol]) > self.max_chain_size:
                await self._trim_option_chain(symbol)
                
        except Exception as e:
            logger.error(f"Error updating option chain for {symbol}: {e}")
    
    async def _trim_option_chain(self, symbol: str) -> None:
        """Trim option chain to maximum size"""
        try:
            if symbol not in self.option_chain:
                return
            
            # Get current strike price (index price)
            spot_price = self.index_prices.get(symbol, 0)
            if spot_price == 0:
                return
            
            # Sort strikes by distance from ATM
            strikes = list(self.option_chain[symbol].keys())
            strikes.sort(key=lambda x: abs(x - spot_price))
            
            # Keep only the closest strikes
            kept_strikes = strikes[:self.max_chain_size]
            
            # Rebuild chain
            new_chain = {}
            for strike in kept_strikes:
                new_chain[strike] = self.option_chain[symbol][strike]
            
            self.option_chain[symbol] = new_chain
            logger.debug(f"Trimmed option chain for {symbol} to {len(new_chain)} strikes")
            
        except Exception as e:
            logger.error(f"Error trimming option chain for {symbol}: {e}")
    
    async def _check_chain_update(self, symbol: str) -> None:
        """Check if option chain update should be triggered"""
        try:
            now = datetime.now(timezone.utc)
            last_update = self.last_chain_update.get(symbol)
            
            if (not last_update or 
                (now - last_update).total_seconds() >= self.update_interval):
                
                await self._trigger_chain_update(symbol)
                self.last_chain_update[symbol] = now
                
        except Exception as e:
            logger.error(f"Error checking chain update for {symbol}: {e}")
    
    async def _trigger_chain_update(self, symbol: str) -> None:
        """Trigger option chain update notification"""
        try:
            if symbol in self.option_chain:
                chain_data = self._format_option_chain(symbol)
                await self._notify_chain_handlers(symbol, chain_data)
                logger.debug(f"Triggered chain update for {symbol}")
                
        except Exception as e:
            logger.error(f"Error triggering chain update for {symbol}: {e}")
    
    def _format_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Format option chain for frontend consumption"""
        try:
            if symbol not in self.option_chain:
                return {}
            
            chain = {}
            spot_price = self.index_prices.get(symbol, 0)
            
            for strike in sorted(self.option_chain[symbol].keys()):
                strike_data = self.option_chain[symbol][strike]
                
                chain[str(strike)] = {
                    "strike": strike,
                    "distance_from_atm": strike - spot_price if spot_price > 0 else 0,
                    "CE": {
                        "ltp": strike_data.get("CE", OptionData(symbol, strike, "CE", 0, 0, 0, None, None, None, None, None, datetime.now())).ltp,
                        "oi": strike_data.get("CE", OptionData(symbol, strike, "CE", 0, 0, 0, None, None, None, None, None, datetime.now())).oi,
                        "volume": strike_data.get("CE", OptionData(symbol, strike, "CE", 0, 0, 0, None, None, None, None, None, datetime.now())).volume
                    } if "CE" in strike_data else None,
                    "PE": {
                        "ltp": strike_data.get("PE", OptionData(symbol, strike, "PE", 0, 0, 0, None, None, None, None, None, datetime.now())).ltp,
                        "oi": strike_data.get("PE", OptionData(symbol, strike, "PE", 0, 0, 0, None, None, None, None, None, datetime.now())).oi,
                        "volume": strike_data.get("PE", OptionData(symbol, strike, "PE", 0, 0, 0, None, None, None, None, None, datetime.now())).volume
                    } if "PE" in strike_data else None
                }
            
            return {
                "symbol": symbol,
                "spot_price": spot_price,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "chain": chain,
                "total_strikes": len(chain)
            }
            
        except Exception as e:
            logger.error(f"Error formatting option chain for {symbol}: {e}")
            return {}
    
    async def _notify_tick_handlers(self, tick: MarketTick) -> None:
        """Notify all registered tick handlers"""
        for handler in self.tick_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(tick)
                else:
                    handler(tick)
            except Exception as e:
                logger.error(f"Error in tick handler: {e}")
    
    async def _notify_chain_handlers(self, symbol: str, chain_data: Dict[str, Any]) -> None:
        """Notify all registered chain handlers"""
        for handler in self.option_chain_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(symbol, chain_data)
                else:
                    handler(symbol, chain_data)
            except Exception as e:
                logger.error(f"Error in chain handler: {e}")
    
    async def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle processing errors"""
        for handler in self.error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error, context)
                else:
                    handler(error, context)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    # Registration methods
    def register_tick_handler(self, handler: Callable[[MarketTick], None]) -> None:
        """Register tick handler"""
        self.tick_handlers.append(handler)
        logger.info(f"Registered tick handler: {handler.__name__}")
    
    def register_chain_handler(self, handler: Callable[[str, Dict], None]) -> None:
        """Register option chain handler"""
        self.option_chain_handlers.append(handler)
        logger.info(f"Registered chain handler: {handler.__name__}")
    
    def register_error_handler(self, handler: Callable[[Exception, Dict[str, Any]], None]) -> None:
        """Register error handler"""
        self.error_handlers.append(handler)
        logger.info(f"Registered error handler: {handler.__name__}")
    
    # Query methods
    def get_latest_tick(self, instrument_key: str) -> Optional[MarketTick]:
        """Get latest tick for instrument"""
        return self.latest_ticks.get(instrument_key)
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get formatted option chain for symbol"""
        return self._format_option_chain(symbol)
    
    def get_index_price(self, symbol: str) -> float:
        """Get latest index price"""
        return self.index_prices.get(symbol, 0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return {
            "ticks_processed": self.ticks_processed,
            "errors_count": self.errors_count,
            "uptime_seconds": uptime,
            "ticks_per_second": self.ticks_processed / max(uptime, 1),
            "error_rate": self.errors_count / max(self.ticks_processed, 1),
            "active_symbols": list(self.index_prices.keys()),
            "total_option_strikes": sum(len(chain) for chain in self.option_chain.values())
        }
    
    # Cleanup methods
    def clear_data(self, symbol: Optional[str] = None) -> None:
        """Clear data for symbol or all symbols"""
        if symbol:
            # Clear specific symbol
            keys_to_remove = [k for k in self.latest_ticks.keys() if k.startswith(symbol)]
            for key in keys_to_remove:
                del self.latest_ticks[key]
            
            if symbol in self.index_prices:
                del self.index_prices[symbol]
            
            if symbol in self.option_chain:
                del self.option_chain[symbol]
            
            if symbol in self.last_chain_update:
                del self.last_chain_update[symbol]
                
            logger.info(f"Cleared data for {symbol}")
        else:
            # Clear all data
            self.latest_ticks.clear()
            self.option_chain.clear()
            self.index_prices.clear()
            self.last_chain_update.clear()
            
            logger.info("Cleared all market data")
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down MarketFeedEngine")
        
        # Clear all data
        self.clear_data()
        
        # Clear handlers
        self.tick_handlers.clear()
        self.option_chain_handlers.clear()
        self.error_handlers.clear()
        
        logger.info("MarketFeedEngine shutdown complete")
