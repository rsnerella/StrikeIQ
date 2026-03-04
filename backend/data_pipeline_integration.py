"""
Complete Data Pipeline Integration with Full Debug Logging
Integrates all services with trace tracking across the entire pipeline
"""

import asyncio
from datetime import datetime
from core.logger import start_trace, get_trace_id, clear_trace, with_trace
from upstox_websocket_client import get_upstox_client
from protobuf_decoder import decode_protobuf_data
from market_aggregator import process_market_data
from websocket_manager import manager
from market_status_service import market_status_service
import os

class DataPipeline:
    def __init__(self):
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        
    @with_trace
    async def start_pipeline(self):
        """Start the complete data pipeline with trace tracking"""
        self.is_running = True
        print("🚀 Starting StrikeIQ Data Pipeline with Full Debug Logging")
        
        # Start market status monitoring
        asyncio.create_task(market_status_service.start_monitoring())
        
        # Check for Upstox token
        access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
        
        if not access_token:
            print("❌ UPSTOX_ACCESS_TOKEN missing — market data disabled")
            return
        
        # Start Upstox WebSocket client
        upstox_client = await get_upstox_client()
        
        if await upstox_client.connect():
            await upstox_client.listen()
        else:
            print("❌ Failed to connect to Upstox WebSocket")
    
    @with_trace
    async def process_upstox_data(self, binary_data: bytes):
        """Process data through complete pipeline with trace tracking"""
        try:
            # Start trace for this data batch
            trace_id = start_trace()
            
            # Step 1: Decode protobuf
            decoded_data = await decode_protobuf_data(binary_data)
            if not decoded_data:
                self.error_count += 1
                return
            
            # Step 2: Aggregate market data
            aggregated_data = await process_market_data(decoded_data)
            if not aggregated_data:
                self.error_count += 1
                return
            
            # Step 3: Broadcast via WebSocket
            await manager.send_market_data(aggregated_data)
            
            # Step 4: Generate and broadcast heatmap
            heatmap_data = market_aggregator.get_heatmap_data()
            if heatmap_data:
                await manager.send_heatmap(heatmap_data)
            
            self.processed_count += 1
            clear_trace()
            
        except Exception as e:
            self.error_count += 1
            print(f"Pipeline error: {e}")
            clear_trace()
    
    def get_stats(self):
        """Get pipeline statistics"""
        return {
            "is_running": self.is_running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (self.processed_count / (self.processed_count + self.error_count) * 100) if (self.processed_count + self.error_count) > 0 else 0
        }

# Global pipeline instance
data_pipeline = DataPipeline()

async def start_data_pipeline():
    """Start the global data pipeline"""
    await data_pipeline.start_pipeline()

def get_pipeline_stats():
    """Get pipeline statistics"""
    return data_pipeline.get_stats()

# Example usage in main FastAPI app
if __name__ == "__main__":
    asyncio.run(start_data_pipeline())
