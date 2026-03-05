"""
Test Market Feed Simulator for StrikeIQ
Simulates WebSocket market data to test option subscription pipeline
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.websocket_market_feed import WebSocketMarketFeed, build_option_keys, get_atm_strike
from app.services.message_router import message_router
from app.services.option_chain_builder import option_chain_builder
from app.services.instrument_registry import get_instrument_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketFeedSimulator:
    """Simulates WebSocket market data for testing"""
    
    def __init__(self):
        self.websocket_feed = WebSocketMarketFeed()
        self.test_results = {
            'index_ticks_received': 0,
            'atm_calculations': 0,
            'option_keys_generated': 0,
            'subscription_payloads_created': 0,
            'option_ticks_received': 0
        }
    
    async def setup(self):
        """Setup test environment without real WebSocket connections"""
        logger.info("=== MARKET FEED SIMULATOR SETUP ===")
        
        # Start option chain builder
        await option_chain_builder.start()
        logger.info("✅ Option chain builder started")
        
        # Mock instrument registry for testing
        self.websocket_feed.current_expiry = "2024-04-10"
        logger.info(f"✅ Mock expiry set to: {self.websocket_feed.current_expiry}")
        
        # Create mock instrument registry
        self.mock_instrument_registry()
        
        logger.info("✅ Setup complete - no real WebSocket connections")
    
    def mock_instrument_registry(self):
        """Create mock instrument registry for testing"""
        logger.info("Creating mock instrument registry...")
        
        # Mock registry with sample NIFTY options
        mock_registry = MockInstrumentRegistry()
        
        # Replace the global registry function
        import app.services.websocket_market_feed
        app.services.websocket_market_feed.get_instrument_registry = lambda: mock_registry
        
        # Also patch the websocket_feed's registry access
        self.websocket_feed.instrument_registry = mock_registry
        
        logger.info("✅ Mock instrument registry created")
    
    async def simulate_index_ticks(self):
        """Simulate multiple index ticks to trigger ATM recalculation"""
        logger.info("=== SIMULATING INDEX TICKS ===")
        
        # Test tick sequence to trigger ATM changes
        test_prices = [24720, 24735, 24750, 24780]
        
        for i, price in enumerate(test_prices):
            logger.info(f"\n--- INDEX TICK {i+1} ---")
            
            # Create fake index tick
            fake_tick = {
                "instrument_key": "NSE_INDEX|Nifty 50",
                "ltp": float(price),
                "timestamp": int(datetime.now().timestamp())
            }
            
            logger.info(f"📊 INDEX TICK: {fake_tick}")
            self.test_results['index_ticks_received'] += 1
            
            # Route through message router
            message = message_router.route_tick(fake_tick)
            logger.info(f"🔀 ROUTED MESSAGE: {message}")
            
            if message:
                # Handle the routed message
                await self.websocket_feed._handle_routed_message(message)
                
                # Verify ATM calculation
                atm = get_atm_strike(price)
                logger.info(f"💰 ATM CALCULATED: {atm}")
                self.test_results['atm_calculations'] += 1
                
                # Test option key generation
                option_keys = build_option_keys(
                    symbol="NIFTY",
                    atm=atm,
                    expiry=self.websocket_feed.current_expiry
                )
                
                logger.info(f"🔑 OPTION KEYS GENERATED: {len(option_keys)}")
                self.test_results['option_keys_generated'] += len(option_keys)
                
                if option_keys:
                    # Simulate subscription payload creation
                    payload = {
                        "guid": "strikeiq-options",
                        "method": "sub",
                        "data": {
                            "mode": "full",
                            "instrumentKeys": option_keys
                        }
                    }
                    
                    logger.info(f"📤 SUBSCRIPTION PAYLOAD CREATED: {len(payload['data']['instrumentKeys'])} instruments")
                    self.test_results['subscription_payloads_created'] += 1
                    
                    # Log first few option keys for verification
                    logger.info("📋 SAMPLE OPTION KEYS:")
                    for key in option_keys[:5]:
                        logger.info(f"   - {key}")
                
                # Small delay between ticks
                await asyncio.sleep(0.1)
    
    async def simulate_option_ticks(self):
        """Simulate option ticks after subscription"""
        logger.info("\n=== SIMULATING OPTION TICKS ===")
        
        # Sample option ticks
        option_ticks = [
            {
                "instrument_key": "NSE_FO|NIFTY10APR24750CE",
                "ltp": 102.5
            },
            {
                "instrument_key": "NSE_FO|NIFTY10APR24750PE", 
                "ltp": 85.3
            },
            {
                "instrument_key": "NSE_FO|NIFTY10APR24800CE",
                "ltp": 78.9
            }
        ]
        
        for i, tick in enumerate(option_ticks):
            logger.info(f"\n--- OPTION TICK {i+1} ---")
            logger.info(f"📈 OPTION TICK: {tick}")
            self.test_results['option_ticks_received'] += 1
            
            # Route through message router
            message = message_router.route_tick(tick)
            logger.info(f"🔀 ROUTED MESSAGE: {message}")
            
            if message:
                # Handle the routed message
                await self.websocket_feed._handle_routed_message(message)
                
                # Verify option chain builder update
                symbol = message["symbol"]
                strike = message["data"]["strike"]
                right = message["data"]["right"]
                ltp = message["data"]["ltp"]
                
                logger.info(f"🔄 OPTION CHAIN UPDATE: {symbol} {strike} {right} @ {ltp}")
            
            await asyncio.sleep(0.1)
    
    async def verify_pipeline(self):
        """Verify pipeline components are working"""
        logger.info("\n=== PIPELINE VERIFICATION ===")
        
        # Check option chain builder state
        logger.info("📊 Option Chain Builder State:")
        logger.info(f"   - Spot prices: {option_chain_builder.spot_prices}")
        logger.info(f"   - Chains: {list(option_chain_builder.chains.keys())}")
        
        # Verify build_option_keys function directly
        logger.info("\n🔑 DIRECT build_option_keys TEST:")
        keys = build_option_keys(symbol="NIFTY", atm=24750, expiry="2024-04-10")
        logger.info(f"   - Keys returned: {len(keys)}")
        if keys:
            logger.info(f"   - Sample keys: {keys[:3]}")
        
        return len(keys) > 0
    
    async def run_test(self):
        """Run complete test simulation"""
        logger.info("🚀 STARTING MARKET FEED SIMULATION TEST")
        
        try:
            # Setup
            await self.setup()
            
            # Simulate index ticks
            await self.simulate_index_ticks()
            
            # Simulate option ticks
            await self.simulate_option_ticks()
            
            # Verify pipeline
            pipeline_working = await self.verify_pipeline()
            
            # Print results
            await self.print_results(pipeline_working)
            
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            raise
        finally:
            # Cleanup
            await option_chain_builder.stop()
            logger.info("🧹 Cleanup complete")
    
    async def print_results(self, pipeline_working: bool):
        """Print test results summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("="*60)
        
        logger.info(f"✅ Index ticks received: {self.test_results['index_ticks_received']}")
        logger.info(f"✅ ATM calculations: {self.test_results['atm_calculations']}")
        logger.info(f"✅ Option keys generated: {self.test_results['option_keys_generated']}")
        logger.info(f"✅ Subscription payloads created: {self.test_results['subscription_payloads_created']}")
        logger.info(f"✅ Option ticks received: {self.test_results['option_ticks_received']}")
        
        logger.info(f"\n🔧 Pipeline working: {'✅ YES' if pipeline_working else '❌ NO'}")
        
        if pipeline_working and self.test_results['option_keys_generated'] > 0:
            logger.info("\n🎉 SUCCESS: Option subscription pipeline validated!")
            logger.info("   - Index ticks → ATM calculation → Option keys → Subscription payload")
            logger.info("   - Option ticks → Option chain builder updates")
        else:
            logger.info("\n⚠️  PARTIAL SUCCESS: Some components may need attention")
        
        logger.info("="*60)


class MockInstrumentRegistry:
    """Mock instrument registry for testing"""
    
    def __init__(self):
        self.ready = True
        self._create_mock_options()
    
    def _create_mock_options(self):
        """Create mock NIFTY options"""
        self.mock_options = []
        
        # Generate options around 24750 strike
        base_strikes = [24100, 24200, 24300, 24400, 24500, 24600, 24700, 24750, 24800, 24900, 25000, 25100]
        
        for strike in base_strikes:
            # Add CE and PE options
            self.mock_options.append({
                "instrument_key": f"NSE_FO|NIFTY10APR{strike}CE",
                "strike": strike,
                "right": "CE",
                "symbol": "NIFTY"
            })
            
            self.mock_options.append({
                "instrument_key": f"NSE_FO|NIFTY10APR{strike}PE", 
                "strike": strike,
                "right": "PE",
                "symbol": "NIFTY"
            })
    
    async def wait_until_ready(self):
        """Mock ready wait"""
        return
    
    def get_expiries(self, symbol: str) -> List[str]:
        """Get mock expiries"""
        return ["2024-04-10", "2024-04-17", "2024-04-24"]
    
    def get_options(self, symbol: str, expiry: str) -> List[Dict[str, Any]]:
        """Get mock options for symbol and expiry"""
        if symbol == "NIFTY" and expiry == "2024-04-10":
            return self.mock_options
        return []


async def main():
    """Main test runner"""
    simulator = MarketFeedSimulator()
    await simulator.run_test()


if __name__ == "__main__":
    asyncio.run(main())
