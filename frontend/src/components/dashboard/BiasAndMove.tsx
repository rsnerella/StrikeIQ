"use client";
import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface BiasAndMoveProps {
    data: LiveMarketData | null;
    isSnapshotMode: boolean;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function BiasPanel() {
    // Law 7: Granular Store Subscriptions
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    
    // v5.0 Bias state
    const biasLabel = analysis?.bias || 'NEUTRAL';
    const biasScore = analysis?.bias_strength || 0;

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Market Bias</SectionLabel>
                    <SkeletonPulse className="w-16 h-5" />
                </div>
                <div className="space-y-4">
                    <SkeletonPulse className="w-full h-16" />
                    <SkeletonPulse className="w-full h-12" />
                </div>
            </div>
        );
    }

    const isBullish = biasLabel === 'BULLISH';
    const isBearish = biasLabel === 'BEARISH';
    const configColor = isBullish ? '#4ade80' : isBearish ? '#f87171' : '#94a3b8';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Directional Bias</SectionLabel>
                <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border border-white/10 bg-white/5`}>
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: configColor }} />
                    <span className="text-[10px] font-black font-mono tracking-widest uppercase" style={{ color: configColor }}>{biasLabel}</span>
                </div>
            </div>

            <div className="flex-grow flex flex-col justify-center gap-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="flex justify-between items-center mb-3">
                         <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Strength Matrix</span>
                         <span className="text-lg font-black font-mono tabular-nums text-white">{(biasScore * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                         <div 
                            className="h-full transition-all duration-1000" 
                            style={{ 
                                width: `${biasScore * 100}%`, 
                                background: `linear-gradient(90deg, transparent, ${configColor})` 
                            }} 
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                        <div className="text-[8px] font-bold font-mono text-slate-600 uppercase mb-1">Conviction</div>
                        <div className="text-[10px] font-black font-mono text-white/80 uppercase">
                            {biasScore > 0.8 ? 'INSTITUTIONAL' : biasScore > 0.5 ? 'STRUCTURAL' : 'NOISE'}
                        </div>
                    </div>
                    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                        <div className="text-[8px] font-bold font-mono text-slate-600 uppercase mb-1">Flow Signal</div>
                        <div className="text-[10px] font-black font-mono text-white/80 uppercase">
                            {isBullish ? 'AGGRESSIVE BUY' : isBearish ? 'AGGRESSIVE SELL' : 'NEUTRAL'}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export function ExpectedMovePanel() {
    const aiReady = useWSStore(s => s.aiReady);
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    const spot = useWSStore(s => s.spot);
    const analysis = useWSStore(s => s.chartAnalysis);
    
    const vol = analysis?.volatility_state;
    const expectedMove = vol?.expected_move || 0;
    const breachProb = vol?.breach_probability || 0;

    if (!hasData || spot === 0) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <SectionLabel>Expected Move (1σ)</SectionLabel>
                 <div className="mt-8 space-y-6">
                    <SkeletonPulse className="w-full h-12" />
                    <SkeletonPulse className="w-full h-16" />
                 </div>
            </div>
        );
    }

    const lower = spot - expectedMove;
    const upper = spot + expectedMove;

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Probabilistic Range (1σ)</SectionLabel>
                <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">
                        Exp Move: ₹{expectedMove.toFixed(1)}
                    </span>
                </div>
            </div>

            <div className="flex-grow flex flex-col justify-center">
                <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="p-4 rounded-xl bg-red-500/[0.03] border border-red-500/10">
                        <div className="text-[8px] font-bold font-mono text-red-400/60 uppercase mb-1">Lower Deviation</div>
                        <div className="text-xl font-black font-mono tabular-nums text-red-400">₹{typeof lower === 'number' && lower > 0 ? lower.toLocaleString() : '—'}</div>
                    </div>
                    <div className="p-4 rounded-xl bg-green-500/[0.03] border border-green-500/10">
                        <div className="text-[8px] font-bold font-mono text-green-400/60 uppercase mb-1">Upper Deviation</div>
                        <div className="text-xl font-black font-mono tabular-nums text-green-400">₹{typeof upper === 'number' && upper > 0 ? upper.toLocaleString() : '—'}</div>
                    </div>
                </div>

                {/* Spot Progress Visual */}
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 mb-6">
                    <div className="flex justify-between items-center mb-3">
                        <span className="text-[9px] font-bold font-mono text-slate-500 uppercase">Atmospheric Spot Position</span>
                        <span className="text-xs font-black font-mono text-white">₹{typeof spot === 'number' && spot > 0 ? spot.toLocaleString() : '—'}</span>
                    </div>
                    <div className="relative h-1 w-full bg-white/5 rounded-full">
                         <div className="absolute top-1/2 left-1/2 -translate-y-1/2 w-0.5 h-3 bg-white/20" />
                         <div 
                            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_10px_#3b82f6]" 
                            style={{ left: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                </div>
            </div>

            {/* Breach Risk */}
            <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <AlertTriangle size={12} className={breachProb > 0.4 ? 'text-orange-400 animate-pulse' : 'text-slate-600'} />
                    <span className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-tighter">Expansion Risk Factor</span>
                </div>
                <span className="text-[12px] font-black font-mono tabular-nums" style={{ color: breachProb > 0.4 ? '#fb923c' : '#4ade80' }}>
                    {(breachProb * 100).toFixed(0)}%
                </span>
            </div>
        </div>
    );
}

// Separate components exported individually for maximum layout flexibility

