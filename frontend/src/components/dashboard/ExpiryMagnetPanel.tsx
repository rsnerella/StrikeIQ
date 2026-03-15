"use client";
import React from 'react';
import { Target, Magnet, TrendingUp, Calendar, Activity } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface ExpiryMagnetPanelProps {
    data: LiveMarketData | null;
}

import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function ExpiryMagnetPanel() {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    const spot = useWSStore(s => s.spot);
    
    // v5.0 Expiry Magnet state
    const mag = analysis?.expiry_magnet;
    const strike = mag?.magnet_strike || 0;
    const pinProb = mag?.pin_probability || 0;
    const daysLeft = mag?.days_to_expiry || 0;
    const dist = strike > 0 ? strike - spot : 0;

    const hasData = lastUpdate > 0;
    if (!hasData || !analysis) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Expiry Magnet</SectionLabel>
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

    const urgencyColor = daysLeft <= 1 ? '#f87171' : daysLeft <= 3 ? '#fb923c' : '#4ade80';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            <div className="flex items-center justify-between mb-6">
                <SectionLabel>Gamma Magnet</SectionLabel>
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5`}>
                     <Target size={12} className="text-blue-400" />
                    <span className="text-[10px] font-black font-mono tracking-widest text-blue-400 uppercase">Pinning Risk</span>
                </div>
            </div>

            {/* Strike Target Block */}
            <div className="mb-6 p-4 rounded-xl bg-blue-500/[0.03] border border-blue-500/10">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[9px] font-bold font-mono text-blue-400 uppercase tracking-widest">Target Objective</span>
                    <span className="text-xl font-black font-mono text-white tabular-nums tracking-tighter">
                        ₹{strike.toLocaleString()}
                    </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 italic">
                    <Magnet size={10} className="animate-pulse" />
                    <span>Atmospheric Attraction: {Math.abs(dist).toFixed(1)} PTS</span>
                </div>
            </div>

            {/* Probability Block */}
            <div className="mb-6 rounded-xl p-4 bg-white/[0.02] border border-white/5">
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Pin Probability</span>
                    <span className="text-sm font-black font-mono" style={{ color: pinProb > 60 ? '#f87171' : '#4ade80' }}>
                        {(pinProb * 100).toFixed(0)}%
                    </span>
                </div>
                <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full bg-blue-500 transition-all duration-1000" 
                        style={{ width: `${pinProb * 100}%` }} 
                    />
                </div>
            </div>

            {/* Grid Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Days To Exp</div>
                    <div className="text-lg font-black font-mono tabular-nums" style={{ color: urgencyColor }}>
                        {daysLeft}d
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                    <div className="text-[8px] font-bold font-mono text-slate-500 uppercase mb-2">Force Bias</div>
                    <div className="text-sm font-black font-mono text-white uppercase tracking-tighter">
                        {dist > 0 ? 'PULL UP' : 'PULL DOWN'}
                    </div>
                </div>
            </div>

            {/* Layout Bottom */}
            <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full animate-pulse`} style={{ backgroundColor: urgencyColor }} />
                    <span className="text-[9px] font-bold font-mono text-slate-600 uppercase">System Ready</span>
                </div>
                <span className="text-[10px] font-black font-mono text-slate-400 uppercase tracking-widest">
                    {pinProb > 0.8 ? 'HIGH PIN ALERT' : 'ORBITAL DRIFT'}
                </span>
            </div>
        </div>
    );
}

export default React.memo(ExpiryMagnetPanel);
