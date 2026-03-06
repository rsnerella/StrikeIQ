from fastapi import APIRouter
from typing import Dict, Any
import logging
from datetime import datetime

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "service": "StrikeIQ API"
    }
