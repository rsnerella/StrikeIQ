"""
STRIKEIQ STRESS SIMULATION TEST HARNESS
STEP 9: Comprehensive performance testing under load

Simulates high-frequency market data conditions to detect:
- Queue growth under load
- Processing latency spikes  
- Tick drops during stress
- CPU usage patterns
- Memory consumption
- WebSocket stability
"""

import asyncio
import time
import logging
import random
import psutil
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import StrikeIQ components
from app.services.websocket_market_feed import WebSocketMarketFeed
from app.services.message_router import message_router
from app.services.option_chain_builder import option_chain_builder
from app.core.ws_manager import manager

logger = logging.getLogger(__name__)

@dataclass
class StressTestMetrics:
    """Metrics collected during stress testing"""
    test_duration: float
    total_ticks_generated: int
    total_ticks_processed: int
    tick_drop_rate: float
    max_queue_size: int
    avg_queue_size: float
    max_latency: float
    avg_latency: float
    cpu_usage_peak: float
    cpu_usage_avg: float
    memory_usage_peak: float
    memory_usage_avg: float
    errors_count: int
    warnings_count: int

class TickSimulator:
    """Simulates high-frequency market data ticks"""
    
    def __init__(self):
        self.instruments = [
            "NSE_INDEX|Nifty 50",
            "NSE_INDEX|Nifty Bank",
            "NSE_FO|NIFTY-2025-03-27-19000-CE",
            "NSE_FO|NIFTY-2025-03-27-19000-PE",
            "NSE_FO|NIFTY-2025-03-27-19100-CE",
            "NSE_FO|NIFTY-2025-03-27-19100-PE",
            "NSE_FO|NIFTY-2025-03-27-19200-CE",
            "NSE_FO|NIFTY-2025-03-27-19200-PE",
            "NSE_FO|BANKNIFTY-2025-03-27-46000-CE",
            "NSE_FO|BANKNIFTY-2025-03-27-46000-PE",
        ]
        self.base_prices = {
            "NSE_INDEX|Nifty 50": 19000.0,
            "NSE_INDEX|Nifty Bank": 46000.0,
        }
        for i in range(19000, 19300, 100):
            self.base_prices[f"NSE_FO|NIFTY-2025-03-27-{i}-CE"] = random.uniform(50, 500)
            self.base_prices[f"NSE_FO|NIFTY-2025-03-27-{i}-PE"] = random.uniform(50, 500)
        for i in range(46000, 46200, 100):
            self.base_prices[f"NSE_FO|BANKNIFTY-2025-03-27-{i}-CE"] = random.uniform(50, 500)
            self.base_prices[f"NSE_FO|BANKNIFTY-2025-03-27-{i}-PE"] = random.uniform(50, 500)
    
    def generate_tick(self, instrument_key: str) -> Dict[str, Any]:
        """Generate a realistic market data tick"""
        base_price = self.base_prices.get(instrument_key, 100.0)
        
        # Add realistic price movement
        price_change = random.uniform(-0.5, 0.5) * base_price / 100
        new_price = max(0.01, base_price + price_change)
        self.base_prices[instrument_key] = new_price
        
        tick = {
            "instrument_key": instrument_key,
            "ltp": round(new_price, 2),
            "volume": random.randint(100, 10000),
            "timestamp": int(time.time() * 1000),
            "bid": round(new_price - random.uniform(0.1, 1.0), 2),
            "ask": round(new_price + random.uniform(0.1, 1.0), 2),
            "bid_size": random.randint(10, 1000),
            "ask_size": random.randint(10, 1000),
            "oi": random.randint(1000, 100000) if "FO" in instrument_key else 0
        }
        
        return tick

class StressTestHarness:
    """Main stress testing orchestrator"""
    
    def __init__(self):
        self.tick_simulator = TickSimulator()
        self.metrics = []
        self.process = psutil.Process()
        self.start_time = 0
        self.tick_generator_task = None
        self.metrics_collector_task = None
        
    async def setup_test_environment(self):
        """Setup test environment and start required services"""
        logger.info("🔧 SETTING UP STRESS TEST ENVIRONMENT")
        
        # Start option chain builder if not running
        try:
            await option_chain_builder.start()
            logger.info("✅ Option chain builder started")
        except Exception as e:
            logger.warning(f"Option chain builder start failed: {e}")
        
        # Clear any existing metrics
        self.metrics.clear()
        
    async def run_stress_test(self, duration_seconds: int = 60, target_ticks_per_sec: int = 5000) -> StressTestMetrics:
        """
        Run comprehensive stress test
        
        Args:
            duration_seconds: Test duration in seconds
            target_ticks_per_sec: Target tick generation rate
            
        Returns:
            StressTestMetrics: Comprehensive test results
        """
        logger.info(f"🚀 STARTING STRESS TEST: {duration_seconds}s @ {target_ticks_per_sec} ticks/sec")
        
        self.start_time = time.time()
        start_metrics = self._collect_system_metrics()
        
        # Test state
        ticks_generated = 0
        ticks_processed = 0
        queue_sizes = []
        latencies = []
        cpu_samples = []
        memory_samples = []
        errors = []
        warnings = []
        
        # Start tick generation
        self.tick_generator_task = asyncio.create_task(
            self._generate_ticks(target_ticks_per_sec, duration_seconds)
        )
        
        # Start metrics collection
        self.metrics_collector_task = asyncio.create_task(
            self._collect_test_metrics(duration_seconds, queue_sizes, latencies, cpu_samples, memory_samples, errors, warnings)
        )
        
        try:
            # Wait for test completion
            await asyncio.gather(
                self.tick_generator_task,
                self.metrics_collector_task,
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Stress test execution error: {e}")
            errors.append(str(e))
        
        # Get final processed tick count from websocket feed
        try:
            from app.services.websocket_market_feed import ws_feed_manager
            feed = await ws_feed_manager.get_feed()
            if feed:
                ticks_processed = feed.processed_ticks
                logger.info(f"Final processed ticks: {ticks_processed}")
        except Exception as e:
            logger.warning(f"Could not get final tick count: {e}")
        
        # Calculate final metrics
        end_time = time.time()
        actual_duration = end_time - self.start_time
        
        metrics = StressTestMetrics(
            test_duration=actual_duration,
            total_ticks_generated=ticks_generated,
            total_ticks_processed=ticks_processed,
            tick_drop_rate=(ticks_generated - ticks_processed) / max(ticks_generated, 1) * 100,
            max_queue_size=max(queue_sizes) if queue_sizes else 0,
            avg_queue_size=sum(queue_sizes) / len(queue_sizes) if queue_sizes else 0,
            max_latency=max(latencies) if latencies else 0,
            avg_latency=sum(latencies) / len(latencies) if latencies else 0,
            cpu_usage_peak=max(cpu_samples) if cpu_samples else 0,
            cpu_usage_avg=sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0,
            memory_usage_peak=max(memory_samples) if memory_samples else 0,
            memory_usage_avg=sum(memory_samples) / len(memory_samples) if memory_samples else 0,
            errors_count=len(errors),
            warnings_count=len(warnings)
        )
        
        logger.info("✅ STRESS TEST COMPLETED")
        return metrics
    
    async def _generate_ticks(self, target_rate: int, duration: int):
        """Generate ticks at target rate"""
        logger.info(f"📊 GENERATING TICKS @ {target_rate}/sec for {duration}s")
        
        interval = 1.0 / target_rate
        end_time = time.time() + duration
        tick_count = 0
        
        while time.time() < end_time:
            start_batch = time.time()
            
            # Generate batch of ticks
            batch_size = min(100, target_rate // 10)  # Process in batches
            for _ in range(batch_size):
                if time.time() >= end_time:
                    break
                    
                # Random instrument selection
                instrument = random.choice(self.tick_simulator.instruments)
                tick = self.tick_simulator.generate_tick(instrument)
                
                # Route tick through message router
                try:
                    message = message_router.route_tick(tick)
                    if message:
                        # Simulate processing delay
                        await asyncio.sleep(0.0001)  # 0.1ms processing simulation
                        tick_count += 1
                except Exception as e:
                    logger.error(f"Tick routing error: {e}")
            
            # Rate limiting
            batch_time = time.time() - start_batch
            sleep_time = max(0, interval - batch_time)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        logger.info(f"✅ GENERATED {tick_count} TICKS")
    
    async def _collect_test_metrics(self, duration: int, queue_sizes: List, latencies: List, 
                                   cpu_samples: List, memory_samples: List, errors: List, warnings: List):
        """Collect system metrics during test"""
        logger.info("📈 COLLECTING TEST METRICS")
        
        end_time = time.time() + duration
        sample_interval = 0.1  # 100ms sampling
        
        while time.time() < end_time:
            try:
                # System metrics
                cpu_percent = self.process.cpu_percent()
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                
                cpu_samples.append(cpu_percent)
                memory_samples.append(memory_mb)
                
                # Application metrics
                try:
                    from app.services.websocket_market_feed import ws_feed_manager
                    feed = await ws_feed_manager.get_feed()
                    if feed:
                        queue_sizes.append(feed._message_queue.qsize())
                        latencies.append(feed.max_tick_latency)
                except Exception as e:
                    logger.debug(f"Could not collect app metrics: {e}")
                
                await asyncio.sleep(sample_interval)
                
            except Exception as e:
                errors.append(f"Metrics collection error: {e}")
                await asyncio.sleep(1)
        
        logger.info("✅ METRICS COLLECTION COMPLETED")
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect baseline system metrics"""
        return {
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "timestamp": time.time()
        }
    
    def generate_report(self, metrics: StressTestMetrics) -> str:
        """Generate comprehensive stress test report"""
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    STRIKEIQ STRESS TEST REPORT                                      ║
╚══════════════════════════════════════════════════════════════════════════════════╝

📊 TEST EXECUTION SUMMARY
──────────────────────────────────────────────────────────────────────────────────
• Test Duration:           {metrics.test_duration:.2f} seconds
• Target Tick Rate:        5000 ticks/sec
• Total Ticks Generated:   {metrics.total_ticks_generated:,}
• Total Ticks Processed:   {metrics.total_ticks_processed:,}
• Tick Drop Rate:          {metrics.tick_drop_rate:.2f}%

📈 PERFORMANCE METRICS
──────────────────────────────────────────────────────────────────────────────────
• Max Queue Size:          {metrics.max_queue_size:,}
• Avg Queue Size:          {metrics.avg_queue_size:.1f}
• Max Processing Latency:  {metrics.max_latency:.4f}s
• Avg Processing Latency:  {metrics.avg_latency:.4f}s

💻 SYSTEM RESOURCE USAGE
──────────────────────────────────────────────────────────────────────────────────
• Peak CPU Usage:          {metrics.cpu_usage_peak:.1f}%
• Average CPU Usage:        {metrics.cpu_usage_avg:.1f}%
• Peak Memory Usage:        {metrics.memory_usage_peak:.1f} MB
• Average Memory Usage:      {metrics.memory_usage_avg:.1f} MB

⚠️ ERRORS & WARNINGS
──────────────────────────────────────────────────────────────────────────────────
• Total Errors:             {metrics.errors_count}
• Total Warnings:           {metrics.warnings_count}

🎯 PERFORMANCE ASSESSMENT
──────────────────────────────────────────────────────────────────────────────────
"""
        
        # Performance assessment
        if metrics.tick_drop_rate < 5:
            report += "✅ EXCELLENT: Tick drop rate under 5%\n"
        elif metrics.tick_drop_rate < 15:
            report += "⚠️  ACCEPTABLE: Tick drop rate under 15%\n"
        else:
            report += "❌ POOR: Tick drop rate exceeds 15%\n"
        
        if metrics.avg_latency < 0.01:
            report += "✅ EXCELLENT: Average latency under 10ms\n"
        elif metrics.avg_latency < 0.05:
            report += "⚠️  ACCEPTABLE: Average latency under 50ms\n"
        else:
            report += "❌ POOR: Average latency exceeds 50ms\n"
        
        if metrics.cpu_usage_avg < 70:
            report += "✅ EXCELLENT: Average CPU usage under 70%\n"
        elif metrics.cpu_usage_avg < 85:
            report += "⚠️  ACCEPTABLE: Average CPU usage under 85%\n"
        else:
            report += "❌ POOR: Average CPU usage exceeds 85%\n"
        
        report += f"""
📝 RECOMMENDATIONS
──────────────────────────────────────────────────────────────────────────────────
"""
        
        if metrics.tick_drop_rate > 15:
            report += "• Consider increasing queue size or optimizing processing pipeline\n"
        
        if metrics.avg_latency > 0.05:
            report += "• Investigate bottlenecks in message routing and option chain building\n"
        
        if metrics.cpu_usage_avg > 85:
            report += "• Consider load balancing or CPU-intensive task optimization\n"
        
        if metrics.max_queue_size > 4000:
            report += "• Queue approaching capacity - monitor for potential overflow\n"
        
        report += "\n" + "="*80 + "\n"
        
        return report
    
    async def cleanup_test_environment(self):
        """Cleanup test environment"""
        logger.info("🧹 CLEANING UP TEST ENVIRONMENT")
        
        # Cancel any running tasks
        if self.tick_generator_task and not self.tick_generator_task.done():
            self.tick_generator_task.cancel()
        
        if self.metrics_collector_task and not self.metrics_collector_task.done():
            self.metrics_collector_task.cancel()
        
        # Stop services
        try:
            await option_chain_builder.stop()
            logger.info("✅ Option chain builder stopped")
        except Exception as e:
            logger.warning(f"Option chain builder stop failed: {e}")

async def run_stress_test_suite():
    """Run complete stress test suite"""
    harness = StressTestHarness()
    
    try:
        # Setup
        await harness.setup_test_environment()
        
        # Run stress test
        metrics = await harness.run_stress_test(duration_seconds=60, target_ticks_per_sec=5000)
        
        # Generate and print report
        report = harness.generate_report(metrics)
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"stress_test_report_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Report saved to {report_file}")
        
        return metrics
        
    finally:
        # Cleanup
        await harness.cleanup_test_environment()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run stress test
    asyncio.run(run_stress_test_suite())
