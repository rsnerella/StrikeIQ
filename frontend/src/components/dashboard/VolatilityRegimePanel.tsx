"use client";
import React from 'react';
import { Activity, TrendingUp, AlertTriangle, BarChart3 } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface VolatilityRegimePanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function VolatilityRegimePanel() {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    const spot = useWSStore(s => s.spot);
    
    // v5.0 Volatility state
    const vol = analysis?.volatility_state;
    const regime = vol?.state || 'NORMAL';
    const iv = vol?.iv_atm || 0;
    const compression = vol?.compression || false;
    const breachProb = vol?.breach_probability || 0;
    const expectedMove = analysis?.expected_move?.[vol?.timeframe || '1h'] || 0;

    const hasData = lastUpdate > 0;
    if (!hasData || !analysis) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Volatility Intelligence</SectionLabel>
                    <SkeletonPulse className="w-24 h-6 rounded-full" />
                </div>
                <div className="space-y-6">
                    <SkeletonPulse className="w-full h-24" />
                    <SkeletonPulse className="w-full h-24" />
                </div>
            </div>
        );
    }

    const getRegimeDisplay = (r: string) => {
        switch (r.toLowerCase()) {
            case 'extreme': return { color: '#f87171', label: 'EXTREME', desc: 'SYSTEMIC VOLATILITY EXPLOSION DETECTED' };
            case 'elevated': return { color: '#fb923c', label: 'ELEVATED', desc: 'STRUCTURAL EXPANSION IN PROGRESS' };
            case 'low': return { color: '#60a5fa', label: 'LOW', desc: 'COMPRESSION / MEAN REVERSION REGIME' };
            default: return { color: '#4ade80', label: 'NORMAL', desc: 'STABLE INSTITUTIONAL FLOW CONDITIONS' };
        }
    };

    const rd = getRegimeDisplay(regime);
    const upperLimit = spot + expectedMove;
    const lowerLimit = spot - expectedMove;
    const movePct = spot > 0 ? ((expectedMove / spot) * 100).toFixed(2) : '0.00';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Volatility Matrix</SectionLabel>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5">
                    <Activity size={12} className="text-blue-400" />
                    <span className="text-[10px] font-black font-mono tracking-widest text-blue-400 uppercase">Real-Time σ</span>
                </div>
            </div>

            {/* Current Regime */}
            <div className="mb-6 p-4 rounded-xl bg-white/[0.02] border border-white/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-3 opacity-10">
                    <Activity size={40} style={{ color: rd.color }} />
                </div>
                <div className="text-[9px] font-bold font-mono text-slate-500 uppercase mb-2">Implying Regime</div>
                <div className="text-2xl font-black font-mono mb-1" style={{ color: rd.color }}>{rd.label}</div>
                <div className="text-[10px] font-mono text-slate-400 italic">"{rd.desc}"</div>
            </div>

            {/* Expected Move */}
            <div className="mb-6 space-y-4">
                <div className="flex justify-between items-end">
                    <div className="flex flex-col gap-1">
                        <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Expected Move (1σ)</span>
                        <span className="text-[11px] font-mono text-slate-400">Timeframe: {vol?.timeframe || '1h'}</span>
                    </div>
                    <div className="text-right">
                        <div className="text-xl font-black font-mono text-white tabular-nums">±{expectedMove.toFixed(1)}</div>
                        <div className="text-[9px] font-bold font-mono text-cyan-400">{movePct}% Deviation</div>
                    </div>
                </div>

                <div className="relative h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
                    <div className="absolute inset-0 opacity-20" style={{ background: `linear-gradient(90deg, #f87171, ${rd.color}, #f87171)` }} />
                    <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-1 bg-white shadow-[0_0_10px_white]" />
                </div>

                <div className="flex justify-between items-center text-[10px] font-bold font-mono text-slate-500">
                    <div className="flex flex-col">
                        <span>LOWER BOUND</span>
                        <span className="text-red-400">₹{lowerLimit.toLocaleString()}</span>
                    </div>
                    <div className="flex flex-col items-end">
                        <span>UPPER BOUND</span>
                        <span className="text-green-400">₹{upperLimit.toLocaleString()}</span>
                    </div>
                </div>
            </div>

            {/* Expansion Probability */}
            <div className="mt-auto pt-6 border-t border-white/5">
                 <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Expansion Risk</span>
                    <span className={`text-[11px] font-black font-mono ${breachProb > 50 ? 'text-red-400' : 'text-blue-400'}`}>
                        {breachProb.toFixed(1)}%
                    </span>
                 </div>
                 <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${breachProb}%`, 
                            background: breachProb > 50 ? '#f87171' : '#60a5fa' 
                        }} 
                    />
                 </div>
            </div>
        </div>
    );
}

export default React.memo(VolatilityRegimePanel);


