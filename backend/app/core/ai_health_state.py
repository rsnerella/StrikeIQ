"""
AI Health State Tracker for StrikeIQ
Global tracking of AI engine health for UI visibility
"""

# Global AI health state
AI_HEALTH = {
    "option_chain": False,
    "gamma": False,
    "volatility": False,
    "flow": False,
    "strategy": False
}

def mark_health(key: str):
    """Mark an AI component as healthy/active"""
    if key in AI_HEALTH:
        AI_HEALTH[key] = True
    else:
        # Log warning for unknown keys but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Unknown AI health key: {key}")

def get_health() -> dict:
    """Get current AI health state"""
    return AI_HEALTH.copy()

def reset_health():
    """Reset all AI health states to False"""
    global AI_HEALTH
    for key in AI_HEALTH:
        AI_HEALTH[key] = False

def is_healthy(key: str) -> bool:
    """Check if a specific AI component is healthy"""
    return AI_HEALTH.get(key, False)

def get_healthy_count() -> int:
    """Get count of healthy AI components"""
    return sum(1 for healthy in AI_HEALTH.values() if healthy)

def get_total_count() -> int:
    """Get total count of AI components"""
    return len(AI_HEALTH)
