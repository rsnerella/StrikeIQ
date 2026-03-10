"""
AI Diagnostics Module for StrikeIQ
Comprehensive validation and diagnostic checks for all AI engines and analytics modules
"""

from app.core.diagnostics import diag

def validate_option_chain(chain):
    """Validate option chain data structure and content"""
    if not chain:
        diag("AI_TEST", "Option chain missing")
        return False

    # Handle different chain structures
    if hasattr(chain, 'strikes'):
        strikes = chain.strikes
    elif isinstance(chain, dict) and 'strikes' in chain:
        strikes = chain['strikes']
    elif isinstance(chain, list):
        strikes = chain
    else:
        diag("AI_TEST", f"Invalid option chain structure: {type(chain)}")
        return False

    if len(strikes) < 10:
        diag("AI_TEST", f"Too few strikes in option chain: {len(strikes)}")
        return False

    diag("AI_TEST", f"Option chain validated: {len(strikes)} strikes")
    return True


def validate_oi(chain):
    """Validate Open Interest data"""
    if not chain:
        diag("AI_TEST", "Cannot validate OI: no chain data")
        return False

    # Handle different chain structures
    if hasattr(chain, 'strikes'):
        strikes = chain.strikes
    elif isinstance(chain, dict) and 'strikes' in chain:
        strikes = chain['strikes']
    elif isinstance(chain, list):
        strikes = chain
    else:
        diag("AI_TEST", f"Cannot validate OI: invalid chain structure")
        return False

    total_call_oi = 0
    total_put_oi = 0

    for strike in strikes:
        if isinstance(strike, dict):
            total_call_oi += strike.get('call_oi', 0)
            total_put_oi += strike.get('put_oi', 0)
        elif hasattr(strike, 'call_oi') and hasattr(strike, 'put_oi'):
            total_call_oi += strike.call_oi
            total_put_oi += strike.put_oi

    diag("AI_TEST", f"CALL OI: {total_call_oi}")
    diag("AI_TEST", f"PUT OI: {total_put_oi}")

    if total_call_oi == 0 and total_put_oi == 0:
        diag("AI_TEST", "OI data invalid: both zero")
        return False

    return True


def validate_pcr(pcr):
    """Validate Put-Call Ratio"""
    diag("AI_TEST", f"PCR value: {pcr}")
    return pcr > 0


def validate_gamma(gamma):
    """Validate Gamma exposure"""
    diag("AI_TEST", f"Dealer gamma: {gamma}")
    return gamma != 0


def validate_expected_move(move):
    """Validate Expected Move calculation"""
    diag("AI_TEST", f"Expected move: {move}")
    return move > 0


def validate_volatility(volatility):
    """Validate volatility calculations"""
    diag("AI_TEST", f"Volatility: {volatility}")
    return volatility > 0


def validate_smart_money_signal(signal):
    """Validate smart money signal"""
    if not signal:
        diag("AI_TEST", "Smart money signal missing")
        return False
    
    bias = signal.get('bias')
    confidence = signal.get('confidence')
    
    diag("AI_TEST", f"Smart money bias: {bias}")
    diag("AI_TEST", f"Smart money confidence: {confidence}")
    
    return bias is not None and confidence is not None


def validate_gamma_pressure(gamma_map):
    """Validate gamma pressure map"""
    if not gamma_map:
        diag("AI_TEST", "Gamma pressure map missing")
        return False
    
    net_gamma = gamma_map.get('net_gamma', 0)
    total_call_gex = gamma_map.get('total_call_gex', 0)
    total_put_gex = gamma_map.get('total_put_gex', 0)
    
    diag("AI_TEST", f"Net gamma: {net_gamma}")
    diag("AI_TEST", f"Total call GEX: {total_call_gex}")
    diag("AI_TEST", f"Total put GEX: {total_put_gex}")
    
    return True


def validate_flow_gamma_interaction(interaction):
    """Validate flow-gamma interaction"""
    if not interaction:
        diag("AI_TEST", "Flow-gamma interaction missing")
        return False
    
    interaction_type = interaction.get('interaction_type')
    confidence = interaction.get('confidence')
    
    diag("AI_TEST", f"Interaction type: {interaction_type}")
    diag("AI_TEST", f"Interaction confidence: {confidence}")
    
    return interaction_type is not None and confidence is not None


def validate_strategy(strategy):
    """Validate generated strategy"""
    if not strategy:
        diag("AI_TEST", "Strategy missing")
        return False
    
    strategy_name = strategy.get('name')
    entry_price = strategy.get('entry_price')
    target_price = strategy.get('target_price')
    stop_loss = strategy.get('stop_loss')
    confidence = strategy.get('confidence')
    
    diag("AI_TEST", f"Generated strategy: {strategy_name}")
    diag("AI_TEST", f"Entry: {entry_price}")
    diag("AI_TEST", f"Target: {target_price}")
    diag("AI_TEST", f"Stoploss: {stop_loss}")
    diag("AI_TEST", f"Confidence: {confidence}")
    
    # Safety guard validation
    if confidence and confidence < 50:
        diag("AI_TEST", "Rejecting strategy: confidence too low")
        return False
    
    return True


def validate_ai_signal(signal):
    """Validate AI signal"""
    if not signal:
        diag("AI_TEST", "AI signal missing")
        return False
    
    signal_type = signal.get('type')
    symbol = signal.get('symbol')
    confidence = signal.get('confidence')
    
    diag("AI_TEST", f"AI signal type: {signal_type}")
    diag("AI_TEST", f"AI signal symbol: {symbol}")
    diag("AI_TEST", f"AI signal confidence: {confidence}")
    
    return signal_type is not None and symbol is not None


def validate_advanced_strategy(strategy):
    """Validate advanced strategy detection"""
    if not strategy:
        diag("AI_TEST", "Advanced strategy missing")
        return False
    
    pattern_type = strategy.get('pattern_type')
    confidence = strategy.get('confidence')
    
    diag("AI_TEST", f"Advanced pattern: {pattern_type}")
    diag("AI_TEST", f"Pattern confidence: {confidence}")
    
    return pattern_type is not None and confidence is not None


def run_comprehensive_validation(data):
    """Run comprehensive validation on all AI components"""
    diag("AI_TEST", "Starting comprehensive AI validation")
    
    validation_results = {}
    
    # Validate option chain
    if 'option_chain' in data:
        validation_results['option_chain'] = validate_option_chain(data['option_chain'])
        validation_results['oi'] = validate_oi(data['option_chain'])
    
    # Validate PCR
    if 'pcr' in data:
        validation_results['pcr'] = validate_pcr(data['pcr'])
    
    # Validate gamma
    if 'gamma' in data:
        validation_results['gamma'] = validate_gamma(data['gamma'])
    
    # Validate expected move
    if 'expected_move' in data:
        validation_results['expected_move'] = validate_expected_move(data['expected_move'])
    
    # Validate volatility
    if 'volatility' in data:
        validation_results['volatility'] = validate_volatility(data['volatility'])
    
    # Validate smart money
    if 'smart_money' in data:
        validation_results['smart_money'] = validate_smart_money_signal(data['smart_money'])
    
    # Validate gamma pressure
    if 'gamma_pressure' in data:
        validation_results['gamma_pressure'] = validate_gamma_pressure(data['gamma_pressure'])
    
    # Validate flow-gamma interaction
    if 'flow_gamma' in data:
        validation_results['flow_gamma'] = validate_flow_gamma_interaction(data['flow_gamma'])
    
    # Validate strategy
    if 'strategy' in data:
        validation_results['strategy'] = validate_strategy(data['strategy'])
    
    # Validate AI signal
    if 'ai_signal' in data:
        validation_results['ai_signal'] = validate_ai_signal(data['ai_signal'])
    
    # Validate advanced strategy
    if 'advanced_strategy' in data:
        validation_results['advanced_strategy'] = validate_advanced_strategy(data['advanced_strategy'])
    
    # Summary
    passed = sum(1 for result in validation_results.values() if result)
    total = len(validation_results)
    
    diag("AI_TEST", f"Validation summary: {passed}/{total} checks passed")
    
    return validation_results
