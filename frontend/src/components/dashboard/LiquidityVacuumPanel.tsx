"use client";
import React from 'react';
import { Wind, AlertTriangle, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface LiquidityVacuumPanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function LiquidityVacuumPanel() {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    const spot = useWSStore(s => s.spot);
    
    // v5.0 Liquidity Vacuum state
    const liq = analysis?.liquidity_analysis;
    const zoneStart = liq?.vacuum_start || 0;
    const zoneEnd = liq?.vacuum_end || 0;
    const width = zoneEnd > zoneStart ? zoneEnd - zoneStart : 0;
    const depth = liq?.book_depth || 0.5;
    const probability = liq?.expansion_probability || 0.3;

    const hasData = lastUpdate > 0;
    if (!hasData || !analysis) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Liquidity Vacuum</SectionLabel>
                    <SkeletonPulse className="w-20 h-5" />
                </div>
                <div className="space-y-6">
                    <SkeletonPulse className="w-full h-24" />
                    <div className="grid grid-cols-2 gap-4">
                        <SkeletonPulse className="h-20" />
                        <SkeletonPulse className="h-20" />
                    </div>
                </div>
            </div>
        );
    }

    const isInVacuum = spot >= zoneStart && spot <= zoneEnd;
    const severityColor = depth < 0.3 ? '#f87171' : depth < 0.6 ? '#fb923c' : '#4ade80';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Liquidity Gaps</SectionLabel>
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full border border-orange-500/20 bg-orange-500/5`}>
                     <Wind size={12} className="text-orange-400" />
                    <span className="text-[10px] font-black font-mono tracking-widest text-orange-400 uppercase">Book Depth</span>
                </div>
            </div>

            {/* Expansion Risk Block */}
            <div className="mb-6 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Rapid Expansion</span>
                    <span className="text-xl font-black font-mono" style={{ color: probability > 60 ? '#f87171' : '#4ade80' }}>
                        {(probability * 100).toFixed(1)}%
                    </span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${probability * 100}%`, 
                            background: `linear-gradient(90deg, transparent, ${probability > 60 ? '#f87171' : '#4ade80'})` 
                        }} 
                    />
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Gap Width</div>
                    <div className="text-sm font-black font-mono tabular-nums text-white">
                        {width.toFixed(1)} <span className="text-[8px] text-slate-500">PTS</span>
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Book Depth</div>
                    <div className="text-sm font-black font-mono tabular-nums" style={{ color: severityColor }}>
                        {(depth * 100).toFixed(0)}%
                    </div>
                </div>
            </div>

            {/* Interactive Zone Snapshot */}
            <div className="mb-6 p-4 rounded-xl bg-orange-500/[0.03] border border-orange-500/10">
                <div className="text-[9px] font-bold font-mono text-orange-400 uppercase tracking-widest mb-3">Void Coordinates</div>
                <div className="flex justify-between items-center tabular-nums text-xs font-black font-mono">
                    <span className="text-slate-400">₹{zoneStart.toLocaleString()}</span>
                    <div className="flex-1 mx-4 h-[1px] bg-orange-500/20 relative">
                        {isInVacuum && <div className="absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-white border border-orange-500 shadow-[0_0_10px_#fff]" />}
                    </div>
                    <span className="text-slate-400">₹{zoneEnd.toLocaleString()}</span>
                </div>
            </div>

            {/* Alert Context */}
            <div className="mt-auto pt-6 border-t border-white/5">
                <div className="flex items-center justify-between">
                     <span className="text-[10px] font-black font-mono text-slate-500 uppercase tracking-tighter">Market Condition:</span>
                     <span className={`text-[10px] font-black font-mono px-2 py-0.5 rounded ${isInVacuum ? 'bg-red-500/10 text-red-400 animate-pulse' : 'bg-green-500/10 text-green-400'}`}>
                         {isInVacuum ? 'LOW DEPTH VOID' : 'CONTINUITY STABLE'}
                     </span>
                </div>
            </div>
        </div>
    );
}

export default React.memo(LiquidityVacuumPanel);
