"""
AI Predictions Database Model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class AIPrediction(Base):
    """AI Prediction record for ML logging"""
    __tablename__ = 'ai_predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Prediction results
    buy_probability = Column(Float, nullable=True)
    sell_probability = Column(Float, nullable=True)
    strategy = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True, index=True)
    model_version = Column(String(20), nullable=True)
    signal_type = Column(String(20), nullable=True)
    prediction_successful = Column(Boolean, nullable=True)
    
    # Input features and metadata
    features = Column(JSON, nullable=True)
    feature_importance = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<AIPrediction(symbol={self.symbol}, timestamp={self.timestamp}, confidence={self.confidence_score})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'buy_probability': self.buy_probability,
            'sell_probability': self.sell_probability,
            'strategy': self.strategy,
            'confidence_score': self.confidence_score,
            'model_version': self.model_version,
            'signal_type': self.signal_type,
            'prediction_successful': self.prediction_successful,
            'features': self.features,
            'feature_importance': self.feature_importance
        }
