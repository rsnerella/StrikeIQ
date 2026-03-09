import logging
import os
import pickle
import pandas as pd
import asyncio
from sqlalchemy import text
from app.models.database import engine
from app.core.async_db import get_db_pool

logger = logging.getLogger(__name__)

class ProbabilityEngine:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "strikeiq_model.pkl")
        self.ml_model = None
        self.model_columns = []
        self._load_model()
        
    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.ml_model = data["model"]
                    self.model_columns = data["columns"]
                    logger.info("ML model loaded successfully")
            else:
                logger.warning("ML model not found, running without ML predictions")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")

    def predict(self, symbol: str, features: dict) -> dict:
        """
        Generate probability predictions.
        Input: feature vector from feature_builder
        Output: BUY probability, SELL probability
        """
        try:
            if not self.ml_model or not features:
                return {}

            # Convert features dict to DataFrame
            df = pd.DataFrame([features])
            
            # One-hot encode categorical exactly like training
            df_cat = pd.get_dummies(df[["wave", "trend"]])
            df_num = df[["price", "pcr", "gamma_exposure", "oi_velocity"]].rename(columns={"gamma_exposure":"gamma"})
            df_combined = pd.concat([df_num, df_cat], axis=1)

            # Ensure all columns exist from training
            for col in self.model_columns:
                if col not in df_combined.columns:
                    df_combined[col] = 0

            # Only use columns the model was trained on
            X = df_combined[self.model_columns]

            # Generate probabilities
            prob = self.ml_model.predict_proba(X)[0]
            # Assumes binary classification 0: SELL/LOSS, 1: BUY/WIN
            sell_prob = float(prob[0])
            buy_prob = float(prob[1]) if len(prob) > 1 else 0.0

            # Define signal, target, stop 
            # Simplified target/stop calculation
            signal = "BUY" if buy_prob > 0.55 else "SELL" if sell_prob > 0.55 else "WAIT"
            price = features.get("price", 0)
            target = price * 1.005 if signal == "BUY" else price * 0.995
            stop = price * 0.997 if signal == "BUY" else price * 1.003
            
            # Use max probability as the primary prediction confidence
            probability = max(buy_prob, sell_prob)
            
            # Log into ai_predictions asynchronously
            from datetime import datetime
            try:
                async def store_prediction():
                    pool = get_db_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO ai_predictions (symbol, timestamp, probability, signal, target, stop) VALUES ($1, $2, $3, $4, $5, $6)",
                            symbol, datetime.now(), probability, signal, target, stop
                        )
                
                # Fire and forget to avoid blocking analytics pipeline
                asyncio.create_task(store_prediction())
            except Exception as e:
                logger.error(f"Failed to store AI prediction: {e}")

            return {
                "type": "ai_prediction",
                "symbol": symbol,
                "probability": probability,
                "signal": signal,
                "target": target,
                "stop": stop,
                "buy_probability": buy_prob,
                "sell_probability": sell_prob
            }

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {}

probability_engine = ProbabilityEngine()
