import logging
import pandas as pd
from sqlalchemy import text
from app.models.database import engine

logger = logging.getLogger(__name__)

class TrainingDatasetBuilder:
    def build_dataset(self) -> pd.DataFrame:
        """
        Loads signal logs and outcomes, combines them into an ML dataset.
        Returns a Pandas DataFrame: X=features, y=result
        """
        try:
            with engine.connect() as conn:
                # Joining ai_signal_logs and signal_outcomes and potentially ai_features.
                # Since the instructions mention ai_signal_logs + signal_outcomes -> features.
                # If feature_builder handles real-time, we can also build historical features 
                # or read from ai_features table joined with signal_outcomes.
                
                query = text("""
                    SELECT 
                        l.id as signal_id,
                        l.price, l.pcr, l.gamma, l.oi_velocity, l.wave, l.trend,
                        o.result
                    FROM ai_signal_logs l
                    JOIN signal_outcomes o ON l.id = o.signal_id
                    WHERE o.result IS NOT NULL
                """)
                
                df = pd.read_sql(query, conn)
                
            if len(df) == 0:
                logger.warning("No data found for training dataset")
                return pd.DataFrame()
            
            # Map result to categorical / numerical
            # result might be WIN / LOSS / HOLD
            # Let's map target variable for binary classification or multiclass
            # we'll let ml_training_engine decide
            
            return df
        except Exception as e:
            logger.error(f"Error building training dataset: {e}")
            return pd.DataFrame()

training_dataset_builder = TrainingDatasetBuilder()
