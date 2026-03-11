from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.sql import func
from .database import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    spot_price = Column(Float)
    vwap = Column(Float, nullable=True)
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)

    # FIXED
    volume = Column(BigInteger, nullable=True)

    market_status = Column(String, nullable=True)

    # Derived directional features
    rsi = Column(Float, nullable=True)
    momentum_score = Column(Float, nullable=True)
    regime = Column(String, nullable=True)
    pcr = Column(Float, nullable=True)
    total_call_oi = Column(BigInteger, nullable=True)
    total_put_oi = Column(BigInteger, nullable=True)
    atm_strike = Column(Float, nullable=True)
    gamma_exposure = Column(Float, nullable=True)
    expected_move = Column(Float, nullable=True)


class OptionChainSnapshot(Base):
    __tablename__ = "option_chain_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    market_snapshot_id = Column(Integer, ForeignKey("market_snapshots.id"))

    symbol = Column(String, index=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    strike = Column(Float, index=True)
    option_type = Column(String)  # CE / PE
    expiry = Column(String)

    # FIXED BIGINT FIELDS
    oi = Column(BigInteger)
    oi_change = Column(BigInteger, nullable=True)
    prev_oi = Column(BigInteger, nullable=True)
    oi_delta = Column(BigInteger, nullable=True)

    ltp = Column(Float)
    iv = Column(Float)

    volume = Column(BigInteger)

    theta = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)


class SmartMoneyPrediction(Base):
    __tablename__ = "smart_money_predictions"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol = Column(String, index=True)

    bias = Column(String)  # BULLISH / BEARISH / NEUTRAL
    confidence = Column(Float)

    pcr = Column(Float)
    pcr_shift_z = Column(Float)

    atm_straddle = Column(Float)
    straddle_change_normalized = Column(Float)

    oi_acceleration_ratio = Column(Float)

    iv_regime = Column(String)

    actual_move = Column(Float, nullable=True)

    result = Column(String, nullable=True)

    model_version = Column(String, default="v1.0")

    expiry_date = Column(String)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol = Column(String, index=True)

    bullish_probability = Column(Float)
    volatility_probability = Column(Float)
    confidence_score = Column(Float)

    regime = Column(String)

    actual_move_30m = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)

    model_version = Column(String)