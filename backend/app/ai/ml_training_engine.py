import os
import pickle
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.database import engine
from app.ai.training_dataset_builder import TrainingDatasetBuilder

logger = logging.getLogger(__name__)

class MLTrainingEngine:
    """
    Enhanced ML Training Engine
    
    Features:
    - Uses TrainingDatasetBuilder for data preparation
    - XGBoost model with hyperparameter tuning
    - Cross-validation and performance metrics
    - Model versioning and artifact management
    - Comprehensive evaluation metrics
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.model_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "strikeiq_model.pkl")
        
        # Training parameters
        self.test_size = 0.2
        self.random_state = 42
        self.cv_folds = 5
        
        # Model hyperparameters
        self.xgb_params = {
            'n_estimators': 100,
            'max_depth': 3,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': self.random_state
        }
        
        logger.info("MLTrainingEngine initialized")

    async def train_model(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_samples: int = 100,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        Train ML model with enhanced pipeline
        
        Args:
            start_date: Start date for training data
            end_date: End date for training data
            min_samples: Minimum samples required for training
            save_model: Whether to save the trained model
            
        Returns:
            Training results and metrics
        """
        try:
            logger.info("Starting enhanced ML Training")
            
            # Create dataset builder
            dataset_builder = TrainingDatasetBuilder(self.db_session)
            
            # Build training dataset
            dataset = await dataset_builder.build_training_dataset(
                start_date=start_date,
                end_date=end_date,
                min_samples=min_samples
            )
            
            if dataset.empty:
                logger.warning("No training data available")
                return {'success': False, 'error': 'No training data available'}
            
            # Split dataset
            train_df, test_df = await dataset_builder.split_dataset(
                dataset, 
                test_size=self.test_size,
                random_state=self.random_state
            )
            
            if train_df.empty or test_df.empty:
                logger.warning("Insufficient data for train/test split")
                return {'success': False, 'error': 'Insufficient data for train/test split'}
            
            # Prepare features and target
            X_train = train_df.drop(columns=['trade_success'])
            y_train = train_df['trade_success']
            X_test = test_df.drop(columns=['trade_success'])
            y_test = test_df['trade_success']
            
            # Train model
            model, training_metrics = await self._train_xgboost_model(X_train, y_train, X_test, y_test)
            
            if model is None:
                return {'success': False, 'error': 'Model training failed'}
            
            # Save model if requested
            model_path = None
            if save_model:
                model_path = await self._save_model(model, X_train.columns.tolist(), training_metrics)
            
            # Log training to database
            await self._log_training_to_db(training_metrics)
            
            # Prepare results
            results = {
                'success': True,
                'model_path': model_path,
                'training_metrics': training_metrics,
                'dataset_info': {
                    'total_samples': len(dataset),
                    'train_samples': len(train_df),
                    'test_samples': len(test_df),
                    'feature_count': len(X_train.columns),
                    'win_rate': dataset['trade_success'].mean()
                }
            }
            
            logger.info(f"ML Training completed: accuracy={training_metrics['accuracy']:.4f}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to train ML model: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def _train_xgboost_model(
        self, 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        """Train XGBoost model with evaluation"""
        try:
            # Import XGBoost
            import xgboost as xgb
            from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, classification_report
            from sklearn.model_selection import cross_val_score
            
            # Create model
            model = xgb.XGBClassifier(**self.xgb_params)
            
            # Train model
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='binary')
            recall = recall_score(y_test, y_pred, average='binary')
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=self.cv_folds, scoring='accuracy')
            cv_mean = cv_scores.mean()
            cv_std = cv_scores.std()
            
            # Feature importance
            feature_importance = dict(zip(X_train.columns, model.feature_importances_))
            
            # Training metrics
            training_metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'roc_auc': roc_auc,
                'cv_mean': cv_mean,
                'cv_std': cv_std,
                'feature_importance': feature_importance,
                'model_type': 'XGBoost',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'feature_count': len(X_train.columns)
            }
            
            logger.info(f"Model trained - Accuracy: {accuracy:.4f}, ROC-AUC: {roc_auc:.4f}")
            return model, training_metrics
            
        except ImportError:
            logger.warning("XGBoost not installed, falling back to RandomForest")
            return await self._train_random_forest_model(X_train, y_train, X_test, y_test)
        except Exception as e:
            logger.error(f"Error training XGBoost model: {e}")
            return None, {}
    
    async def _train_random_forest_model(
        self, 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        """Fallback RandomForest model"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
            from sklearn.model_selection import cross_val_score
            
            # Create model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=3,
                random_state=self.random_state
            )
            
            # Train model
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='binary')
            recall = recall_score(y_test, y_pred, average='binary')
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=self.cv_folds, scoring='accuracy')
            cv_mean = cv_scores.mean()
            cv_std = cv_scores.std()
            
            # Feature importance
            feature_importance = dict(zip(X_train.columns, model.feature_importances_))
            
            # Training metrics
            training_metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'roc_auc': roc_auc,
                'cv_mean': cv_mean,
                'cv_std': cv_std,
                'feature_importance': feature_importance,
                'model_type': 'RandomForest',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'feature_count': len(X_train.columns)
            }
            
            logger.info(f"RandomForest trained - Accuracy: {accuracy:.4f}, ROC-AUC: {roc_auc:.4f}")
            return model, training_metrics
            
        except Exception as e:
            logger.error(f"Error training RandomForest model: {e}")
            return None, {}
    
    async def _save_model(
        self, 
        model: Any, 
        feature_columns: List[str], 
        metrics: Dict[str, Any]
    ) -> Optional[str]:
        """Save trained model with metadata"""
        try:
            # Create versioned model path
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            versioned_path = os.path.join(self.model_dir, f"strikeiq_model_v{timestamp}.pkl")
            
            # Save model artifact
            model_data = {
                'model': model,
                'feature_columns': feature_columns,
                'metrics': metrics,
                'trained_at': datetime.now(timezone.utc).isoformat(),
                'model_version': f"v{timestamp}"
            }
            
            with open(versioned_path, "wb") as f:
                pickle.dump(model_data, f)
            
            # Also save as latest model
            with open(self.model_path, "wb") as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {versioned_path}")
            return versioned_path
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return None
    
    async def _log_training_to_db(self, metrics: Dict[str, Any]) -> None:
        """Log training metrics to database"""
        try:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO ai_models 
                        (model_name, version, accuracy, precision, recall, roc_auc, trained_on, dataset_size, feature_count, model_type) 
                        VALUES (:name, :version, :acc, :prec, :rec, :roc_auc, :time, :size, :features, :model_type)
                    """),
                    {
                        "name": "StrikeIQ_ML_Model",
                        "version": metrics.get('model_version', 'v1.0'),
                        "acc": metrics.get('accuracy', 0),
                        "prec": metrics.get('precision', 0),
                        "rec": metrics.get('recall', 0),
                        "roc_auc": metrics.get('roc_auc', 0),
                        "time": datetime.now(),
                        "size": metrics.get('training_samples', 0),
                        "features": metrics.get('feature_count', 0),
                        "model_type": metrics.get('model_type', 'XGBoost')
                    }
                )
                conn.commit()
                
            logger.info("Training metrics logged to database")
            
        except Exception as e:
            logger.error(f"Error logging training to database: {e}")
    
    async def load_model(self, model_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load trained model from file"""
        try:
            path = model_path or self.model_path
            
            if not os.path.exists(path):
                logger.warning(f"Model file not found: {path}")
                return None
            
            with open(path, "rb") as f:
                model_data = pickle.load(f)
            
            logger.info(f"Model loaded from {path}")
            return model_data
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    async def predict(
        self, 
        features: pd.DataFrame, 
        model_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Make predictions using trained model"""
        try:
            # Load model
            model_data = await self.load_model(model_path)
            if not model_data:
                return None
            
            model = model_data['model']
            feature_columns = model_data['feature_columns']
            
            # Ensure features have correct columns
            if not all(col in features.columns for col in feature_columns):
                missing_cols = [col for col in feature_columns if col not in features.columns]
                logger.error(f"Missing feature columns: {missing_cols}")
                return None
            
            # Select and order features
            X = features[feature_columns]
            
            # Make predictions
            predictions = model.predict(X)
            probabilities = model.predict_proba(X)
            
            # Prepare results
            results = {
                'predictions': predictions.tolist(),
                'probabilities': probabilities.tolist(),
                'buy_probability': probabilities[:, 1].mean(),  # Assuming class 1 is BUY
                'sell_probability': probabilities[:, 0].mean(),  # Assuming class 0 is SELL
                'confidence_score': np.max(probabilities, axis=1).mean(),
                'model_version': model_data.get('model_version'),
                'feature_importance': model_data.get('metrics', {}).get('feature_importance', {})
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return None

# Global instance
ml_training_engine = MLTrainingEngine()
