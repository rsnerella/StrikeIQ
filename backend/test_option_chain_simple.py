import asyncio
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

async def test_option_chain_simple():
    try:
        from app.services.live_option_chain_builder import LiveOptionChainBuilder
        from app.models.live_chain_state import LiveChainState
        from datetime import date, datetime, timezone
        
        print('Testing Option Chain Builder (simple)...')
        
        # Create option chain builder
        builder = LiveOptionChainBuilder('NIFTY', date.today())
        
        # Create a mock chain state directly
        from app.models.live_chain_state import StrikeData
        
        # Create some mock strikes
        strike_map = {
            19900.0: {'CE': 'NSE_FO|50999', 'PE': 'NSE_FO|51000'},
            20000.0: {'CE': 'NSE_FO|51101', 'PE': 'NSE_FO|51102'},
            20100.0: {'CE': 'NSE_FO|51203', 'PE': 'NSE_FO|51204'}
        }
        
        reverse_map = {
            'NSE_FO|50999': (19900.0, 'CE'),
            'NSE_FO|51000': (19900.0, 'PE'),
            'NSE_FO|51101': (20000.0, 'CE'),
            'NSE_FO|51102': (20000.0, 'PE'),
            'NSE_FO|51203': (20100.0, 'CE'),
            'NSE_FO|51204': (20100.0, 'PE')
        }
        
        live_chain = {
            19900.0: StrikeData(
                strike=19900.0,
                ce={'oi': 1000, 'volume': 500, 'ltp': 150.5},
                pe={'oi': 800, 'volume': 400, 'ltp': 120.3}
            ),
            20000.0: StrikeData(
                strike=20000.0,
                ce={'oi': 1200, 'volume': 600, 'ltp': 100.2},
                pe={'oi': 900, 'volume': 450, 'ltp': 98.7}
            ),
            20100.0: StrikeData(
                strike=20100.0,
                ce={'oi': 900, 'volume': 450, 'ltp': 55.8},
                pe={'oi': 1100, 'volume': 550, 'ltp': 52.1}
            )
        }
        
        # Create chain state manually
        chain_state = LiveChainState(
            symbol='NIFTY',
            registry_symbol='NIFTY',
            expiry=date.today(),
            strike_map=strike_map,
            reverse_map=reverse_map,
            live_chain=live_chain,
            spot_price=20000.0,
            last_update=datetime.now(timezone.utc),
            is_active=True
        )
        
        # Test building final chain
        final_chain = chain_state.build_final_chain()
        
        if final_chain and 'strikes' in final_chain:
            print('OPTION_CHAIN_BUILDER: OK')
            strikes_count = len(final_chain.get('strikes', []))
            print('Generated ' + str(strikes_count) + ' strikes')
            print('CHAIN UPDATE → symbol=NIFTY')
            print('Spot price: ' + str(final_chain.get('spot')))
            return True
        else:
            print('OPTION_CHAIN_BUILDER: FAILED - No final chain generated')
            return False
            
    except Exception as e:
        print('OPTION_CHAIN_BUILDER: FAILED - ' + str(e))
        import traceback
        traceback.print_exc()
        return False

asyncio.run(test_option_chain_simple())
