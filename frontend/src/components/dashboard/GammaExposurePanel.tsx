"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface GammaExposurePanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function GammaExposurePanel() {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    const analysis = useWSStore(s => s.chartAnalysis);
    const spot = useWSStore(s => s.spot);
    
    // v5.0 Gamma Exposure state
    const gamma = analysis?.gamma_analysis;
    const netGamma = gamma?.net_gex || 0;
    const flip = gamma?.gex_flip || 0;
    const regime = gamma?.regime || 'NEUTRAL';
    const distToFlip = spot > 0 && flip > 0 ? spot - flip : 0;

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Gamma Exposure</SectionLabel>
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

    const formatGex = (val: number) => {
        const abs = Math.abs(val);
        if (abs >= 1e6) return `${(val / 1e6).toFixed(2)}M`;
        if (abs >= 1e3) return `${(val / 1e3).toFixed(1)}K`;
        return val.toFixed(0);
    };

    const isPositive = regime === 'POSITIVE_GAMMA';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>GEX Profile</SectionLabel>
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${isPositive ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                    <span className="relative flex h-1.5 w-1.5">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-70 ${isPositive ? 'bg-green-400' : 'bg-red-400'}`}></span>
                        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${isPositive ? 'bg-green-400' : 'bg-red-400'}`}></span>
                    </span>
                    <span className={`text-[10px] font-black font-mono tracking-widest uppercase ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                        {regime}
                    </span>
                </div>
            </div>

            {/* Core Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Net GEX</div>
                    <div className="text-xl font-black font-mono tabular-nums tracking-tight" style={{ color: isPositive ? '#4ade80' : '#f87171' }}>
                        {formatGex(netGamma)}
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Flip Level</div>
                    <div className="text-xl font-black font-mono tabular-nums tracking-tight text-white/90">
                        {flip > 0 ? flip.toLocaleString() : '—'}
                    </div>
                </div>
            </div>

            {/* Visual Flux Bar */}
            <div className="mb-6 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Flux Proximity</span>
                    <span className="text-xs font-black font-mono" style={{ color: distToFlip >= 0 ? '#4ade80' : '#f87171' }}>
                        {distToFlip > 0 ? '+' : ''}{distToFlip.toFixed(2)} PTS
                    </span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden flex">
                     <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${Math.min(100, (Math.abs(distToFlip) / (spot * 0.01)) * 100)}%`, 
                            background: `linear-gradient(90deg, transparent, ${distToFlip >= 0 ? '#4ade80' : '#f87171'})` 
                        }} 
                    />
                </div>
            </div>

            {/* Snapshot Indicator */}
            <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    <span className="text-[9px] font-bold font-mono text-slate-600 uppercase">Live Spot Flow</span>
                </div>
                <span className="text-xs font-black font-mono text-white tabular-nums tracking-wider uppercase">
                    ₹{typeof spot === 'number' && spot > 0 ? spot.toLocaleString() : '—'}
                </span>
            </div>
        </div>
    );
}
