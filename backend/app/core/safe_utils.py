# Safe utility functions for StrikeIQ reliability

def safe(obj, key, default=None):
    """Safe attribute access with fallback"""
    return getattr(obj, key, default)

def safe_get(obj, key, default=None):
    """Safe dict get with fallback"""
    return obj.get(key, default) if hasattr(obj, 'get') else default

def safe_float(value, default=0.0):
    """Safe float conversion"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safe int conversion"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def validate_oi(call_oi, put_oi):
    """Validate OI data"""
    return call_oi > 0 or put_oi > 0

def validate_pcr(pcr):
    """Validate PCR data"""
    return pcr > 0 and pcr != float('inf')

def validate_spot(spot):
    """Validate spot price"""
    return spot > 0 and spot != float('inf')
