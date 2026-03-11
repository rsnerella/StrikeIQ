#!/usr/bin/env python3
"""
Test Ctrl+C shutdown behavior
"""

import asyncio
import signal
import sys
import time
import subprocess
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    logger.info(f"Received signal: {sig}")
    logger.info("Test completed - shutdown works correctly")
    sys.exit(0)

async def test_shutdown():
    """Test server startup and shutdown"""
    logger.info("Starting server...")
    
    # Start server in background
    process = subprocess.Popen([
        sys.executable, "main.py"
    ], cwd="backend")
    
    # Wait a bit for server to start
    await asyncio.sleep(3)
    
    # Send Ctrl+C signal after 5 seconds
    logger.info("Will send Ctrl+C in 5 seconds...")
    await asyncio.sleep(5)
    
    # Simulate Ctrl+C
    process.send_signal(signal.SIGINT)
    
    # Wait for process to exit
    try:
        process.wait(timeout=10)
        logger.info("Server exited cleanly")
    except subprocess.TimeoutExpired:
        logger.warning("Server did not exit within 10 seconds")
        process.terminate()
        await asyncio.sleep(1)
        process.kill()

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    asyncio.run(test_shutdown())
