"use client";
import React from 'react';
import { AlertTriangle, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface TrapDetectionPanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function TrapDetectionPanel() {
    // Law 7: Granular Store Subscriptions with null-safe pattern
    const regime       = useWSStore(s => s.regime        ?? 'RANGING')
    const bias         = useWSStore(s => s.bias          ?? 'NEUTRAL')
    const keyLevels    = useWSStore(s => s.keyLevels     ?? {})
    const technicals   = useWSStore(s => s.technicals    ?? {})
    const lastUpdate   = useWSStore(s => s.lastUpdate)
    const hasData      = lastUpdate > 0

    // Extract trap-related data from available fields
    const callWall    = keyLevels?.call_wall  ?? 0
    const putWall     = keyLevels?.put_wall   ?? 0
    const maxPain     = keyLevels?.max_pain   ?? 0
    const rsi         = technicals?.rsi        ?? 0
    const momentum    = technicals?.momentum_15m ?? 0

    // Simple trap detection logic
    const trapDetected = (rsi > 70 || rsi < 30) && momentum !== 0
    const trapDirection = rsi > 70 ? 'BEARISH' : rsi < 30 ? 'BULLISH' : 'NEUTRAL'
    const trapStrength = Math.abs((rsi - 50) / 50)

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Trap Detection</SectionLabel>
                    <SkeletonPulse className="w-20 h-5" />
                </div>
                <div className="space-y-4">
                    <SkeletonPulse className="w-full h-20" />
                    <div className="grid grid-cols-2 gap-4">
                        <SkeletonPulse className="h-24" />
                        <SkeletonPulse className="h-24" />
                    </div>
                </div>
            </div>
        );
    }

    const getTrapColor = (dir: string) => {
        if (dir === 'BULLISH') return '#4ade80'; // Bullish Trap = Bearish Bias
        if (dir === 'BEARISH') return '#f87171'; // Bearish Trap = Bullish Bias
        return '#94a3b8';
    };

    const trapColor = getTrapColor(trapDirection);
    const trapProbability = trapDetected ? trapStrength * 100 : 0
    const riskLevel = trapProbability > 75 ? 'CRITICAL' : trapProbability > 50 ? 'HIGH' : trapProbability > 25 ? 'MODERATE' : 'STABLE';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Liquidity Traps</SectionLabel>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-orange-500/20 bg-orange-500/5">
                    <AlertTriangle size={12} className="text-orange-400" />
                    <span className="text-[10px] font-black font-mono tracking-widest text-orange-400 uppercase">Detection Active</span>
                </div>
            </div>

            {/* Probability Block */}
            <div className="mb-6 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Fakeout Probability</span>
                    <span className="text-xl font-black font-mono" style={{ color: trapColor }}>{trapProbability.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${trapProbability}%`, 
                            background: `linear-gradient(90deg, transparent, ${trapColor})` 
                        }} 
                    />
                </div>
                <div className="flex justify-between mt-2 text-[8px] font-bold font-mono text-slate-600">
                    <span>{riskLevel} RISK</span>
                    <span>INTENSITY: {(trapStrength * 100).toFixed(0)}%</span>
                </div>
            </div>

            {/* Grid Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Trap Core</div>
                    <div className="text-sm font-black font-mono tracking-tight" style={{ color: trapColor }}>
                        {trapDirection} FAKEOUT
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Anchor Level</div>
                    <div className="text-sm font-black font-mono tabular-nums">
                        {callWall > 0 ? `₹${callWall.toLocaleString()}` : 'SCANNING...'}
                    </div>
                </div>
            </div>

            {/* Institutional Context */}
            <div className="mt-auto pt-6 border-t border-white/5">
                <div className="flex gap-4 items-center">
                    <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                        <Users size={16} className="text-slate-400" />
                    </div>
                    <div className="flex-1">
                        <div className="text-[9px] font-bold font-mono text-slate-500 uppercase">Order Flow Insight</div>
                        <div className="text-[11px] font-mono text-slate-300 italic leading-relaxed">
                            {trapDirection === 'BULLISH' 
                                ? "Institutions absorbing aggressive buying. Breakout likely exhausted."
                                : trapDirection === 'BEARISH'
                                ? "Retail panic selling being absorbed. Structural base forming."
                                : "No significant institutional trap patterns detected in this window."
                            }
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default React.memo(TrapDetectionPanel);
