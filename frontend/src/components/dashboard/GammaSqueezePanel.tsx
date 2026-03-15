"use client";
import React from 'react';
import { Zap, TrendingUp, Activity, Target } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface GammaSqueezePanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function GammaSqueezePanel() {
    // Law 7: Granular Store Subscriptions with null-safe pattern
    const regime        = useWSStore(s => s.regime         ?? 'RANGING')
    const bias          = useWSStore(s => s.bias           ?? 'NEUTRAL')
    const gammaAnalysis = useWSStore(s => s.gammaAnalysis  ?? {})
    const keyLevels     = useWSStore(s => s.keyLevels      ?? {})
    const lastUpdate    = useWSStore(s => s.lastUpdate)
    const hasData       = lastUpdate > 0

    // Extract gamma-related data from available fields
    const netGex        = gammaAnalysis?.net_gex    ?? 0
    const gexRegime     = (gammaAnalysis?.regime?.split(' ')[0]) ?? 'UNKNOWN'
    const flipLevel     = gammaAnalysis?.flip_level ?? 0
    const callWall      = keyLevels?.call_wall     ?? 0
    const putWall       = keyLevels?.put_wall      ?? 0

    // Simple gamma squeeze detection
    const squeezeDetected = Math.abs(netGex) > 1000000000 // 1B GEX threshold
    const squeezeDirection = netGex > 0 ? 'CALL' : 'PUT'
    const squeezeIntensity = Math.min(Math.abs(netGex) / 1000000000, 1.0)

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Gamma Squeeze</SectionLabel>
                    <SkeletonPulse className="w-20 h-5" />
                </div>
                <div className="space-y-6">
                    <SkeletonPulse className="w-full h-20" />
                    <SkeletonPulse className="w-full h-24" />
                </div>
            </div>
        );
    }

    const getPressureColor = (p: number) => {
        if (p > 0.75) return '#f87171';
        if (p > 0.50) return '#fb923c';
        return '#4ade80';
    };

    const pressureColor = getPressureColor(squeezeIntensity);
    const formatGex = (val: number) => {
        const abs = Math.abs(val);
        if (abs >= 1e6) return `${(val / 1e6).toFixed(2)}M`;
        if (abs >= 1e3) return `${(val / 1e3).toFixed(1)}K`;
        return val.toFixed(0);
    };

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Gamma Squeeze</SectionLabel>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/20 bg-purple-500/5">
                    <Zap size={12} className="text-purple-400" />
                    <span className="text-[10px] font-black font-mono tracking-widest text-purple-400 uppercase">GEX Engine</span>
                </div>
            </div>

            {/* Hedging Intensity */}
            <div className="mb-6 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Squeeze Intensity</span>
                    <span className="text-xl font-black font-mono" style={{ color: pressureColor }}>{(squeezeIntensity * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${squeezeIntensity * 100}%`, 
                            background: `linear-gradient(90deg, transparent, ${pressureColor})` 
                        }} 
                    />
                </div>
            </div>

            {/* GEX Metrics Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Net GEX</div>
                    <div className="text-sm font-black font-mono tabular-nums" style={{ color: netGex >= 0 ? '#4ade80' : '#f87171' }}>
                        {formatGex(netGex)}
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Flip Anchor</div>
                    <div className="text-sm font-black font-mono tabular-nums text-blue-400">
                        {flipLevel > 0 ? `₹${flipLevel.toLocaleString()}` : '—'}
                    </div>
                </div>
            </div>

            {/* Squeeze Probability */}
            <div className="mb-6 p-4 rounded-xl bg-purple-500/[0.03] border border-purple-500/10">
                <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold font-mono text-purple-400 uppercase tracking-widest">Squeeze Risk</span>
                    <span className="text-lg font-black font-mono text-white">{(squeezeIntensity * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full bg-purple-500 transition-all duration-1000" 
                        style={{ width: `${squeezeIntensity * 100}%` }} 
                    />
                </div>
            </div>

            {/* Regime Context */}
            <div className="mt-auto pt-6 border-t border-white/5">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Activity size={12} className="text-slate-500" />
                        <span className="text-[9px] font-bold font-mono text-slate-500 uppercase">Structural Regime</span>
                    </div>
                    <span className={`text-[10px] font-black font-mono px-2 py-0.5 rounded ${gexRegime.includes('SHORT') ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'}`}>
                        {gexRegime}
                    </span>
                </div>
            </div>
        </div>
    );
}

export default React.memo(GammaSqueezePanel);
