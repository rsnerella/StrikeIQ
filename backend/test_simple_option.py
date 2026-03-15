print('Testing option chain builder...')
try:
    import sys
    sys.path.append('.')
    from app.services.live_option_chain_builder import LiveOptionChainBuilder
    print('Import successful')
    builder = LiveOptionChainBuilder('NIFTY', '2025-06-26')
    print('Builder created')
    print('OPTION_CHAIN_BUILDER: OK')
except Exception as e:
    print('FAILED: ' + str(e))
