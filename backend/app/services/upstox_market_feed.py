"""
Upstox Market Data Feed V3 Service
Handles connection to Upstox WebSocket feed, decoding, and normalization
"""

import asyncio
import json
import logging
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
# import protobuf  # Will need to install protobuf - making optional for now
from app.services.upstox_auth_service import get_upstox_auth_service
from app.services.token_manager import get_token_manager
from app.utils.upstox_retry import retry_on_upstox_401
from app.core.live_market_state import MarketStateManager
from app.services.market_session_manager import get_market_session_manager, EngineMode, check_market_time
from fastapi import HTTPException
import httpx
from app.services.upstox_protobuf_parser_v3 import decode_protobuf_message
from app.services.live_chain_builder_registry import get_live_chain_builder
logger = logging.getLogger(__name__)

def resolve_symbol_from_instrument(instrument_key: str) -> str:
    if instrument_key.startswith("NSE_INDEX|Nifty"):
        return "NIFTY"

    if "BANKNIFTY" in instrument_key:
        return "BANKNIFTY"

    if "FINNIFTY" in instrument_key:
        return "FINNIFTY"

    if "MIDCPNIFTY" in instrument_key:
        return "MIDCPNIFTY"

    if "NIFTY" in instrument_key:
        return "NIFTY"

    return None

# GLOBAL REGISTRY FOR SINGLETON FEEDS (Step 1 singleton)
global_upstox_feeds: Dict[str, 'UpstoxMarketFeed'] = {}

def get_global_feed(symbol: str) -> Optional['UpstoxMarketFeed']:
    """Helper to get global singleton feed for a symbol"""
    return global_upstox_feeds.get(symbol.upper())

@dataclass
class FeedConfig:
    """Configuration for market data feed"""
    symbol: str
    spot_instrument_key: str
    strike_range: int = 10  # ATM ± 10 strikes
    mode: str = "full"  # full, ltpc, option_greeks, full_d30
    reconnect_delay: int = 5
    heartbeat_interval: int = 30

class UpstoxMarketFeed:
    """
    Handles Upstox Market Data Feed V3 connection and data processing
    """
    
    def __init__(self, config: FeedConfig, market_state: Optional[MarketStateManager] = None):
        self.config = config
        self.active_symbol = config.symbol
        self.auth_service = get_upstox_auth_service()  # Use shared instance
        self.market_state = market_state or MarketStateManager()
        self.token_manager = get_token_manager()
        self.websocket = None
        self.is_running = False
        self.last_heartbeat = None
        self.ws_connected = False  # Add connection flag to prevent multiple connections
        self.session_manager = None  # Will be set in start method
        self.ws_subscriptions: Dict[str, bool] = {}  # Track active subscriptions
        self.connection_attempts = 0 # Initialize connection attempts here
        self.max_connection_attempts = 10
        self.connection_backoff = 2  # seconds
        self.ws_lock = asyncio.Lock() # Step 1 singleton lock
        self.latest_ticks: Dict[str, Any] = {} # Step 6 singleton compatibility
        
    @retry_on_upstox_401
    async def _fetch_authorize_url(self, access_token: str, version: str = "v2") -> httpx.Response:
        """Fetch authorize URL from Upstox API with retry support"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            url = f"https://api.upstox.com/{version}/feed/market-data-feed/authorize"
            return await client.get(url, headers=headers)

    async def get_authorized_websocket_url(self) -> Optional[str]:
        """
        Get authorized WebSocket URL from Upstox API
        """
        try:
            # Get valid access token with automatic refresh
            access_token = await self.auth_service.get_valid_access_token()
            if not access_token:
                logger.error("No valid access token available")
                self.token_manager.invalidate("No valid access token")
                raise HTTPException(
                    status_code=401,
                    detail="Upstox authentication required"
                )
                
            # Try V2 first
            response = await self._fetch_authorize_url(access_token, version="v2")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Upstox authorize response: {data}")
                redirect_uri = data.get("data", {}).get("authorized_redirect_uri")
                if redirect_uri:
                    logger.info(f"Got WebSocket redirect URI: {redirect_uri}")
                    return redirect_uri
                else:
                    logger.error("No redirect URI in authorize response")
                    return None
            elif response.status_code == 401:
                logger.error("Upstox token revoked or expired even after retry")
                self.token_manager.invalidate("Upstox token revoked or expired")
                raise HTTPException(
                    status_code=401,
                    detail="Upstox authentication required"
                )
            # Fallback to V3
            v3_response = await self._fetch_authorize_url(access_token, version="v3")
            
            if v3_response.status_code == 200:
                v3_data = v3_response.json()
                logger.info(f"Upstox V3 authorize response: {v3_data}")
                # V3 API uses camelCase authorizedRedirectUri
                v3_redirect_uri = v3_data.get("data", {}).get("authorizedRedirectUri") or v3_data.get("data", {}).get("authorized_redirect_uri")
                if v3_redirect_uri:
                    logger.info(f"Got WebSocket redirect URI from V3: {v3_redirect_uri}")
                    # Log time for diagnostic purposes
                    import time
                    self.authorize_time = time.time()
                    return v3_redirect_uri
                else:
                    logger.error("No redirect URI in V3 authorize response")
                    return None
            else:
                logger.error(f"Failed to get V3 authorized URL: {v3_response.status_code}")
                return None
                    
        except HTTPException:
            # Re-raise HTTPException (401) without modification
            raise
        except Exception as e:
            logger.error(f"Error getting authorized WebSocket URL: {e}")
            return None
    
    async def _subscribe_index(self) -> bool:
        """
        Subscribe to index instrument (NSE_INDEX|Nifty 50 or NSE_INDEX|Nifty Bank)
        """
        try:
            index_key = self.config.spot_instrument_key
            subscribe_msg = {
                "guid": str(uuid.uuid4()),
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": [index_key]
                }
            }
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to %s", index_key)
            return True
        except Exception as e:
            logger.error(f"INDEX subscription failed: {e}")
            return False

    async def _connect(self) -> bool:
        """
        STEP 2: Make _connect() fully awaited handshake method.
        """
        try:
            # STEP 2: AUTHORIZE AFTER WAIT
            logger.info(f"UPSTOX CONNECTING - {self.config.symbol} (attempt {self.connection_attempts})")
            authorized_url = await self.get_authorized_websocket_url()
            
            if not authorized_url:
                logger.error(f"UPSTOX AUTH FAILED - {self.config.symbol}")
                return False
            
            logger.debug(f"UPSTOX WS CONNECTING - {self.config.symbol}")
            
            # STEP 3: CONNECT IMMEDIATELY (< 1s)
            logger.warning(f"=== UPSTOX WS HANDSHAKE START - {self.config.symbol} ===")
            
            # Upstox V3 requires subprotocol "json"
            self.websocket = await websockets.connect(
                authorized_url,
                subprotocols=["json"],
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.warning(f"UPSTOX WS CONNECTED - {self.config.symbol}")
            logger.warning(f"=== UPSTOX WS HANDSHAKE SUCCESS - {self.config.symbol} ===")
            
            # STEP 1 & 2: Send subscription message for index instrument immediately after connect
            success = await self._subscribe_index()
            if not success:
                logger.error(f"UPSTOX INDEX SUBSCRIPTION FAILED - {self.config.symbol}")
                return False
            
            self.ws_connected = True
            self.connection_attempts = 0  # Reset on success
            logger.info(f"UPSTOX CONNECTED - {self.config.symbol}")
            return True
            
        except Exception as ws_error:
            logger.error(f"UPSTOX WS HANDSHAKE FAILED - {self.config.symbol}: {ws_error}")
            return False

    async def connect_to_feed(self) -> bool:
        """
        STEP 1: Refactored connect_to_feed to be blocking and use ws_lock.
        """
        async with self.ws_lock:
            # STEP 5: Ensure ws_connected (is_connected) flag is checked
            if self.ws_connected and self.websocket:
                return True

            try:
                # Increment attempts BEFORE wait/auth
                self.connection_attempts += 1
                
                # STEP 1: WAIT BEFORE AUTHORIZING (Exponential Backoff)
                if self.connection_attempts > 1:
                    backoff = min(self.connection_backoff * (2 ** (self.connection_attempts - 2)), 30)
                    logger.info(f"Backing off for {backoff}s BEFORE authorization for {self.config.symbol}...")
                    await asyncio.sleep(backoff)
                
                # Await the actual handshake method (STEP 2)
                return await self._connect()
                    
            except Exception as e:
                logger.error(f"Failed to connect to Upstox feed for {self.config.symbol}: {e}")
                return False
    
    async def subscribe_to_instruments(self, instrument_keys: List[str]) -> bool:
        """
        Subscribe to specific instruments
        """
        try:
            subscription_message = {
                "guid": f"strikeiq_{int(datetime.now().timestamp())}",
                "method": "sub",
                "data": {
                    "mode": self.config.mode,
                    "instrumentKeys": instrument_keys
                }
            }
            
            # Send subscription request in binary format
            message_bytes = json.dumps(subscription_message).encode('utf-8')
            await self.websocket.send(message_bytes)
            
            logger.debug(f"Subscribed to {len(instrument_keys)} instruments for {self.config.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to instruments: {e}")
            return False
    
    async def unsubscribe_from_instruments(self, instrument_keys: List[str]) -> bool:
        """
        Unsubscribe from specific instruments
        """
        if not self.ws_connected or not self.websocket:
            return False
        
        try:
            unsubscribe_message = {
                "guid": f"strikeiq_unsub_{self.config.symbol}_{int(datetime.now().timestamp())}",
                "method": "unsub",
                "data": {
                    "instrumentKeys": instrument_keys
                }
            }
            
            # Send as binary JSON for consistency or UTF-8? 
            # Subprotocol is "json", so either string or bytes-JSON works.
            message_bytes = json.dumps(unsubscribe_message).encode('utf-8')
            await self.websocket.send(message_bytes)
            
            if hasattr(self, 'ws_subscriptions'):
                for key in instrument_keys:
                    self.ws_subscriptions.pop(key, None)
                    
            logger.info(f"Unsubscribed from {len(instrument_keys)} instruments for {self.config.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from instruments for {self.config.symbol}: {e}")
            return False

    async def subscribe(self, symbol: str) -> None:
        """
        Subscribe to market feed for a symbol
        """
        if symbol in self.ws_subscriptions:
            logger.info(f"Already subscribed to {symbol}")
            return
        
        logger.info(f"Subscribing to market feed for {symbol}")
        await self.connect_symbol_feed(symbol)
        self.ws_subscriptions[symbol] = True
    
    async def unsubscribe(self, symbol: str) -> None:
        """
        Unsubscribe from market feed for a symbol
        """
        if symbol not in self.ws_subscriptions:
            logger.info(f"Not subscribed to {symbol}")
            return
        
        logger.info(f"Unsubscribing from market feed for {symbol}")
        await self.disconnect_symbol_feed(symbol)
        del self.ws_subscriptions[symbol]
    
    async def connect_symbol_feed(self, symbol: str) -> None:
        """
        Connect to symbol-specific market feed
        """
        # This would contain the connection logic for a specific symbol
        # For now, we'll use the existing connection logic
        if not self.ws_connected:
            success = await self.connect_to_feed()
            if not success:
                logger.error(f"Failed to connect to feed for {symbol}")
                return
    
    async def disconnect_symbol_feed(self, symbol: str) -> None:
        """
        Disconnect from symbol-specific market feed
        """
        # This would contain the disconnection logic for a specific symbol
        # For now, we'll just log the disconnection
        logger.info(f"Disconnected from {symbol} feed")
    
    async def resubscribe_to_new_expiry(self, old_instrument_keys: List[str], new_instrument_keys: List[str]) -> bool:
        """
        Resubscribe from old expiry instruments to new expiry instruments
        """
        try:
            if not self.websocket or not self.is_connected:
                logger.warning("WebSocket not connected, cannot resubscribe")
                return False
            
            # Unsubscribe from old instruments
            if old_instrument_keys:
                unsubscribe_message = {
                    "guid": f"strikeiq_unsubscribe_{int(datetime.now().timestamp())}",
                    "method": "unsub",
                    "data": {
                        "instrumentKeys": old_instrument_keys
                    }
                }
                
                message_bytes = json.dumps(unsubscribe_message).encode('utf-8')
                await self.websocket.send(message_bytes)
                logger.info(f"Unsubscribed from {len(old_instrument_keys)} old expiry instruments")
            
            # Subscribe to new instruments
            if new_instrument_keys:
                subscribe_message = {
                    "guid": f"strikeiq_subscribe_{int(datetime.now().timestamp())}",
                    "method": "sub",
                    "data": {
                        "mode": self.config.mode,
                        "instrumentKeys": new_instrument_keys
                    }
                }
                
                message_bytes = json.dumps(subscribe_message).encode('utf-8')
                await self.websocket.send(message_bytes)
                logger.info(f"Subscribed to {len(new_instrument_keys)} new expiry instruments")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resubscribe to new expiry: {e}")
            return False
    
    async def get_active_strikes(self) -> List[str]:
        """
        Get cached ATM ± strike range instruments to subscribe to
        NO REST CALLS - Use cached data from market state to prevent re-authorization loops
        FALLBACK TO BOOTSTRAP IF REST CHAIN NOT AVAILABLE
        """
        try:
            # Get current market state from our market state manager
            symbol_state = await self.market_state.get_symbol_state(self.config.symbol)
            if not symbol_state:
                logger.error(f"No market state available for {self.config.symbol}")
                return []
            
            # Use cached spot price from market state (WS preferred, REST fallback)
            current_spot = symbol_state.ws_tick_price if symbol_state.ws_tick_price is not None else symbol_state.rest_spot_price
            if not current_spot:
                return []
            
            # Use cached option chain from market state
            cached_strikes = list(symbol_state.rest_option_chain.keys()) if symbol_state.rest_option_chain else []
            
            # BOOTSTRAP LOGIC: If no REST chain available, derive ATM from spot price
            if not cached_strikes:
                logger.warning(f"No REST option chain available for {self.config.symbol}, using bootstrap ATM calculation")
                
                # Calculate bootstrap ATM using spot price and standard strike gaps
                is_bn = "BANK" in self.config.symbol.upper()
                strike_gap = 100 if is_bn else 50
                bootstrap_atm = round(current_spot / strike_gap) * strike_gap
                
                # Generate bootstrap strike range around bootstrap ATM
                bootstrap_strikes = []
                # Use 15 strikes as per user request
                for i in range(-15, 16):
                    strike = bootstrap_atm + (i * strike_gap)
                    if strike > 0:  # Only positive strikes
                        bootstrap_strikes.append(strike)
                
                # Convert to instrument keys
                instrument_keys = [self.config.spot_instrument_key]  # Add spot
                
                # Add bootstrap option strikes using Upstox V3 format
                now = datetime.now()
                yr_mon = now.strftime("%y%b").upper()
                sym_prefix = "BANKNIFTY" if is_bn else "NIFTY"
                
                for strike in bootstrap_strikes:
                    strike_str = str(int(strike))
                    # V3 format: NSE_FO|NIFTY26FEB22000CE
                    instrument_keys.append(f"NSE_FO|{sym_prefix}{yr_mon}{strike_str}CE")
                    instrument_keys.append(f"NSE_FO|{sym_prefix}{yr_mon}{strike_str}PE")
                
                logger.info(f"Using {len(instrument_keys)} bootstrap instruments for {self.config.symbol} (ATM: {bootstrap_atm})")
                return instrument_keys
            
            # NORMAL PATH: REST chain available, use cached data
            # Find ATM from cached strikes
            atm_strike = min(cached_strikes, key=lambda x: abs(x - current_spot))
            logger.info(f"Using cached ATM strike: {atm_strike} (spot: {current_spot})")
            
            # Get strike range around ATM (ATM ± configured range)
            strike_range = []
            for strike in cached_strikes:
                if abs(strike - atm_strike) <= (self.config.strike_range * 50):  # 50 point intervals
                    strike_range.append(strike)
            
            # Sort and limit strikes
            strike_range.sort()
            if len(strike_range) > (self.config.strike_range * 2 + 1):
                center_idx = strike_range.index(atm_strike)
                start_idx = max(0, center_idx - self.config.strike_range)
                end_idx = min(len(strike_range), center_idx + self.config.strike_range + 1)
                strike_range = strike_range[start_idx:end_idx]
            
            # Convert to instrument keys
            instrument_keys = [self.config.spot_instrument_key]  # Add spot
            
            # Add option strikes
            for strike in strike_range:
                instrument_keys.append(f"NFO_FO|{strike}-CE")
                instrument_keys.append(f"NFO_FO|{strike}-PE")
            
            logger.info(f"Using {len(instrument_keys)} cached instruments for {self.config.symbol} (ATM: {atm_strike})")
            return instrument_keys
            
        except HTTPException:
            # Re-raise HTTPException (401) without modification
            raise
        except Exception as e:
            logger.error(f"Error getting cached active strikes: {e}")
            return []
    
    async def process_live_feed(self, data: Dict[str, Any]) -> None:
        """
        Process live market data feed
        """
        try:
            feeds = data.get("feeds", {})
            timestamp = data.get("currentTs")

            for instrument_key, feed_data in feeds.items():

                # Safe nested parsing for Upstox V3 feed structure
                market = feed_data.get("fullFeed", {}).get("marketFF", {})
                
                ltpc = market.get("ltpc", {})
                
                ltp = ltpc.get("ltp", 0)
                oi = market.get("oi", 0)
                volume = market.get("vtt", 0)
                iv = market.get("iv", 0)
                
                greeks = market.get("optionGreeks", {})
                delta = greeks.get("delta")
                gamma = greeks.get("gamma")
                theta = greeks.get("theta")
                vega = greeks.get("vega")

                processed_data = {
                    "instrument_key": instrument_key,
                    "timestamp": timestamp,
                    "ltp": ltp,
                    "ltt": ltpc.get("ltt"),
                    "ltq": ltpc.get("ltq"),
                    "cp": ltpc.get("cp"),
                    "oi": oi,
                    "volume": volume,
                    "iv": iv,
                    "delta": delta,
                    "gamma": gamma,
                    "theta": theta,
                    "vega": vega
                }

                # Debug log for parsed tick
                logger.info(f"PARSED TICK → {instrument_key} LTP={ltp} OI={oi}")

                # UPDATE MARKET STATE
                self.market_state.update_ws_tick_price(
                    self.config.symbol,
                    instrument_key,
                    processed_data
                )

                # 🚀 FO BOOST (FIRST INDEX TICK)
                if (
                    instrument_key == self.config.spot_instrument_key
                    and not getattr(self, "_fo_boost_done", False)
                ):
                    ltp = processed_data.get("ltp")
                    if ltp:
                        success = await self._subscribe_to_fo_options(ltp)
                        if not success:
                            logger.error(f"FO subscription failed for {self.config.symbol}")
                            continue
                        self._fo_boost_done = True

                # ======================================
                # BROADCAST MARKET TICK TO FRONTEND ✅
                # ======================================
                if instrument_key == self.config.spot_instrument_key:
                    ltp = processed_data.get("ltp")
                    if ltp:
                        # Broadcast to frontend WebSocket
                        from app.core.ws_manager import manager
                        
                        broadcast_message = {
                            "type": "market_data",
                            "instrument": instrument_key,
                            "ltp": ltp
                        }
                        
                        logger.info(f"MARKET DATA EXTRACTED - instrument={instrument_key} ltp={ltp}")
                        await manager.broadcast(broadcast_message)  # ISSUE 5 FIX: Use broadcast() instead of broadcast_json()
                        logger.info(f"WS BROADCAST SENT - instrument={instrument_key} ltp={ltp}")

                # ======================================
                # LIVE CHAIN BUILDER PUSH  ✅ FINAL FIX
                # ======================================

                tick_data = {
                    "instrument_key": instrument_key,
                    "ltp": processed_data.get("ltp"),
                    "timestamp": processed_data.get("timestamp")
                        or int(datetime.now().timestamp() * 1000),
                    "oi": processed_data.get("oi"),
                    "volume": processed_data.get("volume"),
                    "delta": processed_data.get("delta"),
                    "gamma": processed_data.get("gamma"),
                    "theta": processed_data.get("theta"),
                    "vega": processed_data.get("vega"),
                    "iv": processed_data.get("iv")
                }

                # AI latest tick cache
                self.latest_ticks[instrument_key] = tick_data

                # 🔥 RESOLVE SYMBOL FROM INSTRUMENT
                symbol = resolve_symbol_from_instrument(instrument_key)

                if not symbol:
                    continue   # ❗ WAS RETURN → NOW FIXED

                builder = get_live_chain_builder(symbol, "")  # ISSUE 4 FIX: Pass expiry parameter

                if not builder:
                    continue   # ❗ SAFETY FIX

                asyncio.create_task(
                    builder.handle_tick(
                        symbol,
                        instrument_key,
                        tick_data
                    )
                )

        except Exception as e:
            logger.error(f"Error processing live feed: {e}")
    
    async def process_message(self, message: str | bytes) -> None:
        """
        Process incoming WebSocket message. 
        Supports both JSON and Binary (Protobuf).
        """
        try:
            logger.info("UPSTOX RAW MESSAGE RECEIVED")
            
            if isinstance(message, bytes):
                # Binary message -> Protobuf
                logger.info("UPSTOX BINARY MESSAGE - Parsing protobuf")
                ticks = parse_upstox_feed(message)
                if ticks:
                    logger.info(f"UPSTOX PROTOBUF DECODE SUCCESS - {len(ticks)} ticks")
                    # Convert tick list to feeds dict format for compatibility
                    feeds_dict = {}
                    for tick in ticks:
                        instrument_key = tick.get("instrument_key")
                        ltp = tick.get("ltp")
                        if instrument_key and ltp:
                            feeds_dict[instrument_key] = {
                                "ltpc": {"ltp": ltp},
                                "timestamp": tick.get("timestamp"),
                                "oi": 0,  # Default values
                                "volume": 0,
                                "option_greeks": {
                                    "delta": 0,
                                    "gamma": 0,
                                    "theta": 0,
                                    "vega": 0,
                                    "iv": 0
                                }
                            }
                    
                    data = {
                        "feeds": feeds_dict,
                        "currentTs": int(datetime.now().timestamp() * 1000)
                    }
                    logger.info("UPSTOX MARKET DATA EXTRACTED - Processing feed")
                    await self.process_live_feed(data)
                return

            # JSON message -> Session management or market data
            logger.info("UPSTOX JSON MESSAGE - Parsing")
            data = json.loads(message)
            await self.process_live_feed(data)
            self.last_heartbeat = datetime.now(timezone.utc)
            logger.info("UPSTOX MESSAGE PROCESSED")
        except Exception as e:
            logger.error(f"UPSTOX MESSAGE PROCESSING ERROR: {e}")
    
    async def run_feed_loop(self) -> None:
        """
        Main feed loop - connect, subscribe, and process messages
        """
        while self.is_running:
            try:
                # Connect to feed (sequential check)
                if not await self.connect_to_feed():
                    await asyncio.sleep(self.config.reconnect_delay)
                    continue
                
                # Get instruments to subscribe to
                instrument_keys = await self.get_active_strikes()
                if not instrument_keys:
                    await asyncio.sleep(self.config.reconnect_delay)
                    continue
                
                # Subscribe to instruments
                if not await self.subscribe_to_instruments(instrument_keys):
                    await asyncio.sleep(self.config.reconnect_delay)
                    continue
                
                # Process messages
                async for message in self.websocket:
                    await self.process_message(message)
                    
                    # Check heartbeat
                    if (self.last_heartbeat and 
                        (datetime.now(timezone.utc) - self.last_heartbeat).seconds > self.config.heartbeat_interval * 2):
                        logger.warning("Heartbeat timeout, reconnecting...")
                        break
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
            except Exception as e:
                logger.error(f"Feed loop error: {e}")
            
            # Cleanup and reconnect delay
            if self.websocket:
                try:
                    await self.websocket.close()
                except:
                    pass
            
            await asyncio.sleep(self.config.reconnect_delay)
    
    async def start(self) -> None:
        """
        Start the market feed service with market status integration
        """
        try:
            self.session_manager = get_market_session_manager()
            if self.session_manager is None:
                logger.warning("Market session manager not available, starting without status integration")
                self.is_running = True
                return
            
            # Register for market status changes
            await self.session_manager.register_status_callback(self._on_market_status_change)
            
            # Check current market status
            current_status = self.session_manager.get_market_status().value
            
            # Note: We still allow starting even if market is closed for startup handshake
            # as per user preference: "WS should connect ONLY on: FastAPI startup event"
            self.is_running = True
            
        except Exception as e:
            logger.error(f"Error starting market feed: {e}")
            self.is_running = False
            return
        
        logger.info(f"Starting Upstox market feed for {self.config.symbol}")
        
        # Register in global registry for singleton access
        global_upstox_feeds[self.config.symbol.upper()] = self
        
        # Run feed loop in background
        # Note: Handshake should be awaited externally before this loop takes over
        asyncio.create_task(self.run_feed_loop())
    
    async def _on_market_status_change(self, status, mode: EngineMode):
        """Handle market status changes"""
        logger.info(f"Market status changed: {status.value} ({mode.value})")
        
        # Step 3 fix: Do not start feed loop here to avoid parallel handshake triggers
        # Only handle stopping if needed, or logging.
        if not check_market_time() or mode != EngineMode.LIVE:
            if self.is_running:
                logger.info(f"Market {status.value} - stopping WebSocket feed background loop")
                # We keep the connection if possible, or fully stop. 
                # For now, let's keep it simple and just log.
                pass
    
    async def can_start_websocket(self) -> bool:
        """Check if WebSocket feed can be started based on market status"""
        if not self.session_manager:
            self.session_manager = get_market_session_manager()
        
        current_status = self.session_manager.get_market_status().value
        return check_market_time() and self.session_manager.get_engine_mode() == EngineMode.LIVE
    
    async def resync_subscriptions(self) -> None:
        """
        Resync WebSocket subscriptions when REST option chain becomes available
        """
        try:
            logger.info(f"Resyncing subscriptions for {self.config.symbol}")
            
            # Get new instrument list with updated REST chain
            new_instrument_keys = await self.get_active_strikes()
            
            if new_instrument_keys and self.websocket:
                # Send new subscription message
                subscription_message = {
                    "guid": f"strikeiq_resync_{int(datetime.now().timestamp())}",
                    "method": "sub",
                    "data": {
                        "mode": self.config.mode,
                        "instrumentKeys": new_instrument_keys
                    }
                }
                
                message_bytes = json.dumps(subscription_message).encode('utf-8')
                await self.websocket.send(message_bytes)
                logger.info(f"Resubscribed to {len(new_instrument_keys)} instruments for {self.config.symbol}")
            
        except Exception as e:
            logger.error(f"Error resyncing subscriptions: {e}")

    async def stop(self) -> None:
        """
        Stop the market feed service
        """
        self.is_running = False
        self.ws_connected = False  # Reset connection flag
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        logger.info(f"Stopped Upstox market feed for {self.config.symbol}")

    async def _subscribe_to_fo_options(self, spot_price: float) -> bool:
        """
        Dynamically subscribe to FO options based on arrived spot price (Upstox V3)
        """
        try:
            # STEP 1: Fetch ATM strike from index LTP
            is_bn = "BANK" in self.config.symbol.upper()
            strike_gap = 100 if is_bn else 50
            atm_strike = round(spot_price / strike_gap) * strike_gap
            
            # STEP 3: Construct and Resolve Numeric instrumentKeys
            resolved_keys = []
            now = datetime.now()
            yr_mon = now.strftime("%y%b").upper() # Monthly fallback (e.g. 26FEB)
            sym = "BANKNIFTY" if is_bn else "NIFTY"
            
            for i in range(-15, 16):
                strike = atm_strike + (i * strike_gap)
                if strike <= 0: continue
                
                strike_str = str(int(strike))
                # Trading symbols (e.g. NIFTY26FEB22000CE)
                ce_tsym = f"{sym}{yr_mon}{strike_str}CE"
                pe_tsym = f"{sym}{yr_mon}{strike_str}PE"
                
                # Lookup numeric key from instruments.json cache
                symbol = self.config.symbol
                builder = get_live_chain_builder(symbol, "")  # ISSUE 4 FIX: Pass expiry parameter
                ce_key = builder.resolve_instrument_key(ce_tsym)
                pe_key = builder.resolve_instrument_key(pe_tsym)
                
                if ce_key:
                    resolved_keys.append(ce_key)
                    logger.debug(f"Resolved {ce_tsym} -> {ce_key}")
                if pe_key:
                    resolved_keys.append(pe_key)
                    logger.debug(f"Resolved {pe_tsym} -> {pe_key}")
            
            logger.info("Resolved FO symbols for subscription for %s", self.config.symbol)
            
            # STEP 4: Send WS subscription ONLY using numeric keys
            if resolved_keys and self.websocket:
                subscription_message = {
                    "guid": str(uuid.uuid4()),
                    "method": "sub",
                    "data": {
                        "mode": self.config.mode,
                        "instrumentKeys": resolved_keys
                    }
                }
                message_bytes = json.dumps(subscription_message).encode('utf-8')
                await self.websocket.send(message_bytes)
                logger.info("Subscribed to %d numeric FO instruments for %s around ATM %s", 
                            len(resolved_keys), self.config.symbol, atm_strike)
                return True
            else:
                logger.warning(f"No numeric FO keys resolved for {self.config.symbol} ATM {atm_strike}")
                return False
                
        except Exception as e:
            logger.error(f"Error in dynamic FO subscription: {e}")
            return False
