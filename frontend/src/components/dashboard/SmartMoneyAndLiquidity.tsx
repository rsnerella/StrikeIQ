"use client";
import React, { memo } from 'react';
import { Minus } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface SmartMoneyAndLiquidityProps {
    data: LiveMarketData | null;
    isLiveMode: boolean;
    isSnapshotMode: boolean;
    mode: string;
}

export function SmartMoneyPanel({ data, isSnapshotMode }: { data: LiveMarketData | null; isSnapshotMode: boolean }) {
    const biasLabel = (data as any)?.intelligence?.bias?.label ?? 'NEUTRAL';
    const biasStrength = (data as any)?.intelligence?.bias?.bias_strength ?? 0;
    const confidence = (data as any)?.intelligence?.bias?.score ?? 0;

    return (
        <div
            className="trading-panel h-full"
            onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = CARD_HOVER_BORDER;
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
            }}
        >
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Smart Money Flow</SectionLabel>
                {isSnapshotMode && (
                    <span className="text-[9px] font-bold font-mono px-3 py-1 rounded-full bg-slate-500/10 border border-slate-500/20 text-slate-400 tracking-widest uppercase">
                        DISABLED
                    </span>
                )}
            </div>

            <div className="space-y-4">
                {[
                    { label: 'Current Sentiment', value: biasLabel, color: biasLabel === 'BULLISH' ? '#4ade80' : biasLabel === 'BEARISH' ? '#f87171' : '#94a3b8' },
                    { label: 'Aggregated Strength', value: biasStrength.toFixed(1), color: '#fff' },
                    { label: 'Signal Confidence', value: `${confidence.toFixed(1)}%`, color: confidence > 70 ? '#4ade80' : '#fb923c' },
                ].map(({ label, value, color }) => (
                    <div
                        key={label}
                        className="flex justify-between items-center p-3 rounded-xl transition-all hover:bg-white/5"
                        style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
                    >
                        <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">{label}</span>
                        <span className="text-[12px] font-bold font-mono tracking-tight tabular-nums" style={{ color }}>
                            {value}
                        </span>
                    </div>
                ))}
            </div>

            <div className="mt-8">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400"></div>
                    <span className="text-[10px] font-bold font-mono tracking-widest uppercase text-slate-500">Flow Concentration</span>
                </div>
                <div className="grid grid-cols-5 gap-1.5 h-1.5">
                    {[1, 2, 3, 4, 5].map((idx) => (
                        <div
                            key={idx}
                            className="rounded-full h-full transition-all duration-500"
                            style={{
                                background: idx <= (biasStrength / 2) ? (biasLabel === 'BULLISH' ? '#4ade80' : '#f87171') : 'rgba(255,255,255,0.05)',
                                opacity: idx <= (biasStrength / 2) ? 1 - (idx * 0.1) : 1
                            }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

export function LiquidityPanel({ data }: { data: LiveMarketData | null }) {
    const totalOi = (((data as any)?.analytics?.total_call_oi || 0) + ((data as any)?.analytics?.total_put_oi || 0));
    const oiChange = ((data as any)?.analytics?.oi_change_24h ?? 0);
    const volume = ((data as any)?.analytics?.total_volume || 0);
    const pressure = ((data as any)?.analytics?.liquidity_pressure) || 0;

    return (
        <div
            className="trading-panel h-full"
            onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = CARD_HOVER_BORDER;
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
            }}
        >
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Market Liquidity</SectionLabel>
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-blue-500/20 bg-blue-500/5">
                    <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400 capitalize">POOL A</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-6">
                {[
                    { label: 'Open Interest', value: totalOi.toLocaleString(), color: '#fff' },
                    { label: 'OI Change', value: `${oiChange > 0 ? '+' : ''}${oiChange.toFixed(0)}`, color: oiChange > 0 ? '#4ade80' : '#f87171' },
                ].map(({ label, value, color }) => (
                    <div
                        key={label}
                        className="rounded-xl p-3 flex flex-col gap-1 transition-all hover:bg-white/5"
                        style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
                    >
                        <span className="text-[9px] font-bold font-mono tracking-widest text-slate-500 uppercase">{label}</span>
                        <span className="text-[12px] font-bold font-mono tracking-tight tabular-nums" style={{ color }}>{value}</span>
                    </div>
                ))}
            </div>

            {/* Pressure Meter */}
            <div className="mt-auto">
                <div className="flex items-center justify-between mb-3 px-1">
                    <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase text-xs">Liquidity Pressure</span>
                    <span className="text-[12px] font-bold font-mono text-white tabular-nums">
                        {(pressure * 100).toFixed(1)}%
                    </span>
                </div>

                <div className="relative h-2 rounded-full overflow-hidden bg-white/5 border border-white/5">
                    <div
                        className="absolute inset-0 transition-all duration-1000 ease-out"
                        style={{
                            width: `${Math.min(100, pressure * 100)}%`,
                            background: 'linear-gradient(90deg, #4ade80, #fb923c, #f87171)',
                            boxShadow: '0 0 12px rgba(251,146,60,0.2)'
                        }}
                    />
                </div>

                <div className="flex justify-between mt-2 px-1">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-green-500/50 uppercase">LIQUID</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-red-500/50 uppercase">CONGESTED</span>
                </div>
            </div>
        </div>
    );
}

export function SmartMoneyAndLiquidity({ data, isSnapshotMode }: SmartMoneyAndLiquidityProps) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 h-full">
            <SmartMoneyPanel data={data} isSnapshotMode={isSnapshotMode} />
            <LiquidityPanel data={data} />
        </div>
    );
}

