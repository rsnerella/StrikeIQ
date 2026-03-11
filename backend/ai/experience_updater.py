import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import Column, Integer, String, Float, DateTime, select, update, JSON
from sqlalchemy.sql import func
from app.models.database import AsyncSessionLocal, Base

logger = logging.getLogger(__name__)

# Model definition (ideally moved to app/models but kept here for proximity)
class FormulaExperience(Base):
    """Formula experience tracking table"""
    __tablename__ = "formula_experience"
    
    id = Column(Integer, primary_key=True)
    formula_id = Column(String, index=True)
    total_tests = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    avg_reward = Column(Float, default=0.0)
    avg_risk = Column(Float, default=0.0)
    confidence_adjustment = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    experience_adjusted_confidence = Column(Float, default=0.0)
    confidence_stats = Column(JSON, default=dict) # Phase 5: Track win-rate by tier
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ExperienceUpdater:
    def __init__(self):
        pass
        
    async def get_formula_experience(self, formula_id: str) -> Optional[dict]:
        """Get current experience statistics for a formula (Async)"""
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(FormulaExperience).where(FormulaExperience.formula_id == formula_id)
                result = await db.execute(stmt)
                experience = result.scalar_one_or_none()
                
                if experience:
                    return {
                        'total_tests': experience.total_tests,
                        'wins': experience.wins,
                        'losses': experience.losses,
                        'success_rate': experience.success_rate
                    }
                else:
                    await self.initialize_formula_experience(formula_id)
                    return {
                        'total_tests': 0, 'wins': 0, 'losses': 0, 'success_rate': 0.0
                    }
        except Exception as e:
            logger.error(f"Error getting experience for {formula_id}: {e}")
            return None
            
    async def initialize_formula_experience(self, formula_id: str):
        """Initialize experience record for a new formula (Async)"""
        try:
            async with AsyncSessionLocal() as db:
                experience = FormulaExperience(formula_id=formula_id)
                db.add(experience)
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error initializing experience for {formula_id}: {e}")
            return False
            
    async def update_experience(self, formula_id: str, outcome: str, confidence: float = 0, pnl: float = 0):
        """Update experience statistics for a formula (Async)"""
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(FormulaExperience).where(FormulaExperience.formula_id == formula_id)
                result = await db.execute(stmt)
                exp = result.scalar_one_or_none()
                
                if not exp:
                    exp = FormulaExperience(
                        formula_id=formula_id,
                        wins=0,
                        losses=0,
                        total_tests=0,
                        avg_reward=0.0,
                        avg_risk=0.0,
                        accuracy=0.0
                    )
                    db.add(exp)
                
                exp.total_tests += 1
                if outcome == 'WIN':
                    old_wins = exp.wins
                    exp.wins += 1
                    # Moving average for reward
                    exp.avg_reward = ((exp.avg_reward * old_wins) + pnl) / exp.wins if exp.wins > 0 else pnl
                elif outcome == 'LOSS':
                    old_losses = exp.losses
                    exp.losses += 1
                    # Moving average for risk (store as positive)
                    loss_val = abs(pnl)
                    exp.avg_risk = ((exp.avg_risk * old_losses) + loss_val) / exp.losses if exp.losses > 0 else loss_val
                
                # Accuracy calculation (Phase 5)
                exp.accuracy = (exp.wins / (exp.wins + exp.losses)) * 100 if (exp.wins + exp.losses) > 0 else 0.0
                exp.success_rate = exp.accuracy
                
                # Confidence Tier Tracking (Phase 5)
                stats = dict(exp.confidence_stats or {})
                tier = f"{int(confidence * 10) * 10}" # e.g. "70" for 0.75
                if tier not in stats: stats[tier] = {'wins': 0, 'losses': 0}
                
                if outcome == 'WIN': stats[tier]['wins'] += 1
                elif outcome == 'LOSS': stats[tier]['losses'] += 1
                exp.confidence_stats = stats

                # Confidence calibration / adjustment logic (Phase 4: Sample Size >= 20)
                if exp.total_tests >= 20:
                    if exp.accuracy > 70:
                        exp.confidence_adjustment = 0.15
                    elif exp.accuracy < 40:
                        exp.confidence_adjustment = -0.2
                    else:
                        exp.confidence_adjustment = 0.0
                else:
                    exp.confidence_adjustment = 0.0
                
                exp.experience_adjusted_confidence = min(1.0, max(0.1, 0.5 + exp.confidence_adjustment))
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating experience: {e}")
            return False
            
    async def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """Get top performing formulas (Async)"""
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(FormulaExperience).where(
                    FormulaExperience.total_tests >= 5
                ).order_by(FormulaExperience.success_rate.desc()).limit(limit)
                
                result = await db.execute(stmt)
                performers = result.scalars().all()
                return [{
                    'formula_id': p.formula_id,
                    'total_tests': p.total_tests,
                    'wins': p.wins,
                    'losses': p.losses,
                    'success_rate': p.success_rate
                } for p in performers]
        except Exception as e:
            logger.error(f"Error getting performers: {e}")
            return []

# Global instance
experience_updater = ExperienceUpdater()

