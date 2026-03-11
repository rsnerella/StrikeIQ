import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .prediction_service import prediction_service
from .experience_updater import experience_updater
from app.services.upstox_auth_service import get_upstox_auth_service

logger = logging.getLogger(__name__)

class OutcomeChecker:
    def __init__(self):
        self.prediction_service = prediction_service
        self.experience_updater = experience_updater
        self.auth_service = get_upstox_auth_service()
        self._client = httpx.AsyncClient(timeout=10)
        
    async def get_current_nifty_price(self) -> Optional[float]:
        """Get current NIFTY price from Upstox API using centralized auth"""
        try:
            url = "https://api.upstox.com/v2/market-quote/ltp"
            
            token_data = await self.auth_service.get_valid_access_token()
            headers = {
                'accept': 'application/json',
                'Authorization': f"Bearer {token_data['access_token']}"
            }
            params = {
                'instrument_key': 'NSE_INDEX|Nifty 50'
            }
            
            response = await self._client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'NSE_INDEX|Nifty 50' in data['data']:
                    price = float(data['data']['NSE_INDEX|Nifty 50']['last_price'])
                    logger.info(f"Current NIFTY price: {price}")
                    return price
                    
            logger.error(f"Failed to get NIFTY price: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting NIFTY price: {e}")
            return None
            
    def calculate_outcome(self, initial_spot: float, current_spot: float) -> str:
        """
        Calculate prediction outcome based on price movement
        
        Args:
            initial_spot: NIFTY spot when prediction was made
            current_spot: Current NIFTY spot
            
        Returns:
            WIN, LOSS, or NEUTRAL
        """
        if not initial_spot or not current_spot:
            return 'NEUTRAL'
            
        price_change = ((current_spot - initial_spot) / initial_spot) * 100
        
        if price_change > 0.3:
            return 'WIN'
        elif price_change < -0.3:
            return 'LOSS'
        else:
            return 'NEUTRAL'
            
    async def check_outcomes(self):
        """Check outcomes for all pending predictions (Async)"""
        try:
            logger.info("Starting outcome check cycle")
            
            pending_predictions = await self.prediction_service.get_pending_predictions()
            
            if not pending_predictions:
                return
                
            current_price = await self.get_current_nifty_price()
            
            if not current_price:
                return
                
            for prediction in pending_predictions:
                try:
                    outcome = self.calculate_outcome(
                        prediction['nifty_spot'],
                        current_price
                    )
                    
                    success = await self.prediction_service.mark_prediction_checked(
                        prediction['id'],
                        outcome
                    )
                    
                    if success:
                        self.experience_updater.update_experience(
                            prediction['formula_id'],
                            outcome
                        )
                except Exception as e:
                    logger.error(f"Error processing prediction {prediction['id']}: {e}")
                    
            logger.info(f"Outcome check cycle completed. Processed {len(pending_predictions)} predictions")
            
        except Exception as e:
            logger.error(f"Error in outcome check cycle: {e}")

# Global outcome checker instance
outcome_checker = OutcomeChecker()
