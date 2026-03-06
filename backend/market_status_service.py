"""
Market Status Service with Full Debug Logging
Handles market status monitoring and broadcasting with trace tracking
"""

import asyncio
import datetime
from typing import Dict, Any, Optional
from core.logger import market_logger, get_trace_id
from websocket_manager import manager

class MarketStatusService:
    def __init__(self):
        self.current_status = None
        self.last_check_time = None
        self.status_change_count = 0
        self.check_count = 0
        self.broadcast_interval = 30  # seconds
        
    async def start_monitoring(self):
        """Start market status monitoring with logging"""
        market_logger.info("MARKET STATUS MONITORING STARTED")
        
        while True:
            try:
                await self._check_and_broadcast_status()
                await asyncio.sleep(self.broadcast_interval)
                
            except Exception as e:
                market_logger.error(f"MARKET STATUS MONITORING ERROR trace={get_trace_id()} error={str(e)}")
                await asyncio.sleep(5)  # retry after 5 seconds
    
    async def _check_and_broadcast_status(self):
        """Check market status and broadcast if changed"""
        try:
            self.check_count += 1
            market_logger.info(f"MARKET STATUS CHECK START trace={get_trace_id()} check_count={self.check_count}")
            
            # Get current market status
            new_status = await self._get_market_status_from_api()
            
            if new_status != self.current_status:
                # Status changed, log and broadcast
                self.current_status = new_status
                self.status_change_count += 1
                self.last_check_time = datetime.datetime.now()
                
                if new_status:
                    market_logger.info(f"MARKET STATUS OPEN trace={get_trace_id()} change_count={self.status_change_count} time={self.last_check_time.isoformat()}")
                else:
                    market_logger.info(f"MARKET STATUS CLOSED trace={get_trace_id()} change_count={self.status_change_count} time={self.last_check_time.isoformat()}")
                
                # Broadcast to all WebSocket clients
                await manager.send_market_status(new_status)
                
            else:
                # No status change
                market_logger.debug(f"MARKET STATUS UNCHANGED trace={get_trace_id()} status={'OPEN' if new_status else 'CLOSED'} check_count={self.check_count}")
                
        except Exception as e:
            market_logger.error(f"MARKET STATUS CHECK ERROR trace={get_trace_id()} error={str(e)}")
    
    async def _get_market_status_from_api(self) -> bool:
        """Get market status from canonical service"""
        try:
            market_logger.debug(f"MARKET STATUS CANONICAL CALL trace={get_trace_id()}")
            
            from app.services.market_status_service import get_market_status
            status = await get_market_status()
            
            market_logger.debug(f"MARKET STATUS CANONICAL RESPONSE trace={get_trace_id()} status={status}")
            
            # Map to bool
            is_open = status == "OPEN"
            market_logger.debug(f"MARKET STATUS PARSED trace={get_trace_id()} is_open={is_open}")
            
            return is_open
                
        except Exception as e:
            market_logger.error(f"MARKET STATUS CANONICAL FAILURE trace={get_trace_id()} error={str(e)}")
            return self.current_status or False
    
    async def force_status_update(self, market_open: bool):
        """Force market status update with logging"""
        try:
            if market_open != self.current_status:
                self.current_status = market_open
                self.status_change_count += 1
                self.last_check_time = datetime.datetime.now()
                
                if market_open:
                    market_logger.info(f"MARKET STATUS FORCE OPEN trace={get_trace_id()} change_count={self.status_change_count}")
                else:
                    market_logger.info(f"MARKET STATUS FORCE CLOSED trace={get_trace_id()} change_count={self.status_change_count}")
                
                # Broadcast to all WebSocket clients
                await manager.send_market_status(market_open)
                
            else:
                market_logger.debug(f"MARKET STATUS FORCE UNCHANGED trace={get_trace_id()} status={'OPEN' if market_open else 'CLOSED'}")
                
        except Exception as e:
            market_logger.error(f"MARKET STATUS FORCE ERROR trace={get_trace_id()} error={str(e)}")
    
    def get_current_status(self) -> Optional[bool]:
        """Get current market status"""
        return self.current_status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get market status service statistics"""
        return {
            "current_status": "OPEN" if self.current_status else "CLOSED" if self.current_status is False else "UNKNOWN",
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "status_change_count": self.status_change_count,
            "check_count": self.check_count,
            "broadcast_interval": self.broadcast_interval
        }

# Global market status service instance
market_status_service: Optional[MarketStatusService] = None

def init_market_status_service():
    """Initialize market status service"""
    global market_status_service
    market_status_service = MarketStatusService()
    market_logger.info("MARKET STATUS SERVICE INITIALIZED")

async def start_market_status_monitoring():
    """Start market status monitoring"""
    if not market_status_service:
        market_logger.error("MARKET STATUS SERVICE NOT INITIALIZED")
        return
    await market_status_service.start_monitoring()

async def force_market_status_update(market_open: bool):
    """Force market status update"""
    if not market_status_service:
        market_logger.error("MARKET STATUS SERVICE NOT INITIALIZED")
        return
    await market_status_service.force_status_update(market_open)

def get_market_status_stats() -> Dict[str, Any]:
    """Get market status statistics"""
    if not market_status_service:
        return {}
    return market_status_service.get_stats()
