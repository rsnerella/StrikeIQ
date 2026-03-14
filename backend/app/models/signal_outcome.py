from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from .database import Base

class SignalOutcome(Base):
    """
    Signal Outcome table for storing results of AI signals (WIN/LOSS/HOLD)
    Matches the schema in strikeiq_schema.sql
    """
    __tablename__ = "signal_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("ai_signal_logs.id"), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    outcome_type = Column(String)  # e.g., "5m", "15m", "30m"
    outcome_value = Column(Float, nullable=True)  # Price move amount
    accuracy = Column(Float, nullable=True)
    result = Column(String)  # WIN, LOSS, HOLD
    
    outcome_metadata = Column("metadata", JSON)  # Additional flags or prices

    def __repr__(self):
        return f"<SignalOutcome(id={self.id}, signal_id={self.signal_id}, result={self.result})>"
