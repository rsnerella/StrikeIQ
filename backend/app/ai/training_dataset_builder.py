"""
Training Dataset Builder - ML Dataset Creation
Builds training datasets from features, signals, and outcomes
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import json

from app.models.ai_features import AIFeature
from app.models.ai_signal_log import AiSignalLog
from app.models.signal_outcome import SignalOutcome

logger = logging.getLogger(__name__)

class TrainingDatasetBuilder:
    """
    Training Dataset Builder
    
    Purpose:
    - Join signals with market features
    - Label outcomes as WIN or LOSS
    - Convert categorical features to numeric
    - Normalize numeric columns
    - Export dataset as pandas dataframe
    
    Input Tables:
    - ai_features
    - ai_signal_logs  
    - signal_outcomes
    
    Output:
    - training_dataset.csv
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # Feature columns for ML
        self.feature_columns = [
            'pcr',
            'gamma_exposure', 
            'oi_velocity',
            'volatility',
            'trend_strength',
            'liquidity_score',
            'market_regime'
        ]
        
        # Target variable
        self.target_column = 'trade_success'
        
        logger.info("TrainingDatasetBuilder initialized")
    
    async def build_training_dataset(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_samples: int = 100
    ) -> pd.DataFrame:
        """
        Build complete training dataset
        
        Args:
            start_date: Start date for data collection
            end_date: End date for data collection
            min_samples: Minimum samples required
            
        Returns:
            Training dataset as pandas DataFrame
        """
        try:
            logger.info("Building training dataset...")
            
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                start_date = end_date - timedelta(days=30)  # Default to last 30 days
            
            # Step 1: Join signals with features
            joined_data = await self._join_signals_with_features(start_date, end_date)
            
            if len(joined_data) < min_samples:
                logger.warning(f"Insufficient data: {len(joined_data)} samples < {min_samples} minimum")
                return pd.DataFrame()
            
            # Step 2: Label outcomes
            labeled_data = await self._label_outcomes(joined_data)
            
            # Step 3: Convert categorical to numeric
            numeric_data = await self._convert_categorical_to_numeric(labeled_data)
            
            # Step 4: Normalize numeric columns
            normalized_data = await self._normalize_features(numeric_data)
            
            # Step 5: Create final dataset
            training_data = await self._create_final_dataset(normalized_data)
            
            logger.info(f"Built training dataset: {len(training_data)} samples, {len(training_data.columns)} features")
            return training_data
            
        except Exception as e:
            logger.error(f"Error building training dataset: {e}")
            return pd.DataFrame()
    
    async def _join_signals_with_features(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Join AI signals with market features"""
        try:
            # Query AI signals in date range
            signals_query = self.db_session.query(AiSignalLog).filter(
                and_(
                    AiSignalLog.timestamp >= start_date,
                    AiSignalLog.timestamp <= end_date
                )
            ).order_by(AiSignalLog.timestamp)
            
            signals = signals_query.all()
            logger.info(f"Found {len(signals)} signals in date range")
            
            joined_data = []
            
            for signal in signals:
                # Find closest feature record within 5 minutes
                feature_time_min = signal.timestamp - timedelta(minutes=5)
                feature_time_max = signal.timestamp + timedelta(minutes=5)
                
                feature_query = self.db_session.query(AIFeature).filter(
                    and_(
                        AIFeature.symbol == signal.symbol,
                        AIFeature.timestamp >= feature_time_min,
                        AIFeature.timestamp <= feature_time_max
                    )
                ).order_by(AIFeature.timestamp).first()
                
                if feature_query:
                    # Join signal with feature
                    joined_record = {
                        'signal_id': signal.id,
                        'symbol': signal.symbol,
                        'timestamp': signal.timestamp,
                        'signal_type': signal.signal_type,
                        'signal_strength': signal.signal_strength,
                        'strategy': signal.strategy,
                        
                        # Feature columns
                        'pcr': feature_query.pcr,
                        'gamma_exposure': feature_query.gamma_exposure,
                        'oi_velocity': feature_query.oi_velocity,
                        'volatility': feature_query.volatility,
                        'trend_strength': feature_query.trend_strength,
                        'liquidity_score': feature_query.liquidity_score,
                        'market_regime': feature_query.market_regime,
                        
                        # Full feature vector
                        'feature_vector': feature_query.feature_vector_json
                    }
                    
                    joined_data.append(joined_record)
            
            logger.info(f"Joined {len(joined_data)} signals with features")
            return joined_data
            
        except Exception as e:
            logger.error(f"Error joining signals with features: {e}")
            return []
    
    async def _label_outcomes(self, joined_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Label outcomes as WIN or LOSS"""
        try:
            labeled_data = []
            
            for record in joined_data:
                # Find outcome for this signal
                outcome_query = self.db_session.query(SignalOutcome).filter(
                    SignalOutcome.signal_id == record['signal_id']
                ).first()
                
                if outcome_query:
                    # Determine outcome label
                    if outcome_query.profit_loss > 0:
                        outcome_label = 'WIN'
                        outcome_numeric = 1
                    else:
                        outcome_label = 'LOSS'
                        outcome_numeric = 0
                    
                    # Add outcome to record
                    record['outcome_label'] = outcome_label
                    record['outcome_numeric'] = outcome_numeric
                    record['profit_loss'] = outcome_query.profit_loss
                    record['return_pct'] = outcome_query.return_pct
                    
                    labeled_data.append(record)
                else:
                    # No outcome found, skip this record
                    continue
            
            logger.info(f"Labeled {len(labeled_data)} records with outcomes")
            return labeled_data
            
        except Exception as e:
            logger.error(f"Error labeling outcomes: {e}")
            return []
    
    async def _convert_categorical_to_numeric(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert categorical features to numeric"""
        try:
            # Extract categorical columns
            categorical_columns = ['signal_type', 'strategy', 'market_regime']
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Convert categorical to numeric
            for col in categorical_columns:
                if col in df.columns:
                    df[col] = df[col].fillna('unknown')
                    df[col + '_encoded'] = self.label_encoder.fit_transform(df[col])
            
            # Convert back to list of dicts
            numeric_data = df.to_dict('records')
            
            logger.info(f"Converted categorical features to numeric for {len(numeric_data)} records")
            return numeric_data
            
        except Exception as e:
            logger.error(f"Error converting categorical to numeric: {e}")
            return []
    
    async def _normalize_features(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize numeric feature columns"""
        try:
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Filter to numeric feature columns that exist
            numeric_features = [col for col in self.feature_columns if col in df.columns]
            
            if numeric_features:
                # Fill missing values with median
                for col in numeric_features:
                    df[col] = df[col].fillna(df[col].median())
                
                # Normalize features
                df[numeric_features] = self.scaler.fit_transform(df[numeric_features])
            
            # Convert back to list of dicts
            normalized_data = df.to_dict('records')
            
            logger.info(f"Normalized {len(numeric_features)} features for {len(normalized_data)} records")
            return normalized_data
            
        except Exception as e:
            logger.error(f"Error normalizing features: {e}")
            return []
    
    async def _create_final_dataset(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create final training dataset"""
        try:
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Select final feature columns
            feature_cols = []
            
            # Add numeric feature columns
            for col in self.feature_columns:
                if col in df.columns:
                    feature_cols.append(col)
            
            # Add encoded categorical columns
            categorical_cols = ['signal_type', 'strategy', 'market_regime']
            for col in categorical_cols:
                encoded_col = col + '_encoded'
                if encoded_col in df.columns:
                    feature_cols.append(encoded_col)
            
            # Add signal strength
            if 'signal_strength' in df.columns:
                feature_cols.append('signal_strength')
            
            # Create final dataset
            final_df = df[feature_cols + ['outcome_numeric']].copy()
            final_df.columns = feature_cols + [self.target_column]
            
            # Remove any rows with missing target
            final_df = final_df.dropna(subset=[self.target_column])
            
            logger.info(f"Created final dataset: {len(final_df)} samples, {len(feature_cols)} features")
            return final_df
            
        except Exception as e:
            logger.error(f"Error creating final dataset: {e}")
            return pd.DataFrame()
    
    async def save_dataset(self, dataset: pd.DataFrame, filepath: str = 'training_dataset.csv') -> bool:
        """Save dataset to CSV file"""
        try:
            if dataset.empty:
                logger.warning("Dataset is empty, nothing to save")
                return False
            
            dataset.to_csv(filepath, index=False)
            logger.info(f"Saved dataset to {filepath}: {len(dataset)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error saving dataset: {e}")
            return False
    
    async def get_dataset_statistics(self, dataset: pd.DataFrame) -> Dict[str, Any]:
        """Get dataset statistics"""
        try:
            if dataset.empty:
                return {}
            
            stats = {
                'total_samples': len(dataset),
                'feature_count': len(dataset.columns) - 1,  # Exclude target
                'win_rate': dataset[self.target_column].mean(),
                'features': list(dataset.columns[:-1]),  # Exclude target
                'target_distribution': dataset[self.target_column].value_counts().to_dict(),
                'missing_values': dataset.isnull().sum().sum(),
                'data_types': dataset.dtypes.to_dict()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting dataset statistics: {e}")
            return {}
    
    async def split_dataset(
        self, 
        dataset: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Split dataset into train and test sets"""
        try:
            if dataset.empty:
                return pd.DataFrame(), pd.DataFrame()
            
            # Split features and target
            X = dataset.drop(columns=[self.target_column])
            y = dataset[self.target_column]
            
            # Split dataset
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
            
            # Recombine with target
            train_df = pd.concat([X_train, y_train], axis=1)
            test_df = pd.concat([X_test, y_test], axis=1)
            
            logger.info(f"Split dataset: {len(train_df)} train, {len(test_df)} test samples")
            return train_df, test_df
            
        except Exception as e:
            logger.error(f"Error splitting dataset: {e}")
            return pd.DataFrame(), pd.DataFrame()
