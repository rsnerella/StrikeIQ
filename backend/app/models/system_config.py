from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from .database import Base

class SystemConfig(Base):
    """
    System configuration table for storing settings and state
    (e.g., Upstox auth tokens)
    Replaces local file storage for stateless architecture
    """
    __tablename__ = "system_config"

    key = Column(String, primary_key=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemConfig(key={self.key})>"
