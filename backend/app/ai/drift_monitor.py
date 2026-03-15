"""
Model Drift Monitor for StrikeIQ
Observes feature stability and adjusts confidence
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class ModelDriftMonitor:
    """
    Tracks the distribution of input features and compares them to training baselines.
    Detects when market conditions have shifted significantly (drift), reducing AI conviction.
    """
    
    def __init__(self):
        self._baseline_features: Dict[str, List[float]] = {}
        self._drift_score = 0.0
        logger.info("ModelDriftMonitor initialized")

    def observe(self, fv: Any) -> float:
        """
        Observes a new feature vector and returns a drift score (0.0 to 1.0).
        0.0 = No drift, 1.0 = Extreme drift (unreliable model).
        """
        # In a real system, this would compare against a stored baseline distribution.
        # For now, we use a simple heuristic based on feature extremes.
        
        drift = 0.0
        
        # Check for abnormal volatility
        if fv.volatility_15m > 0.05: # 5% move in 15m is extreme drift from normal regimes
            drift += 0.4
            
        # Check for abnormal PCR
        if fv.pcr_ratio > 3.0 or fv.pcr_ratio < 0.2:
            drift += 0.3
            
        self._drift_score = float(np.clip(drift, 0.0, 1.0))
        
        if self._drift_score > 0.5:
            logger.warning(f"Significant model drift detected: {self._drift_score:.2f}")
            
        return self._drift_score

    @property
    def current_drift(self) -> float:
        return self._drift_score

model_drift_monitor = ModelDriftMonitor()
