from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import asyncio
from .outcome_checker import outcome_checker
from app.services.market_session_manager import get_market_session_manager
from app.services.ai_outcome_engine import AIOutcomeEngine

logger = logging.getLogger(__name__)

class AIScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.market_session_manager = get_market_session_manager()
        self.setup_jobs()
        
    def setup_jobs(self):
        """Setup scheduled jobs for AI learning system"""
        try:
            # Signal generation job → every 5 seconds
            self.scheduler.add_job(
                func=self.signal_generation_job,
                trigger=IntervalTrigger(seconds=5),
                id='signal_generation',
                name='Generate AI signals',
                replace_existing=True,
                max_instances=1  # Prevent overlapping
            )
            
            # Paper trade monitor → every 10 seconds
            self.scheduler.add_job(
                func=self.paper_trade_monitor_job,
                trigger=IntervalTrigger(seconds=10),
                id='paper_trade_monitor',
                name='Monitor paper trades',
                replace_existing=True,
                max_instances=1  # Prevent overlapping
            )
            
            # New prediction processing → every 15 seconds
            self.scheduler.add_job(
                func=self.new_prediction_processing_job,
                trigger=IntervalTrigger(seconds=15),
                id='new_prediction_processing',
                name='Process new predictions',
                replace_existing=True,
                max_instances=1  # Prevent overlapping
            )
            
            # Outcome checker → every 1 minute
            from app.services.ai_outcome_engine import AIOutcomeEngine
            engine = AIOutcomeEngine()
            self.scheduler.add_job(
                engine.evaluate_pending_outcomes,
                "interval",
                minutes=1,
                id='outcome_checker',
                name='Evaluate prediction outcomes',
                replace_existing=True,
                max_instances=1
            )
            
            # Learning updater → every 1 minute
            self.scheduler.add_job(
                func=self.learning_update_job,
                trigger=IntervalTrigger(minutes=1),
                id='learning_update',
                name='Update AI learning',
                replace_existing=True,
                max_instances=1  # Prevent overlapping
            )
            
            # ML Model Training → everyday at 16:00 IST
            self.scheduler.add_job(
                func=self.ml_training_job,
                trigger=CronTrigger(hour=16, minute=0, timezone='Asia/Kolkata'),
                id='ml_training',
                name='ML Model Training',
                replace_existing=True,
                max_instances=1  # Prevent overlapping
            )
            
            # Adaptive learning update → every 30 minutes (Step 11)
            self.scheduler.add_job(
                func=self.adaptive_learning_job,
                trigger=IntervalTrigger(minutes=30),
                id='adaptive_learning',
                name='Update strategy learning scores',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info("AI scheduler jobs setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up scheduler jobs: {e}")
            
    async def adaptive_learning_job(self):
        """Job for updating AI strategy scores based on history (Step 11)"""
        try:
            from ai.adaptive_learning_engine import adaptive_learning_engine
            scores = await adaptive_learning_engine.update_strategy_scores()
            if scores:
                logger.info(f"Adaptive learning: strategy scores updated {scores}")
        except Exception as e:
            logger.error(f"Error in adaptive learning job: {e}")
    
    async def signal_generation_job(self):
        """Job for generating AI signals"""
        try:
            # Check if market is open before running AI
            if not await self.market_session_manager.is_market_open():
                logger.debug("Market closed - skipping signal generation")
                return
                
            from app.services.ai_signal_engine import ai_signal_engine
            signals_generated = ai_signal_engine.generate_signals()
            if signals_generated > 0:
                logger.info(f"Signal generation job: {signals_generated} signals generated")
        except Exception as e:
            logger.error(f"Error in signal generation job: {e}")
    
    async def paper_trade_monitor_job(self):
        """Job for monitoring paper trades"""
        try:
            # Check if market is open before running AI
            if not await self.market_session_manager.is_market_open():
                logger.debug("Market closed - skipping paper trade monitor")
                return
                
            from app.services.paper_trade_engine import paper_trade_engine
            trades_closed = paper_trade_engine.monitor_open_trades()
            if trades_closed > 0:
                logger.info(f"Paper trade monitor job: {trades_closed} trades closed")
        except Exception as e:
            logger.error(f"Error in paper trade monitor job: {e}")
    
    async def new_prediction_processing_job(self):
        """Job for processing new predictions into paper trades"""
        try:
            # Check if market is open before running AI
            if not await self.market_session_manager.is_market_open():
                logger.debug("Market closed - skipping prediction processing")
                return
                
            from app.services.paper_trade_engine import paper_trade_engine
            trades_created = paper_trade_engine.process_new_predictions()
            if trades_created > 0:
                logger.info(f"New prediction processing job: {trades_created} trades created")
        except Exception as e:
            logger.error(f"Error in new prediction processing job: {e}")
    
    async def outcome_checker_job(self):
        """Job for checking prediction outcomes"""
        try:
            # Check if market is open before running AI
            if not await self.market_session_manager.is_market_open():
                logger.debug("Market closed - skipping outcome checker")
                return
                
            from app.services.ai_outcome_engine import ai_outcome_engine
            outcomes_evaluated = ai_outcome_engine.evaluate_pending_outcomes()
            if outcomes_evaluated > 0:
                logger.info(f"Outcome checker job: {outcomes_evaluated} outcomes evaluated")
        except Exception as e:
            logger.error(f"Error in outcome checker job: {e}")
    
    async def learning_update_job(self):
        """Job for updating AI learning"""
        try:
            # Check if market is open before running AI
            if not await self.market_session_manager.is_market_open():
                logger.debug("Market closed - skipping learning update")
                return
                
            from app.services.ai_learning_engine import ai_learning_engine
            formulas_updated = ai_learning_engine.update_all_formula_learning()
            if formulas_updated > 0:
                logger.info(f"Learning update job: {formulas_updated} formulas updated")
        except Exception as e:
            logger.error(f"Error in learning update job: {e}")
            
    async def ml_training_job(self):
        """Job for training ML model after market close"""
        try:
            logger.info("Starting scheduled ML training job (Daily 16:00 IST)")
            from app.services.ml_training_engine import ml_training_engine
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, ml_training_engine.train)
            if result:
                logger.info("ML model training completed successfully")
            else:
                logger.warning("ML model training did not complete (maybe no data yet)")
        except Exception as e:
            logger.error(f"Error in ML training job: {e}", exc_info=True)
    
    async def market_snapshot_job(self):
        """Job for collecting market snapshots"""
        try:
            # Check if market is open before collecting snapshots
            if not await self.market_session_manager.is_market_open():
                logger.debug("Market closed - skipping market snapshot")
                return
                
            # Collect real market snapshot
            await self.collect_real_market_snapshot()
                    
        except Exception as e:
            logger.error(f"Error in market snapshot job: {e}")
    
    async def collect_real_market_snapshot(self):
        """Collect real market snapshot from market data API"""
        try:
            from app.market_data.market_data_service import get_latest_option_chain
            
            # Get real market data for NIFTY
            market_data = await get_latest_option_chain("NIFTY")
            
            if market_data and 'spot_price' in market_data:
                spot_price = float(market_data.get('spot_price', 0))
                
                # Calculate PCR from option chain
                total_call_oi = 0
                total_put_oi = 0
                
                if 'option_chain' in market_data:
                    for option in market_data['option_chain']:
                        if 'call_oi' in option:
                            total_call_oi += float(option.get('call_oi', 0))
                        if 'put_oi' in option:
                            total_put_oi += float(option.get('put_oi', 0))
                
                pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
                atm_strike = round(spot_price / 50) * 50
                
                from ai.ai_db import ai_db
                
                query = """
                    INSERT INTO market_snapshot 
                    (symbol, spot_price, pcr, total_call_oi, total_put_oi, atm_strike)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                params = ("NIFTY", spot_price, pcr, total_call_oi, total_put_oi, atm_strike)
                ai_db.execute_query(query, params)
                
                logger.info(f"Market snapshot stored: NIFTY @ {spot_price}, PCR: {pcr:.2f}")
            else:
                logger.warning("Market snapshot unavailable")
                return
                
        except Exception as e:
            logger.error(f"Error collecting real market snapshot: {e}")
            return
    
    async def create_sample_market_snapshot(self):
        """Create sample market snapshot for AI analysis"""
        try:
            import random
            
            # Sample market data (in production, fetch from real market)
            spot_price = random.uniform(19500, 20500)
            total_call_oi = random.uniform(1000000, 5000000)
            total_put_oi = random.uniform(800000, 4000000)
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
            atm_strike = round(spot_price / 50) * 50
            
            from ai.ai_db import ai_db
            
            query = """
                INSERT INTO market_snapshot 
                (symbol, spot_price, pcr, total_call_oi, total_put_oi, atm_strike)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = ("NIFTY", spot_price, pcr, total_call_oi, total_put_oi, atm_strike)
            ai_db.execute_query(query, params)
            
            logger.info(f"Sample market snapshot stored: NIFTY @ {spot_price:.2f}, PCR: {pcr:.2f}")
            
        except Exception as e:
            logger.error(f"Error creating sample market snapshot: {e}")
            
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("AI scheduler started successfully")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            
    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("AI scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            
    def get_job_status(self):
        """Get status of all scheduled jobs"""
        try:
            # Start scheduler if not running
            if not self.scheduler.running:
                self.scheduler.start()
                
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': str(job.next_run_time) if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            return jobs
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return []

# Global scheduler instance
ai_scheduler = AIScheduler()
