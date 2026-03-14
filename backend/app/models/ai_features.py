"""
AI Features Database Model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class AIFeature(Base):
    """AI Feature record for ML training"""
    __tablename__ = 'ai_features'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Individual feature columns
    pcr = Column(Float, nullable=True)  # Put-Call Ratio
    gamma_exposure = Column(Float, nullable=True)  # Gamma exposure
    oi_velocity = Column(Float, nullable=True)  # Open Interest velocity
    volatility = Column(Float, nullable=True)  # Volatility measure
    trend_strength = Column(Float, nullable=True)  # Trend strength
    liquidity_score = Column(Float, nullable=True)  # Liquidity score
    market_regime = Column(String(20), nullable=True)  # Market regime
    
    # Full feature vector as JSON
    feature_vector_json = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<AIFeature(symbol={self.symbol}, timestamp={self.timestamp})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'pcr': self.pcr,
            'gamma_exposure': self.gamma_exposure,
            'oi_velocity': self.oi_velocity,
            'volatility': self.volatility,
            'trend_strength': self.trend_strength,
            'liquidity_score': self.liquidity_score,
            'market_regime': self.market_regime,
            'feature_vector_json': self.feature_vector_json
        }
