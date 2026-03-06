from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

from ...services.ai_interpreter_service import ai_interpreter_service

router = APIRouter(tags=["intelligence"])
logger = logging.getLogger(__name__)

@router.post("/interpret")
async def interpret_intelligence(intelligence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpret market intelligence using AI.
    
    Accepts MarketIntelligence object and returns structured narrative interpretation.
    """
    try:
        logger.info("AI interpretation request received")
        
        # Validate intelligence structure
        if not isinstance(intelligence, dict):
            raise HTTPException(status_code=400, detail="Intelligence must be a dictionary")
        
        # Call AI interpreter service
        interpretation = await ai_interpreter_service.interpret_market(intelligence)
        
        return {
            "status": "success",
            "data": interpretation,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in intelligence interpretation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
