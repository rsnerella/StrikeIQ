import logging

logger = logging.getLogger(__name__)

class FeatureBuilder:
    def build_features(self, signal_payload: dict) -> dict:
        """
        Converts signals into ML features.
        signal_payload example: output from chart analysis or scoring engine.
        Returns a dict of features ready to be inserted into ai_features table and used for prediction.
        """
        try:
            # Extract basic vars, providing defaults
            price = signal_payload.get("price", 0.0)
            if not price and "spot" in signal_payload:
                price = signal_payload["spot"]

            pcr = float(signal_payload.get("pcr", 1.0) or 1.0)
            gamma_exposure = float(signal_payload.get("gamma", 0.0) or 0.0)
            oi_velocity = float(signal_payload.get("oi_velocity", 0.0) or 0.0)
            wave = str(signal_payload.get("wave", "unknown"))
            momentum = float(signal_payload.get("momentum", 0.0) or 0.0)
            volatility = float(signal_payload.get("volatility", 0.0) or 0.0)
            trend = str(signal_payload.get("trend", "neutral"))
            
            # Map categorical variables to numeric if needed by model, but we'll return raw features 
            # and let ml_training_engine handle encoding.
            features = {
                "price": price,
                "pcr": pcr,
                "gamma_exposure": gamma_exposure,
                "oi_velocity": oi_velocity,
                "wave": wave,
                "momentum": momentum,
                "volatility": volatility,
                "trend": trend,
                "label": signal_payload.get("signal", "WAIT")
            }
            return features
        except Exception as e:
            logger.error(f"FeatureBuilder error: {e}")
            return {}

feature_builder = FeatureBuilder()
