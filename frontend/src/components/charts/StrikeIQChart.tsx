import { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";
import { useWSStore } from "../../core/ws/wsStore";

export default function StrikeIQChart() {

  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
  const chartAnalysis = useWSStore(s => s.chartAnalysis);
  const candles = useWSStore(s => s.candles);
  const [chartReady, setChartReady] = useState(false);

  // Initialize chart once
  useEffect(() => {
    if (!chartRef.current || chartInstanceRef.current) return;

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 400,
      layout: { 
        background: { color: "#0f172a" }, 
        textColor: "#d1d5db" 
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: {
        mode: 0,
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    chartInstanceRef.current = chart;
    candleSeriesRef.current = candleSeries;
    setChartReady(true);

    // Handle window resize
    const handleResize = () => {
      if (chartRef.current && chartInstanceRef.current) {
        chartInstanceRef.current.applyOptions({
          width: chartRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, []);

  // Update candle data when available
  useEffect(() => {
    if (!chartReady || !candleSeriesRef.current || !candles || candles.length === 0) return;

    // Convert candle data to lightweight-charts format
    const formattedCandles = candles.map(candle => ({
      time: candle.time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candleSeriesRef.current.setData(formattedCandles);
  }, [candles, chartReady]);

  // AI Overlay Hooks
  useEffect(() => {
    if (!chartReady) return;

    if (chartAnalysis?.signal === "BUY") {
      console.log("AI BUY SIGNAL", chartAnalysis.price);
      // TODO: Add BUY signal overlay
    }
    
    if (chartAnalysis?.signal === "SELL") {
      console.log("AI SELL SIGNAL", chartAnalysis.price);
      // TODO: Add SELL signal overlay
    }

    // Elliott wave labels
    if (chartAnalysis?.wave) {
      console.log("Elliott Wave:", chartAnalysis.wave);
      // TODO: Add Elliott wave overlay
    }

    // NeoWave patterns
    if (chartAnalysis?.neo_pattern) {
      console.log("NeoWave Pattern:", chartAnalysis.neo_pattern);
      // TODO: Add NeoWave pattern overlay
    }

    // Supply/Demand zones
    if (chartAnalysis?.supply_zone || chartAnalysis?.demand_zone) {
      console.log("Supply Zone:", chartAnalysis.supply_zone);
      console.log("Demand Zone:", chartAnalysis.demand_zone);
      // TODO: Add zone overlays
    }
  }, [chartAnalysis, chartReady]);

  return (
    <div ref={chartRef} style={{ width: "100%", height: "400px" }} />
  );
}
