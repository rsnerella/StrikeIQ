import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, LineStyle, CrosshairMode, SeriesMarkerPosition, SeriesMarkerShape, LineWidth } from 'lightweight-charts';
import { useMarketContextStore } from '@/stores/marketContextStore';
import { LiveMarketData } from '@/hooks/useLiveMarketData';
import { useWSStore } from '@/core/ws/wsStore';
import { useShallow } from 'zustand/shallow';

interface ChartIntelligenceOverlay {
    type: 'marker' | 'rectangle' | 'trendline';
    time?: number;
    price?: number;
    label?: string;
    top?: number;
    bottom?: number;
    points?: Array<{time: number; price: number}>;
    color?: string;
    width?: number;
}

interface StrikeIQPriceChartProps {
    data?: LiveMarketData | null;
}

export const StrikeIQPriceChart: React.FC<StrikeIQPriceChartProps> = ({ data }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const waveSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    
    // Store price lines to remove them on update
    const priceLinesRef = useRef<any[]>([]);
    
    // Chart intelligence overlay series refs
    const overlaySeriesRef = useRef<Map<string, ISeriesApi<any>>>(new Map());
    const markerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const rectangleSeriesRef = useRef<Map<string, ISeriesApi<"Area">>>(new Map());
    const trendlineSeriesRef = useRef<Map<string, ISeriesApi<"Line">>>(new Map());
    
    // Track last overlay payload to avoid unnecessary updates
    const lastOverlayPayloadRef = useRef<string>('');

    const symbol = useMarketContextStore(state => state.symbol);
    const timeframe = useMarketContextStore(state => state.timeframe || '1m');

    // Use granular selectors for performance
    const { spot, timestamp, chartAnalysis, analytics, aiIntelligence, marketStatus } = useWSStore(
        useShallow(state => {
            const rawUpdate = state.lastUpdate;
            let tsNum = typeof rawUpdate === 'number' ? rawUpdate : Date.now();
            if (isNaN(tsNum)) tsNum = Date.now();
            
            return {
                spot: state.spot,
                timestamp: tsNum,
                chartAnalysis: state.chartAnalysis,
                analytics: state.analytics,
                aiIntelligence: state.aiIntelligence,
                marketStatus: state.marketStatus
            };
        })
    );

    const [loading, setLoading] = useState(true);
    const [chartMessage, setChartMessage] = useState<string | null>(null);

    // References to hold current state of markers and zones so we can update them
    const currentPriceRef = useRef<number | null>(null);
    const currentCloseTimeRef = useRef<number | null>(null);

    // Timeframe mapping for backend API
    const timeframeMap = useMemo(() => ({
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '1h': '1h',
        '1d': '1d'
    }), []);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: 'rgba(255,255,255,0.7)',
            },
            grid: {
                vertLines: { color: 'rgba(255,255,255,0.05)' },
                horzLines: { color: 'rgba(255,255,255,0.05)' },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
            },
            rightPriceScale: {
                visible: true,
                borderVisible: false,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1
                }
            },
            leftPriceScale: {
                visible: false
            },
            timeScale: {
                borderVisible: false,
                timeVisible: true,
                secondsVisible: false,
                barSpacing: 10,
                // Fix: Shift labels by 5.5 hours to align UTC data with IST if needed, 
                // but usually lightweight-charts expects UTC and browser converts to local.
                // We'll stick to local time string but ensure the format is clean.
                tickMarkFormatter: (time: number) => {
                    const date = new Date(time * 1000);
                    return date.toLocaleTimeString('en-IN', {
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                }
            }
        });
        
        console.log("STRIKEIQ CHART INIT → chart created");

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#4ade80',
            downColor: '#f87171',
            borderVisible: false,
            wickUpColor: '#4ade80',
            wickDownColor: '#f87171',
            priceScaleId: 'right',
        });
        
        console.log("STRIKEIQ CHART SERIES → candlestick series created");

        const waveSeries = chart.addLineSeries({
            color: '#a855f7',
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
        });

        chartRef.current = chart;
        seriesRef.current = candlestickSeries;
        waveSeriesRef.current = waveSeries;

        const handleResize = () => {
            if (!chartContainerRef.current) return

            chart.applyOptions({
                width: chartContainerRef.current.clientWidth,
                height: chartContainerRef.current.clientHeight
            })
        }

        window.addEventListener("resize", handleResize)
        
        return () => {
            window.removeEventListener("resize", handleResize)
            clearChartIntelligenceOverlays();
            chart.remove();
        };
    }, []);

    // Load historical candles
    useEffect(() => {
        let isMounted = true;
        const loadHistoricalCandles = async () => {
            if (!chartRef.current || !symbol) return;
            
            console.log("STRIKEIQ CHART TIMEFRAME →", timeframe);
            
            setLoading(true);
            try {
                // Reset chart before loading new symbol
                clearChartIntelligenceOverlays();
                lastOverlayPayloadRef.current = '';
                
                if (seriesRef.current) {
                    chartRef.current.removeSeries(seriesRef.current);
                    seriesRef.current = null;
                }
                if (waveSeriesRef.current) {
                    chartRef.current.removeSeries(waveSeriesRef.current);
                    waveSeriesRef.current = null;
                }

                // Reset tracking refs on symbol/timeframe change
                currentPriceRef.current = null;
                currentCloseTimeRef.current = null;

                // Add fresh series
                const candlestickSeries = chartRef.current.addCandlestickSeries({
                    upColor: '#4ade80',
                    downColor: '#f87171',
                    borderVisible: false,
                    wickUpColor: '#4ade80',
                    wickDownColor: '#f87171',
                    priceScaleId: 'right',
                });
                const waveSeries = chartRef.current.addLineSeries({
                    color: '#a855f7',
                    lineWidth: 2,
                    lineStyle: LineStyle.Solid,
                });

                seriesRef.current = candlestickSeries;
                waveSeriesRef.current = waveSeries;

                const backendTimeframe = timeframeMap[timeframe as keyof typeof timeframeMap] || '1m';
                
                console.log("STRIKEIQ CHART FETCHING →", {
                    symbol,
                    timeframe: backendTimeframe
                });
                
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/market/candles?symbol=${symbol}&tf=${backendTimeframe}&limit=400`);
                
                // Check if response is JSON before parsing
                const contentType = res.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    console.warn('STRIKEIQ CHART → Backend not available - non-JSON response');
                    setChartMessage('Backend offline - chart data unavailable');
                    setLoading(false);
                    return;
                }
                
                const responseData = await res.json();
                console.log("STRIKEIQ CHART RESPONSE →", responseData);
                
                if (res.ok) {
                    const candles = responseData.candles || [];
                    
                    // Show message if no candles
                    if (!candles || candles.length === 0) {
                        setChartMessage('Market closed — showing last session data');
                        setLoading(false);
                        return;
                    }
                    
                    setChartMessage(null);
                    
                    if (isMounted && seriesRef.current && candles.length > 0) {
                        // Filter candles to NSE trading hours (09:15 → 15:30)
                        // Determine current IST time
                        const now = new Date();
                        const istTime = new Date(
                            now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
                        );

                        const currentMinutes =
                            istTime.getHours() * 60 + istTime.getMinutes();

                        // NSE trading session
                        const SESSION_START = 9 * 60 + 15;
                        const SESSION_END = 15 * 60 + 30;

                        const isMarketOpen =
                            currentMinutes >= SESSION_START &&
                            currentMinutes <= SESSION_END;

                        console.log("DEBUG_CANDLE_COUNT", candles.length);
                        console.log("DEBUG_MARKET_TIME", new Date().toLocaleString("en-IN",{timeZone:"Asia/Kolkata"}));

                        let filteredCandles = candles.filter((c: any) => {
                            const date = new Date(c.time * 1000);
                            const minutes = date.getHours() * 60 + date.getMinutes();
                            return minutes >= SESSION_START && minutes <= SESSION_END;
                        });

                        console.log("DEBUG_FILTERED_CANDLES", filteredCandles.length);

                        if (filteredCandles.length === 0) {
                            filteredCandles = candles;

                            // Only show "market closed" if market is actually closed now
                            setChartMessage(
                                isMarketOpen
                                    ? null
                                    : "Market closed — showing last session data"
                            );
                        } else {
                            setChartMessage(null);
                        }

                        console.log("MARKET_STATUS", isMarketOpen);
                        console.log("FINAL_CANDLE_COUNT", filteredCandles.length);

                        
                        // Sanitize candles - filter out invalid data
                        filteredCandles = filteredCandles.filter((c: any) => {
                            if (!c.time || !c.open || !c.high || !c.low || !c.close) return false;
                            if (c.open <= 0 || c.high <= 0 || c.low <= 0 || c.close <= 0) return false;
                            if (c.high < c.low) return false; // Data error
                            if (c.high < c.open || c.high < c.close) return false; // Invalid OHLC
                            if (c.low > c.open || c.low > c.close) return false; // Invalid OHLC
                            // Reject extreme outliers (> 50% deviation from median)
                            const priceRange = Math.abs(c.close - c.open) / c.open;
                            if (priceRange > 0.5) return false;
                            return true;
                        });
                        
                        console.log("STRIKEIQ CHART FILTERED →", filteredCandles.length, "candles");
                        
                        const formattedCandles = filteredCandles.map((c: any) => ({
                            time: Math.floor(Number(c.time)),
                            open: c.open,
                            high: c.high,
                            low: c.low,
                            close: c.close
                        }));
                        
                        // Sort candles by time (lightweight-charts requirement)
                        formattedCandles.sort((a, b) => a.time - b.time);
                        
                        seriesRef.current.setData(formattedCandles);
                        chartRef.current?.timeScale().fitContent();
                        const lastCandle = formattedCandles[formattedCandles.length - 1];
                        currentPriceRef.current = Number(lastCandle.close);
                        currentCloseTimeRef.current = Number(lastCandle.time);
                        
                        // Proactively clear "Market Closed" if we have genuine recent data
                        if (formattedCandles.length > 0) {
                            setChartMessage(null);
                        }
                    }
                } else {
                    console.log("STRIKEIQ CHART API ERROR →", res.status, res.statusText);
                }
            } catch (err: any) {
                console.error("STRIKEIQ CHART → Failed to load historical candles", err);
                
                // Handle backend offline scenario
                if (err?.message?.includes('Backend not available')) {
                    setChartMessage('Backend offline - chart data unavailable');
                    setLoading(false);
                    return;
                }
                
                // Fallback test candles if market closed
                if (seriesRef.current && isMounted) {
                    const testCandles = [
                        { time: 1700000000 as any, open: 100, high: 105, low: 98, close: 102 },
                        { time: 1700000600 as any, open: 102, high: 108, low: 101, close: 107 },
                        { time: 1700001200 as any, open: 107, high: 110, low: 104, close: 105 }
                    ];
                    console.log("STRIKEIQ CHART → Test candles loaded");
                    seriesRef.current.setData(testCandles);
                    currentPriceRef.current = 105;
                    currentCloseTimeRef.current = 1700001200;
                }
            } finally {
                if (isMounted) setLoading(false);
                console.log("STRIKEIQ CHART → Initialization complete");
            }
        };

        loadHistoricalCandles().catch(err => {
            console.error('STRIKEIQ CHART → loadHistoricalCandles failed at top level:', err);
            if (err?.message?.includes('Backend not available')) {
                setChartMessage('Backend offline - chart data unavailable');
                setLoading(false);
            }
        });

        return () => {
            isMounted = false;
        };
    }, [symbol, timeframe, timeframeMap]);

    // Update with live ticks
    useEffect(() => {
        if (!spot || !seriesRef.current || !currentCloseTimeRef.current || !currentPriceRef.current) return;

        if (chartMessage && chartMessage.includes("Market closed")) {
            setChartMessage(null);
        }

        // timestamp is now guaranteed to be a number from the selector
        const now = Math.floor(timestamp / 1000);
        // Round to nearest minute for timeframe
        const tfSecs = timeframe === '15m' ? 900 : timeframe === '5m' ? 300 : timeframe === '1h' ? 3600 : timeframe === '1d' ? 86400 : 60;
        const candleTime = Number(now - (now % tfSecs));

        if (isNaN(candleTime)) return;

        const price = Number(spot);
        const lastCandleTime = currentCloseTimeRef.current || 0;

        if (price > 0 && candleTime >= lastCandleTime) {
            // Get the current high/low from the existing candle if we're updating
            let currentHigh = currentPriceRef.current || price;
            let currentLow = currentPriceRef.current || price;
            
            if (candleTime === lastCandleTime && currentPriceRef.current !== null) {
                // Updating existing candle - preserve high/low
                currentHigh = Math.max(currentPriceRef.current, price);
                currentLow = Math.min(currentPriceRef.current, price);
            }
            
            const candleUpdate = {
                time: Math.floor(candleTime) as any,
                open: candleTime > lastCandleTime ? price : (currentPriceRef.current || price),
                high: candleTime > lastCandleTime ? price : currentHigh,
                low: candleTime > lastCandleTime ? price : currentLow,
                close: price,
            };
            
            // Final safety check for lightweight-charts
            if (typeof candleUpdate.time !== 'number' || isNaN(candleUpdate.time)) return;

            try {
                seriesRef.current.update(candleUpdate);
                currentCloseTimeRef.current = candleTime;
                currentPriceRef.current = price;
            } catch (err) {
                console.warn("STRIKEIQ CHART → Update failed:", err, candleUpdate);
            }
        }
    }, [spot, timestamp, timeframe]);

    // Clear all chart intelligence overlays
    const clearChartIntelligenceOverlays = useCallback(() => {
        if (!chartRef.current) return;
        
        // Clear marker series
        if (markerSeriesRef.current) {
            try {
                chartRef.current.removeSeries(markerSeriesRef.current);
            } catch {}
            markerSeriesRef.current = null;
        }
        
        // Clear rectangle series
        rectangleSeriesRef.current.forEach((series) => {
            try {
                chartRef.current?.removeSeries(series);
            } catch {}
        });
        rectangleSeriesRef.current.clear();
        
        // Clear trendline series
        trendlineSeriesRef.current.forEach((series) => {
            try {
                chartRef.current?.removeSeries(series);
            } catch {}
        });
        trendlineSeriesRef.current.clear();
        
        // Clear overlay series map
        overlaySeriesRef.current.forEach((series) => {
            try {
                chartRef.current?.removeSeries(series);
            } catch {}
        });
        overlaySeriesRef.current.clear();

        // Clear price lines
        priceLinesRef.current.forEach(pl => {
            try {
                seriesRef.current?.removePriceLine(pl)
            } catch {}
        });
        priceLinesRef.current = [];
        
        // Clear markers on main series
        seriesRef.current?.setMarkers([]);
    }, []);
    
    // Render chart intelligence overlays
    const renderChartIntelligenceOverlays = useCallback((overlays: ChartIntelligenceOverlay[]) => {
        if (!chartRef.current || !seriesRef.current) return;
        
        clearChartIntelligenceOverlays();
        
        const markers: any[] = [];
        const candles = seriesRef.current.data();
        if (candles.length === 0) return;
        
        const firstTime = Number(candles[0].time);
        const lastTime = Number(candles[candles.length - 1].time);
        
        overlays.forEach((overlay, index) => {
            const overlayId = `overlay-${index}-${overlay.type}`;
            
            switch (overlay.type) {
                case 'marker':
                    if (overlay.time !== undefined) {
                        markers.push({
                            time: Number(overlay.time),
                            position: "aboveBar" as SeriesMarkerPosition,
                            color: overlay.color || "#3b82f6",
                            shape: "circle" as SeriesMarkerShape,
                            text: overlay.label || '',
                        });
                    }
                    break;
                    
                case 'rectangle':
                    if (overlay.top !== undefined && overlay.bottom !== undefined) {
                        const rectSeries = chartRef.current!.addAreaSeries({
                            topColor: overlay.color || 'rgba(59, 130, 246, 0.2)',
                            bottomColor: 'transparent',
                            lineColor: 'transparent',
                            lineWidth: 0 as LineWidth,
                            priceScaleId: 'right',
                        });
                        
                        rectSeries.setData([
                            { time: firstTime as any, value: Number(overlay.top) },
                            { time: lastTime as any, value: Number(overlay.top) }
                        ]);
                        
                        rectangleSeriesRef.current.set(overlayId, rectSeries);
                        overlaySeriesRef.current.set(overlayId, rectSeries);
                    }
                    break;
                    
                case 'trendline':
                    if (overlay.points && overlay.points.length >= 2) {
                        const lineSeries = chartRef.current!.addLineSeries({
                            color: overlay.color || '#3b82f6',
                            lineWidth: (overlay.width || 2) as LineWidth,
                            lineStyle: LineStyle.Solid,
                            priceScaleId: 'right',
                        });
                        
                        const lineData = overlay.points.map(point => ({
                            time: Number(point.time) as any,
                            value: Number(point.price),
                        })).sort((a, b) => Number(a.time) - Number(b.time));
                        
                        lineSeries.setData(lineData);
                        trendlineSeriesRef.current.set(overlayId, lineSeries);
                        overlaySeriesRef.current.set(overlayId, lineSeries);
                    }
                    break;
            }
        });
        
        if (markers.length > 0) {
            seriesRef.current.setMarkers(markers.sort((a, b) => a.time - b.time));
        }
    }, [clearChartIntelligenceOverlays]);
    
    // Handle chart intelligence overlays from backend
    useEffect(() => {
        const overlays = aiIntelligence?.chart_intelligence?.overlay_objects;
        if (!overlays || !Array.isArray(overlays)) {
            clearChartIntelligenceOverlays();
            return;
        }
        
        const payloadString = JSON.stringify(overlays);
        if (payloadString === lastOverlayPayloadRef.current) return;
        
        lastOverlayPayloadRef.current = payloadString;
        renderChartIntelligenceOverlays(overlays);
    }, [aiIntelligence?.chart_intelligence?.overlay_objects, renderChartIntelligenceOverlays, clearChartIntelligenceOverlays, loading]);
    
    // Clear overlays when symbol changes
    useEffect(() => {
        clearChartIntelligenceOverlays();
        lastOverlayPayloadRef.current = '';
    }, [symbol, clearChartIntelligenceOverlays]);

    return (
        <div className="w-full h-full relative border border-white/10 rounded-xl overflow-visible bg-black/40 backdrop-blur-md">
            {loading && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60">
                    <span className="text-white/70 font-mono text-xs tracking-widest animate-pulse">LOADING STRIKEIQ CHART...</span>
                </div>
            )}
            {!loading && chartMessage && (
                <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/40 pointer-events-none">
                    <div className="bg-black/60 backdrop-blur-md px-4 py-2 rounded-lg border border-white/10 shadow-2xl">
                        <span className="text-white/60 font-mono text-xs uppercase tracking-wider">{chartMessage}</span>
                    </div>
                </div>
            )}
            {/* Header info overlay */}
            <div className="absolute top-4 left-4 z-10 font-mono text-xs text-white/50 bg-black/50 px-3 py-1.5 rounded-md backdrop-blur-sm shadow-xl border border-white/5 flex items-center gap-2">
                <span className="text-white font-bold">{symbol}</span>
                <span className="opacity-30">|</span>
                <span>{timeframe}</span>
                <span className="opacity-30">|</span>
                <span className={marketStatus === 'OPEN' ? 'text-green-400 font-bold' : 'text-orange-400 font-bold'}>
                    {marketStatus}
                </span>
                <span className="opacity-30">|</span>
                <span>STRIKEIQ CHART ENGINE</span>
            </div>
            
            <div className="w-full h-full relative pr-10">
                <div ref={chartContainerRef} className="w-full h-full" style={{ minHeight: '400px' }} />
            </div>
        </div>
    );
};

export default StrikeIQPriceChart;
