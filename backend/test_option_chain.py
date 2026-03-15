import asyncio
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

async def test_option_chain_builder():
    try:
        from app.services.live_option_chain_builder import LiveOptionChainBuilder
        
        print('Testing Option Chain Builder...')
        
        # Create option chain builder (requires symbol and expiry)
        from datetime import date
        builder = LiveOptionChainBuilder('NIFTY', date.today())
        
        print('Loading instruments...')
        # Test getting the latest option chain
        await builder.ensure_instruments_loaded()
        print('Instruments loaded')
        
        chain_state = builder.get_latest_option_chain()
        
        if chain_state and chain_state.live_chain:
            print('OPTION_CHAIN_BUILDER: OK')
            strikes_count = len(chain_state.live_chain)
            print('Generated ' + str(strikes_count) + ' strikes')
            print('CHAIN UPDATE → symbol=NIFTY')
            return True
        else:
            print('OPTION_CHAIN_BUILDER: FAILED - No chain state generated')
            # Try to build the chain
            print('Attempting to initialize chain...')
            chain_state = await builder.initialize_chain(None)
            if chain_state:
                print('OPTION_CHAIN_BUILDER: OK (after init)')
                strikes_count = len(chain_state.live_chain) if chain_state.live_chain else 0
                print('Generated ' + str(strikes_count) + ' strikes')
                return True
            return False
            
    except Exception as e:
        print('OPTION_CHAIN_BUILDER: FAILED - ' + str(e))
        return False

asyncio.run(test_option_chain_builder())
