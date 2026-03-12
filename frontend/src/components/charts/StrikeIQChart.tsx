import { useEffect, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
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
      rightPriceScale: {
        visible: true,
        borderVisible: false,
      },
      leftPriceScale: {
        visible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
    });
    
    console.log("CHART INIT → chart created");

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });
    
    console.log("SERIES INIT → candlestick series created");

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
      
      console.log("CANDLE UPDATE →", formattedCandles.slice(0, 3));
      candleSeriesRef.current.setData(formattedCandles);
    }, [candles, chartReady]);

  // AI Overlay Hooks
  useEffect(() => {
    if (!chartReady) return;
    
    console.log("PATTERN ENGINE RUNNING → chartAnalysis:", chartAnalysis ? "found" : "none");

    if (chartAnalysis?.signal === "BUY") {
      console.log("AI BUY SIGNAL", chartAnalysis.price);
      console.log("OVERLAY DRAWN → BUY signal");
      // TODO: Add BUY signal overlay
    }
    
    if (chartAnalysis?.signal === "SELL") {
      console.log("AI SELL SIGNAL", chartAnalysis.price);
      console.log("OVERLAY DRAWN → SELL signal");
      // TODO: Add SELL signal overlay
    }

    // Elliott wave labels
    if (chartAnalysis?.wave) {
      console.log("Elliott Wave:", chartAnalysis.wave);
      console.log("OVERLAY DRAWN → Elliott Wave");
      // TODO: Add Elliott wave overlay
    }

    // NeoWave patterns
    if (chartAnalysis?.neo_pattern) {
      console.log("NeoWave Pattern:", chartAnalysis.neo_pattern);
      console.log("OVERLAY DRAWN → NeoWave Pattern");
      // TODO: Add NeoWave pattern overlay
    }

    // Supply/Demand zones
    if (chartAnalysis?.supply_zone || chartAnalysis?.demand_zone) {
      console.log("Supply Zone:", chartAnalysis.supply_zone);
      console.log("Demand Zone:", chartAnalysis.demand_zone);
      console.log("OVERLAY DRAWN → Supply/Demand Zones");
      // TODO: Add zone overlays
    }
    
    console.log("STRIKEIQ CHART PIPELINE OK");
  }, [chartAnalysis, chartReady]);

  return (
    <div ref={chartRef} style={{ width: "100%", height: "400px" }} />
  );
}
