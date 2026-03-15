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

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function SmartMoneyPanel() {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    
    // v5.0 Smart Money state
    const strength = analysis?.bias_strength || 0;
    const confidence = analysis?.confidence || 0;

    const hasData = lastUpdate > 0;
    if (!hasData || !analysis) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Institutional Flow</SectionLabel>
                    <SkeletonPulse className="w-16 h-5" />
                </div>
                <div className="space-y-4">
                    <SkeletonPulse className="w-full h-12" />
                    <SkeletonPulse className="w-full h-12" />
                    <SkeletonPulse className="w-full h-12" />
                </div>
            </div>
        );
    }

    const flowColor = analysis?.bias === 'BULLISH' ? '#4ade80' : analysis?.bias === 'BEARISH' ? '#f87171' : '#94a3b8';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Smart Money Signal</SectionLabel>
                <div className="px-2.5 py-1 rounded-full border border-blue-500/20 bg-blue-500/5">
                    <span className="text-[9px] font-black font-mono tracking-widest text-blue-400 uppercase">Alpha v5.0</span>
                </div>
            </div>

            <div className="space-y-3 mb-6">
                {[
                    { label: 'Delta Regime', val: analysis?.bias || 'NEUTRAL', color: flowColor },
                    { label: 'Signal Vector', val: `${(strength * 10).toFixed(1)}x`, color: '#fff' },
                    { label: 'Reliability', val: `${(confidence * 100).toFixed(0)}%`, color: confidence > 0.7 ? '#4ade80' : '#fb923c' }
                ].map((m, i) => (
                    <div key={i} className="flex justify-between items-center p-3 rounded-xl bg-white/[0.02] border border-white/5">
                        <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">{m.label}</span>
                        <span className="text-xs font-black font-mono tracking-tighter" style={{ color: m.color }}>{m.val}</span>
                    </div>
                ))}
            </div>

            {/* Visual Flux */}
            <div className="mt-auto">
                <div className="text-[8px] font-bold font-mono text-slate-600 uppercase mb-2 tracking-[0.2em]">Concentration Spectrum</div>
                <div className="flex gap-1 h-1">
                    {[...Array(10)].map((_, i) => (
                        <div 
                            key={i} 
                            className="flex-1 rounded-full transition-all duration-700"
                            style={{ 
                                backgroundColor: i / 10 < strength ? flowColor : 'rgba(255,255,255,0.05)',
                                opacity: i / 10 < strength ? 1 - (i * 0.05) : 1
                            }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

export function LiquidityPanel() {
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    
    // v5.0 Liquidity state
    const liq = analysis?.liquidity_analysis;
    const totalOi = (liq?.total_call_oi || 0) + (liq?.total_put_oi || 0);
    const oiChange = liq?.oi_change_24h || 0;
    const pressure = liq?.liquidity_pressure || 0;

    const hasData = lastUpdate > 0;
    if (!hasData || !analysis) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <SectionLabel>Market Depth</SectionLabel>
                 <div className="mt-8 grid grid-cols-2 gap-4">
                    <SkeletonPulse className="h-16" />
                    <SkeletonPulse className="h-16" />
                 </div>
                 <div className="mt-8">
                    <SkeletonPulse className="w-full h-8" />
                 </div>
            </div>
        );
    }

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Pool Liquidity</SectionLabel>
                <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                    <span className="text-[9px] font-bold font-mono text-cyan-400 uppercase tracking-widest">Active Pool</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-6">
                 <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-1">Total OI</div>
                    <div className="text-sm font-black font-mono text-white tabular-nums">{(totalOi / 1000000).toFixed(1)}M</div>
                 </div>
                 <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-1">OI Δ 24H</div>
                    <div className="text-sm font-black font-mono tabular-nums" style={{ color: oiChange > 0 ? '#4ade80' : '#f87171' }}>
                        {oiChange > 0 ? '+' : ''}{(oiChange / 1000).toFixed(0)}k
                    </div>
                 </div>
            </div>

            {/* Viscous Pressure Visual */}
            <div className="mt-auto">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Dynamic Pressure</span>
                    <span className="text-xs font-black font-mono text-white">{(pressure * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/10">
                     <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${pressure * 100}%`, 
                            background: `linear-gradient(90deg, #4ade80, #fb923c, #f87171)` 
                        }} 
                    />
                </div>
                <div className="flex justify-between mt-2">
                    <span className="text-[8px] font-bold font-mono text-green-500/40 uppercase">Fluid</span>
                    <span className="text-[8px] font-bold font-mono text-red-500/40 uppercase">Viscous</span>
                </div>
            </div>
        </div>
    );
}

// Visual building blocks for the institutional dashboard

