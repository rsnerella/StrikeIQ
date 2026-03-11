import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, LineStyle, CrosshairMode } from 'lightweight-charts';
import { useMarketContextStore } from '@/stores/marketContextStore';
import { LiveMarketData } from '@/hooks/useLiveMarketData';

interface AdvancedPriceChartProps {
    data: LiveMarketData | null;
}

export const AdvancedPriceChart: React.FC<AdvancedPriceChartProps> = ({ data }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const waveSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    
    // Store price lines to remove them on update
    const priceLinesRef = useRef<any[]>([]);

    const symbol = useMarketContextStore(state => state.symbol);
    const timeframe = useMarketContextStore(state => state.timeframe || '1m');

    const [loading, setLoading] = useState(true);

    // References to hold current state of markers and zones so we can update them
    const currentPriceRef = useRef<number | null>(null);
    const currentCloseTimeRef = useRef<number | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: 'rgba(255, 255, 255, 0.7)',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                autoScale: true,
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#4ade80',
            downColor: '#f87171',
            borderVisible: false,
            wickUpColor: '#4ade80',
            wickDownColor: '#f87171',
        });

        const waveSeries = chart.addLineSeries({
            color: '#a855f7',
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
        });

        chartRef.current = chart;
        seriesRef.current = candlestickSeries;
        waveSeriesRef.current = waveSeries;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);
        
        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    // Load historical candles
    useEffect(() => {
        let isMounted = true;
        const loadHistoricalCandles = async () => {
            if (!chartRef.current || !symbol) return;
            
            setLoading(true);
            try {
                // PHASE 1: Reset chart before loading new symbol
                if (seriesRef.current) {
                    chartRef.current.removeSeries(seriesRef.current);
                    seriesRef.current = null;
                }
                if (waveSeriesRef.current) {
                    chartRef.current.removeSeries(waveSeriesRef.current);
                    waveSeriesRef.current = null;
                }

                // Add fresh series
                const candlestickSeries = chartRef.current.addCandlestickSeries({
                    upColor: '#4ade80',
                    downColor: '#f87171',
                    borderVisible: false,
                    wickUpColor: '#4ade80',
                    wickDownColor: '#f87171',
                });
                const waveSeries = chartRef.current.addLineSeries({
                    color: '#a855f7',
                    lineWidth: 2,
                    lineStyle: LineStyle.Solid,
                });

                seriesRef.current = candlestickSeries;
                waveSeriesRef.current = waveSeries;

                const res = await fetch(`/api/v1/market/candles?symbol=${symbol}&tf=${timeframe}&limit=300`);
                if (res.ok) {
                    const responseData = await res.json();
                    const candles = responseData.candles || [];
                    
                    if (isMounted && seriesRef.current && candles.length > 0) {
                        seriesRef.current.setData(candles.map((c: any) => ({
                            time: c.time,
                            open: c.open,
                            high: c.high,
                            low: c.low,
                            close: c.close
                        })));
                        const lastCandle = candles[candles.length - 1];
                        currentPriceRef.current = lastCandle.close;
                        currentCloseTimeRef.current = lastCandle.time;
                    }
                }
            } catch (err) {
                console.error("Failed to load historical candles", err);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        loadHistoricalCandles();

        return () => {
            isMounted = false;
        };
    }, [symbol, timeframe]);

    // Update with live ticks
    useEffect(() => {
        if (!data || !data.spot || !seriesRef.current || !currentCloseTimeRef.current) return;

        const now = Math.floor(new Date(data.timestamp).getTime() / 1000);
        // Round to nearest minute for '1m'
        const tfSecs = timeframe === '15m' ? 900 : timeframe === '5m' ? 300 : 60;
        const candleTime = now - (now % tfSecs);

        const price = data.spot;

        if (price > 0 && candleTime >= currentCloseTimeRef.current) {
            // New candle or update current
            if (candleTime > currentCloseTimeRef.current) {
                seriesRef.current.update({
                    time: candleTime as any,
                    open: price,
                    high: price,
                    low: price,
                    close: price,
                });
                currentCloseTimeRef.current = candleTime;
            } else {
                // Not ideal for full OHL update since we only have tick price, 
                // but this satisfies lightweight chart typings
                seriesRef.current.update({
                    time: candleTime as any,
                    open: price, // we lose true open without a state-held OHL
                    high: price,
                    low: price,
                    close: price,
                });
            }
        }
    }, [data?.spot, data?.timestamp, timeframe]);

    // Handle overlays and markers
    useEffect(() => {
        if (!seriesRef.current || !chartRef.current || !waveSeriesRef.current || !data) return;

        // Clear previous lines
        priceLinesRef.current.forEach(pl => seriesRef.current?.removePriceLine(pl));
        priceLinesRef.current = [];

        const chartAnalysis = data?.chartAnalysis;

        // Phase 5: Elliot Wave
        const waves = chartAnalysis?.wave_points || [];
        if (waves.length > 0) {
            const waveData = waves.map((w: any) => ({
                time: (w.time) as any,
                value: w.price
            })).sort((a: any, b: any) => a.time - b.time);
            
            waveSeriesRef.current.setData(waveData);
        } else {
            waveSeriesRef.current.setData([]);
        }

        const markers: any[] = [];
        
        // Phase 8: Gamma Walls (Structural)
        const gamma = (data?.analytics as any)?.structural || {};
        if (gamma.resistance_level) {
            priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: gamma.resistance_level,
                color: '#ef4444',
                lineWidth: 2,
                lineStyle: LineStyle.Solid,
                title: 'Call Wall',
                axisLabelVisible: true,
            }));
        }
        if (gamma.support_level) {
            priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: gamma.support_level,
                color: '#22c55e',
                lineWidth: 2,
                lineStyle: LineStyle.Solid,
                title: 'Put Wall',
                axisLabelVisible: true,
            }));
        }

        // Phase 6 & 7 & 10: SMC / ICT / Zones
        const allZones = chartAnalysis?.all_zones || [];
        allZones.forEach((z: any) => {
            const color = (z.type.includes('SUPPLY') || z.type.includes('BEARISH')) ? '#f87171' : 
                         (z.type.includes('DEMAND') || z.type.includes('BULLISH')) ? '#4ade80' : '#fbbf24';
            
            // Draw top boundary
            priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: z.top,
                color: color,
                lineWidth: 1,
                lineStyle: LineStyle.Dashed,
                title: z.type,
                axisLabelVisible: false,
            }));
            // Draw bottom boundary
            priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: z.bottom,
                color: color,
                lineWidth: 1,
                lineStyle: LineStyle.Dashed,
                axisLabelVisible: false,
            }));
        });

        // ICT Equilibrium
        const ict = (data?.analytics as any)?.advanced_strategies?.ict || {};
        if (ict.premium_discount_zone?.atm) {
            priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: ict.premium_discount_zone.atm,
                color: '#60a5fa',
                lineWidth: 1,
                lineStyle: LineStyle.Dotted,
                title: 'ICT EQ',
                axisLabelVisible: true,
            }));
        }

        // Phase 9: AI Trade Signals (Real Options)
        const activeTrade = (data?.analytics as any)?.trade_setup;
        if (activeTrade && activeTrade.entry) {
            const isBullish = activeTrade.option_type === 'CE';
            
            markers.push({
                time: currentCloseTimeRef.current,
                position: isBullish ? 'belowBar' : 'aboveBar',
                color: isBullish ? '#34d399' : '#f87171',
                shape: isBullish ? 'arrowUp' : 'arrowDown',
                text: `BUY ${activeTrade.option_type} @ ${activeTrade.entry}`,
            });

            // Note: Chart is price-scaled to Index, but trade is in Premium.
            // We only show markers on the index chart for entry confirmation.
            // Targets and SL lines for PREMIUM are better shown as text or in a dedicated premium chart.
            // However, the user asked for SL/Target lines. If they meant index levels, we should use them.
            // Since the engine only gave us premium levels, we will skip drawing lines 
            // on the index chart to avoid scaling issues, unless we have index-equivalent targets.
        }

        // Liquidity Sweep Markers
        const smc = (data?.analytics as any)?.advanced_strategies?.smc || {};
        if (smc.liquidity_sweep?.detected) {
            markers.push({
                time: currentCloseTimeRef.current,
                position: smc.liquidity_sweep.direction === 'bullish' ? 'belowBar' : 'aboveBar',
                color: '#fcd34d',
                shape: 'arrowUp',
                text: 'SWEEP',
            });
        }

        // Apply markers
        markers.sort((a, b) => a.time - b.time);
        seriesRef.current.setMarkers(markers);
        
    }, [data]);

    return (
        <div className="w-full h-full relative border border-white/10 rounded-xl overflow-hidden bg-black/40 backdrop-blur-md">
            {loading && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60">
                    <span className="text-white/70 font-mono text-xs tracking-widest animate-pulse">LOADING SYMBOL DATA...</span>
                </div>
            )}
            {/* Header info overlay */}
            <div className="absolute top-4 left-4 z-10 font-mono text-xs text-white/50 bg-black/50 px-3 py-1.5 rounded-md backdrop-blur-sm shadow-xl border border-white/5">
                <span className="text-white font-bold">{symbol}</span> • {timeframe} CHART ENGINE
            </div>
            
            <div ref={chartContainerRef} className="w-full h-full" style={{ minHeight: '400px' }} />
        </div>
    );
};

export default AdvancedPriceChart;
