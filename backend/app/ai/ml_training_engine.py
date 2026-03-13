import os
import pickle
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import text
from app.models.database import engine

logger = logging.getLogger(__name__)

class MLTrainingEngine:
    def __init__(self):
        self.model_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "strikeiq_model.pkl")

    def train(self):
        """
        Loads features, trains ML model (XGBoost/LightGBM or falling back to Scikit-Learn RandomForest if unsupported), Evaluate accuracy, save to pkl.
        """
        logger.info("Starting ML Training")
        try:
            from app.services.training_dataset_builder import training_dataset_builder
            df = training_dataset_builder.build_dataset()
            
            if df.empty or len(df) < 10:
                logger.warning("Not enough data to train ML model")
                return False

            # Drop missing values
            df = df.dropna()

            # Prepare X and y
            # One-hot encode categorical features: wave, trend
            X_cat = pd.get_dummies(df[["wave", "trend"]])
            X_num = df[["price", "pcr", "gamma", "oi_velocity"]]
            X = pd.concat([X_num, X_cat], axis=1)
            
            # Map labels to numeric 0: HOLD/LOSS, 1: WIN
            y = df["result"].apply(lambda x: 1 if x == "WIN" else 0)

            # Train/test split
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Try to use xgboost, fallback to RandomForest
            try:
                import xgboost as xgb
                model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1)
            except ImportError:
                logger.warning("xgboost not installed, using RandomForestClassifier")
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=100, max_depth=3)

            model.fit(X_train, y_train)

            # Evaluate accuracy
            from sklearn.metrics import accuracy_score
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            logger.info(f"Model trained with accuracy: {accuracy:.4f}")

            # Save model
            with open(self.model_path, "wb") as f:
                pickle.dump({"model": model, "columns": X.columns.tolist(), "accuracy": accuracy}, f)
                
            # Log into ai_models table
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO ai_models (model_name, version, accuracy, trained_on, dataset_size) VALUES (:name, :version, :acc, :time, :size)"),
                    {"name": "XGB_StrikeIQ", "version": "v1.0", "acc": accuracy, "time": datetime.now(), "size": len(df)}
                )
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to train ML model: {e}", exc_info=True)
            return False

ml_training_engine = MLTrainingEngine()
