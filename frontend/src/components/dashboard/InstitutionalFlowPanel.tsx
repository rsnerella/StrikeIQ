"use client";
import React from 'react';
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface InstitutionalFlowPanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function InstitutionalFlowPanel() {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    
    // v5.0 Flow state
    const flow = analysis?.flow_analysis;
    const callVelocity = flow?.call_velocity || 0;
    const putVelocity = flow?.put_velocity || 0;
    const direction = flow?.direction || 'NEUTRAL';
    const intent = flow?.intent_score || 0;
    const imbalance = flow?.imbalance || 0;

    const hasData = lastUpdate > 0;
    if (!hasData || !analysis) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Institutional Flow</SectionLabel>
                    <SkeletonPulse className="w-20 h-5" />
                </div>
                <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                        <SkeletonPulse className="h-20" />
                        <SkeletonPulse className="h-20" />
                    </div>
                    <SkeletonPulse className="w-full h-16" />
                </div>
            </div>
        );
    }

    const formatFlow = (val: number) => {
        const abs = Math.abs(val);
        if (abs >= 1e6) return `${(val / 1e6).toFixed(2)}M`;
        if (abs >= 1e3) return `${(val / 1e3).toFixed(1)}K`;
        return val.toFixed(0);
    };

    const total = Math.abs(callVelocity) + Math.abs(putVelocity);
    const callPct = total > 0 ? (Math.abs(callVelocity) / total) * 100 : 50;
    const putPct = total > 0 ? (Math.abs(putVelocity) / total) * 100 : 50;

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Institutional Flow</SectionLabel>
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5`}>
                     <div className="flex items-center gap-1.5">
                        {direction === 'BULLISH' ? <ArrowUpRight size={12} className="text-green-400" /> : direction === 'BEARISH' ? <ArrowDownRight size={12} className="text-red-400" /> : <Minus size={12} className="text-slate-400" />}
                        <span className="text-[10px] font-black font-mono tracking-widest text-white/80 uppercase">{direction}</span>
                    </div>
                </div>
            </div>

            {/* Velocity Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Call Velocity</div>
                    <div className="text-lg font-black font-mono tabular-nums tracking-tight text-green-400">
                        {formatFlow(callVelocity)}
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Put Velocity</div>
                    <div className="text-lg font-black font-mono tabular-nums tracking-tight text-red-400">
                        {formatFlow(putVelocity)}
                    </div>
                </div>
            </div>

            {/* Multi-Side Imbalance Bar */}
            <div className="mb-6 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Global Imbalance</span>
                    <span className="text-xs font-black font-mono tabular-nums" style={{ color: imbalance >= 0 ? '#4ade80' : '#f87171' }}>
                        {imbalance > 0 ? '+' : ''}{(imbalance * 100).toFixed(1)}%
                    </span>
                </div>
                <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden flex">
                     <div className="h-full bg-green-500 transition-all duration-700" style={{ width: `${callPct}%` }} />
                     <div className="h-full bg-red-500 transition-all duration-700" style={{ width: `${putPct}%` }} />
                </div>
            </div>

            {/* Strategic Intent */}
            <div className="mt-auto pt-4 border-t border-white/5">
                <div className="flex justify-between items-center">
                    <div className="flex flex-col">
                        <span className="text-[8px] font-bold font-mono text-slate-600 uppercase">Intent Intensity</span>
                        <div className="h-1 w-24 bg-white/5 mt-1 rounded-full overflow-hidden">
                             <div 
                                className="h-full bg-blue-500" 
                                style={{ width: `${intent}%`, boxShadow: '0 0 10px rgba(59,130,246,0.5)' }} 
                            />
                        </div>
                    </div>
                    <div className="text-right">
                        <span className="text-[14px] font-black font-mono text-white tracking-widest uppercase">
                            {intent >= 75 ? 'SURGE' : intent >= 50 ? 'STEADY' : 'LATENT'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
