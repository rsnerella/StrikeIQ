"""
Automated Retraining Job - ML Model Retraining with Versioning
Handles scheduled retraining of ML models based on performance metrics
"""

import asyncio
import logging
import os
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.ai.ml_training_engine import MLTrainingEngine
from app.ai.training_dataset_builder import TrainingDatasetBuilder
from app.ai.learning_engine import LearningEngine

logger = logging.getLogger(__name__)

class AutomatedRetrainingJob:
    """
    Automated Retraining Job
    
    Features:
    - Scheduled model retraining (daily/weekly)
    - Model versioning and artifact management
    - Performance-based retraining triggers
    - Automatic dataset preparation
    - Model evaluation before deployment
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.ml_engine = MLTrainingEngine(db_session)
        self.dataset_builder = TrainingDatasetBuilder(db_session)
        self.learning_engine = LearningEngine(db_session)
        
        # Retraining parameters
        self.retraining_interval = timedelta(days=1)  # Default daily
        self.min_samples_for_retraining = 100
        self.accuracy_threshold = 0.5
        self.max_model_versions = 5  # Keep last 5 model versions
        
        # Model versioning
        self.model_versions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("AutomatedRetrainingJob initialized")
    
    async def run_scheduled_retraining(self) -> Dict[str, Any]:
        """Run scheduled retraining job"""
        try:
            logger.info("Starting scheduled retraining job")
            
            # Check if retraining should be triggered
            should_retrain, reason = await self._should_trigger_retraining()
            
            if not should_retrain:
                return {
                    'status': 'skipped',
                    'reason': reason,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Step 1: Prepare training dataset
            dataset_result = await self._prepare_training_dataset()
            
            if not dataset_result['success']:
                return {
                    'status': 'failed',
                    'error': dataset_result.get('error', 'Unknown error'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Step 2: Train new model
            training_result = await self._train_new_model(dataset_result['dataset'])
            
            if not training_result['success']:
                return {
                    'status': 'failed',
                    'error': training_result.get('error', 'Unknown error'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Step 3: Evaluate new model
            evaluation_result = await self._evaluate_new_model(training_result['model_path'])
            
            # Step 4: Deploy if evaluation passes
            if evaluation_result['deploy']:
                deployment_result = await self._deploy_model(training_result['model_path'], evaluation_result)
            else:
                deployment_result = {'status': 'rejected', 'reason': evaluation_result.get('reason', 'Evaluation failed')}
            
            # Step 5: Update model registry
            await self._update_model_registry(training_result, evaluation_result, deployment_result)
            
            result = {
                'status': 'completed',
                'dataset_info': dataset_result,
                'training_metrics': training_result['training_metrics'],
                'evaluation_result': evaluation_result,
                'deployment_result': deployment_result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Automated retraining completed: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in automated retraining: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _should_trigger_retraining(self) -> Tuple[bool, str]:
        """Check if retraining should be triggered"""
        try:
            # Check learning engine recommendation
            should_retrain, reason = await self.learning_engine.should_trigger_retraining()
            
            if should_retrain:
                return True, f"Learning engine recommendation: {reason}"
            
            # Check time-based schedule
            last_retraining = self._get_last_retraining_time()
            if last_retraining and (datetime.now() - last_retraining) >= self.retraining_interval:
                return True, f"Scheduled retraining (last: {last_retraining.isoformat()})"
            
            # Check performance threshold
            ml_performance = self.learning_engine.ml_model_performance
            if ml_performance.get('accuracy', 1.0) < self.accuracy_threshold:
                return True, f"Low accuracy: {ml_performance['accuracy']:.2%} below threshold"
            
            return False, "No retraining trigger conditions met"
            
        except Exception as e:
            logger.error(f"Error checking retraining trigger: {e}")
            return False, f"Error checking trigger: {e}"
    
    def _get_last_retraining_time(self) -> Optional[datetime]:
        """Get timestamp of last retraining"""
        try:
            # This would typically come from a database table or file
            # For now, return None (no previous retraining)
            return None
        except Exception as e:
            logger.error(f"Error getting last retraining time: {e}")
            return None
    
    async def _prepare_training_dataset(self) -> Dict[str, Any]:
        """Prepare training dataset for retraining"""
        try:
            logger.info("Preparing training dataset for retraining")
            
            # Build dataset with extended date range for better training
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)  # Use 30 days for retraining
            
            dataset = await self.dataset_builder.build_training_dataset(
                start_date=start_date,
                end_date=end_date,
                min_samples=self.min_samples_for_retraining
            )
            
            if dataset.empty:
                return {
                    'success': False,
                    'error': 'Insufficient training data',
                    'dataset_info': {'samples': 0}
                }
            
            # Save dataset to file for backup
            dataset_path = 'retraining_dataset.csv'
            saved = await self.dataset_builder.save_dataset(dataset, dataset_path)
            
            # Get dataset statistics
            stats = await self.dataset_builder.get_dataset_statistics(dataset)
            
            return {
                'success': True,
                'dataset_path': dataset_path,
                'dataset': dataset,
                'dataset_info': stats
            }
            
        except Exception as e:
            logger.error(f"Error preparing training dataset: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _train_new_model(self, dataset) -> Dict[str, Any]:
        """Train new model with enhanced parameters"""
        try:
            logger.info(f"Training new model with {len(dataset)} samples")
            
            # Train model with enhanced parameters
            training_result = await self.ml_engine.train_model(
                dataset=dataset,
                min_samples=self.min_samples_for_retraining,
                save_model=True
            )
            
            return training_result
            
        except Exception as e:
            logger.error(f"Error training new model: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _evaluate_new_model(self, model_path: str) -> Dict[str, Any]:
        """Evaluate newly trained model before deployment"""
        try:
            logger.info(f"Evaluating new model: {model_path}")
            
            # Load model and get metrics
            model_data = await self.ml_engine.load_model(model_path)
            
            if not model_data:
                return {
                    'deploy': False,
                    'reason': 'Failed to load trained model',
                    'model_path': model_path
                }
            
            metrics = model_data.get('metrics', {})
            
            # Check if model meets deployment criteria
            deploy = True
            reasons = []
            
            # Accuracy threshold
            if metrics.get('accuracy', 0) < 0.5:
                deploy = False
                reasons.append(f"Low accuracy: {metrics.get('accuracy', 0):.2%}")
            
            # Minimum samples
            if metrics.get('training_samples', 0) < self.min_samples_for_retraining:
                deploy = False
                reasons.append(f"Insufficient training samples: {metrics.get('training_samples', 0)}")
            
            # ROC-AUC threshold
            if metrics.get('roc_auc', 0) < 0.6:
                deploy = False
                reasons.append(f"Low ROC-AUC: {metrics.get('roc_auc', 0):.3f}")
            
            result = {
                'deploy': deploy,
                'reason': '; '.join(reasons) if reasons else 'Model meets deployment criteria',
                'metrics': metrics
            }
            
            logger.info(f"Model evaluation: deploy={deploy}, reason={result['reason']}")
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating new model: {e}")
            return {
                'deploy': False,
                'reason': f"Evaluation error: {e}",
                'model_path': model_path
            }
    
    async def _deploy_model(self, model_path: str, evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy new model to production"""
        try:
            if not evaluation_result.get('deploy', False):
                return {
                    'status': 'rejected',
                    'reason': evaluation_result.get('reason', 'Model evaluation failed')
                }
            
            # Create versioned model path
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            versioned_path = f"models/strikeiq_model_v{timestamp}.pkl"
            
            # Copy model to versioned location
            import shutil
            shutil.copy2(model_path, versioned_path)
            
            # Update latest model link
            latest_path = "models/strikeiq_model.pkl"
            if os.path.exists(latest_path):
                os.remove(latest_path)
            os.symlink(os.path.basename(versioned_path), latest_path)
            
            logger.info(f"Model deployed: {versioned_path}")
            
            return {
                'status': 'deployed',
                'versioned_path': versioned_path,
                'latest_path': latest_path
            }
            
        except Exception as e:
            logger.error(f"Error deploying model: {e}")
            return {
                'status': 'failed',
                'reason': f"Deployment error: {e}"
            }
    
    async def _update_model_registry(self, training_result: Dict[str, Any], evaluation_result: Dict[str, Any], deployment_result: Dict[str, Any]) -> None:
        """Update model registry with new version information"""
        try:
            # Create model version record
            model_version = {
                'version': training_result['training_metrics'].get('model_version', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'training_metrics': training_result['training_metrics'],
                'evaluation_metrics': evaluation_result['metrics'],
                'deployment_path': deployment_result.get('versioned_path'),
                'dataset_info': training_result['dataset_info'],
                'status': deployment_result['status']
            }
            
            # Add to registry
            version_key = model_version['version']
            self.model_versions[version_key] = model_version
            
            # Clean up old versions (keep only the most recent)
            if len(self.model_versions) > self.max_model_versions:
                # Sort by timestamp and keep only the most recent
                sorted_versions = sorted(
                    self.model_versions.items(),
                    key=lambda x: x[1]['timestamp'],
                    reverse=True
                )
                
                # Remove excess versions
                for version_key, version_data in sorted_versions[self.max_model_versions:]:
                    del self.model_versions[version_key]
                    logger.info(f"Removed old model version: {version_key}")
            
            logger.info(f"Model registry updated: {len(self.model_versions)} versions")
            
        except Exception as e:
            logger.error(f"Error updating model registry: {e}")
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get current model and retraining status"""
        try:
            # Get latest model info
            latest_model = await self.ml_engine.load_model()
            
            # Get retraining status
            should_retrain, retrain_reason = await self._should_trigger_retraining()
            
            # Get learning engine status
            learning_summary = self.learning_engine.get_learning_summary()
            
            return {
                'latest_model': {
                    'loaded': latest_model is not None,
                    'version': latest_model.get('model_version', 'unknown') if latest_model else None,
                    'trained_at': latest_model.get('trained_at') if latest_model else None
                },
                'model_versions': {
                    'total': len(self.model_versions),
                    'latest': list(self.model_versions.keys())[-1] if self.model_versions else None,
                    'all_versions': list(self.model_versions.keys())
                },
                'retraining_status': {
                    'should_retrain': should_retrain,
                    'reason': retrain_reason,
                    'last_check': datetime.now(timezone.utc).isoformat()
                },
                'learning_engine': learning_summary,
                'retraining_interval': self.retraining_interval.total_seconds(),
                'min_samples_threshold': self.min_samples_for_retraining,
                'accuracy_threshold': self.accuracy_threshold
            }
            
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_models(self, keep_versions: int = 3) -> int:
        """Clean up old model versions, keeping only the most recent"""
        try:
            model_dir = "models"
            if not os.path.exists(model_dir):
                return 0
            
            # Get all model files
            model_files = [f for f in os.listdir(model_dir) if f.startswith('strikeiq_model_v') and f.endswith('.pkl')]
            
            # Sort by modification time (newest first)
            model_files.sort(key=lambda x: os.path.getmtime(os.path.join(model_dir, x)), reverse=True)
            
            # Keep only the specified number of most recent versions
            files_to_keep = model_files[:keep_versions]
            files_to_remove = model_files[keep_versions:]
            
            # Remove old files
            removed_count = 0
            for file in files_to_remove:
                file_path = os.path.join(model_dir, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(f"Removed old model: {file}")
            
            logger.info(f"Cleaned up {removed_count} old model files, kept {len(files_to_keep)} most recent")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old models: {e}")
            return 0
    
    async def schedule_retraining(self) -> None:
        """Schedule the next retraining job"""
        try:
            # Calculate next retraining time
            next_run = datetime.now(timezone.utc) + self.retraining_interval
            
            logger.info(f"Scheduled next retraining for: {next_run.isoformat()}")
            
            # In production, this would integrate with a job scheduler like Celery or APScheduler
            # For now, just log the schedule
            
        except Exception as e:
            logger.error(f"Error scheduling retraining: {e}")

# Global instance
automated_retraining_job = None

async def get_automated_retraining_job(db_session: Session) -> AutomatedRetrainingJob:
    """Get or create automated retraining job instance"""
    global automated_retraining_job
    
    if automated_retraining_job is None:
        automated_retraining_job = AutomatedRetrainingJob(db_session)
    
    return automated_retraining_job
