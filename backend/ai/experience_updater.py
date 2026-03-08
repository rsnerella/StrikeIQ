import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.models.database import AsyncSessionLocal, Base

logger = logging.getLogger(__name__)

# Create FormulaExperience model since it doesn't exist
class FormulaExperience(Base):
    """Formula experience tracking table"""
    __tablename__ = "formula_experience"
    
    id = Column(Integer, primary_key=True)
    formula_id = Column(String, index=True)
    total_tests = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

class ExperienceUpdater:
    def __init__(self):
        # Use SQLAlchemy session instead of duplicate database connection
        pass
        
    def get_formula_experience(self, formula_id: str) -> Optional[dict]:
        """Get current experience statistics for a formula"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Query formula experience
            experience = db.query(FormulaExperience).filter(
                FormulaExperience.formula_id == formula_id
            ).first()
            
            if experience:
                return {
                    'total_tests': experience.total_tests,
                    'wins': experience.wins,
                    'losses': experience.losses,
                    'success_rate': experience.success_rate
                }
            else:
                # Initialize new formula experience
                self.initialize_formula_experience(formula_id)
                return {
                    'total_tests': 0,
                    'wins': 0,
                    'losses': 0,
                    'success_rate': 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting formula experience for {formula_id}: {e}")
            return None
        finally:
            try:
                db.close()
            except:
                pass
            
    def initialize_formula_experience(self, formula_id: str):
        """Initialize experience record for a new formula"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Create new formula experience record
            experience = FormulaExperience(
                formula_id=formula_id,
                total_tests=0,
                wins=0,
                losses=0,
                success_rate=0.0,
                last_updated=datetime.now()
            )
            
            # Add to session and commit
            db.add(experience)
            db.commit()
            
            logger.info(f"Initialized experience for formula {formula_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing formula experience: {e}")
            # Rollback on error
            try:
                db.rollback()
            except:
                pass
            return False
        finally:
            # Always close session
            try:
                db.close()
            except:
                pass
            
    def update_formula_experience(self, formula_id: str, is_win: bool):
        """Update formula experience after a trade outcome"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Get current experience
            experience = db.query(FormulaExperience).filter(
                FormulaExperience.formula_id == formula_id
            ).first()
            
            if experience:
                # Update statistics
                experience.total_tests += 1
                if is_win:
                    experience.wins += 1
                else:
                    experience.losses += 1
                
                # Calculate new success rate
                experience.success_rate = (experience.wins / experience.total_tests) * 100 if experience.total_tests > 0 else 0.0
                experience.last_updated = datetime.now()
                
                db.commit()
                
                logger.info(f"Updated experience for {formula_id}: {experience.success_rate:.1f}% success rate")
                return True
            else:
                # Initialize if not found
                self.initialize_formula_experience(formula_id)
                return self.update_formula_experience(formula_id, is_win)
                
        except Exception as e:
            logger.error(f"Error updating formula experience: {e}")
            # Rollback on error
            try:
                db.rollback()
            except:
                pass
            return False
        finally:
            # Always close session
            try:
                db.close()
            except:
                pass

    def update_experience(self, formula_id: str, outcome: str):
        """
        Update experience statistics for a formula based on prediction outcome
        
        Args:
            formula_id: Formula identifier (e.g., F01, F02, etc.)
            outcome: Prediction outcome (WIN/LOSS/NEUTRAL)
        """
        try:
            # Get database session
            db = SessionLocal()
            
            # Get current experience
            experience = db.query(FormulaExperience).filter(
                FormulaExperience.formula_id == formula_id
            ).first()
            
            if not experience:
                logger.error(f"Could not get experience for formula {formula_id}")
                return False
                
            # Update counters based on outcome
            experience.total_tests += 1
            wins = experience.wins
            losses = experience.losses
            
            if outcome == 'WIN':
                wins += 1
            elif outcome == 'LOSS':
                losses += 1
            # NEUTRAL doesn't increment wins or losses
            
            # Calculate new success rate
            experience.success_rate = (wins / experience.total_tests) * 100 if experience.total_tests > 0 else 0.0
            experience.last_updated = datetime.now()
            
            db.commit()
            
            logger.info(f"Updated experience for {formula_id}: {outcome} -> {experience.total_tests} tests, {wins} wins, {losses} losses, {experience.success_rate:.2f}% success rate")
            return True
                
        except Exception as e:
            logger.error(f"Error updating experience for {formula_id}: {e}")
            # Rollback on error
            try:
                db.rollback()
            except:
                pass
            return False
        finally:
            # Always close session
            try:
                db.close()
            except:
                pass
            
    def get_top_performers(self, limit: int = 10) -> list:
        """Get top performing formulas based on success rate"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Query for top performing formulas
            performers = db.query(FormulaExperience).filter(
                FormulaExperience.total_tests >= 10  # Only include formulas with sufficient data
            ).order_by(
                FormulaExperience.success_rate.desc(),
                FormulaExperience.total_tests.desc()
            ).limit(limit).all()
            
            result = []
            for performer in performers:
                result.append({
                    'formula_id': performer.formula_id,
                    'total_tests': performer.total_tests,
                    'wins': performer.wins,
                    'losses': performer.losses,
                    'success_rate': performer.success_rate
                })
                
            logger.info(f"Retrieved top {len(result)} performing formulas")
            return result
            
        except Exception as e:
            logger.error(f"Error getting top performers: {e}")
            return []
        finally:
            # Always close session
            try:
                db.close()
            except:
                pass

# Global experience updater instance
experience_updater = ExperienceUpdater()
