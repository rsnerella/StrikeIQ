"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Target, Shield, Activity, Search } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function TradeSetupPanel() {
    // Law 7: Granular Store Subscriptions with null-safe pattern
    const regime       = useWSStore(s => s.regime        ?? 'RANGING')
    const bias         = useWSStore(s => s.bias          ?? 'NEUTRAL')
    const pcr          = useWSStore(s => s.pcr           ?? 0)
    const tradeSetup    = useWSStore(s => s.tradeSetup)    // NEW: Use separated tradeSetup
    const lastUpdate   = useWSStore(s => s.lastUpdate)
    const hasData      = lastUpdate > 0
    
    // Loading State (Law 2 & 7)
    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col justify-center items-center gap-4 opacity-60">
                <Search className="w-8 h-8 text-blue-500/50 animate-bounce" />
                <div className="flex flex-col items-center gap-2">
                    <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-blue-400 uppercase">
                        Initializing Market Data...
                    </span>
                    <div className="flex gap-1">
                        <SkeletonPulse className="w-2 h-2" />
                        <SkeletonPulse className="w-2 h-2" />
                        <SkeletonPulse className="w-2 h-2" />
                    </div>
                </div>
            </div>
        );
    }

    // NEW: Handle NO_TRADE case
    if (!tradeSetup || tradeSetup.action === "NO_TRADE") {
        return (
            <div className="trading-panel h-full flex flex-col justify-center items-center gap-4 opacity-60">
                <Shield className="w-8 h-8 text-slate-400/50" />
                <div className="flex flex-col items-center gap-2">
                    <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-400 uppercase">
                        No high conviction setup
                    </span>
                    <div className="text-[8px] font-mono text-slate-500 text-center">
                        Market conditions not favorable for trading
                    </div>
                </div>
            </div>
        );
    }

    const entryDisplay = tradeSetup?.entry > 0
      ? `₹${tradeSetup.entry.toFixed(2)}` 
      : '—'

    const slDisplay = tradeSetup?.stop_loss > 0
      ? `₹${tradeSetup.stop_loss.toFixed(2)}` 
      : '—'

    const targetDisplay = tradeSetup?.target > 0
      ? `₹${tradeSetup.target.toFixed(2)}` 
      : '—'

    const directionDisplay = tradeSetup?.action ?? 'NEUTRAL'
    const isBullish = directionDisplay.includes('CE') || directionDisplay.includes('BULLISH');
    const isBearish = directionDisplay.includes('PE') || directionDisplay.includes('BEARISH');

    const reasonDisplay = tradeSetup?.execution_reasoning?.[0]
      ?? (hasData
            ? 'No high-conviction setup at current levels'
            : '—')

    // Directional Styling
    const directionStyle = isBullish 
        ? { color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)', icon: <TrendingUp className="w-4 h-4" /> }
        : isBearish 
        ? { color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)', icon: <TrendingDown className="w-4 h-4" /> }
        : { color: '#94a3b8', bgColor: 'rgba(148,163,184,0.08)', borderColor: 'rgba(148,163,184,0.18)', icon: <Activity className="w-4 h-4" /> };

    // Risk/Reward (Law 2 Safeguard)
    const risk = Math.abs((tradeSetup?.entry || 0) - (tradeSetup?.stop_loss || 0));
    const reward = Math.abs((tradeSetup?.target || 0) - (tradeSetup?.entry || 0));
    const rrRatio = risk > 0 ? (reward / risk).toFixed(2) : '—';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Institutional Trade Setup</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: directionStyle.bgColor,
                            border: `1px solid ${directionStyle.borderColor}`,
                            color: directionStyle.color,
                            boxShadow: `0 0 10px ${directionStyle.color}15`
                        }}
                    >
                        {directionStyle.icon}
                        {tradeSetup?.strike ? `${tradeSetup.action} ${tradeSetup.strike}` : directionDisplay}
                    </span>
                </div>
            </div>

            {/* Market Context Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/3 border border-white/5 bg-white/[0.02]">
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">Regime</div>
                    <div className="text-[14px] font-bold font-mono text-cyan-400 uppercase truncate">
                        {regime.replace(/_/g, ' ')}
                    </div>
                </div>

                <div className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/3 border border-white/5 bg-white/[0.02]">
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">Market Bias</div>
                    <div className={`text-[14px] font-bold font-mono tracking-tight uppercase truncate ${isBullish ? 'text-green-400' : isBearish ? 'text-red-400' : 'text-slate-300'}`}>
                        {bias}
                    </div>
                </div>
            </div>

            {/* Trade Levels Section */}
            <div className="space-y-4 mb-6 flex-grow">
                {/* Entry Zone */}
                <div className="rounded-xl p-4 border border-white/10 bg-blue-500/[0.03]">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Target className="w-3.5 h-3.5 text-blue-400" />
                            <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-400">Optimal Entry</span>
                        </div>
                        <span className="text-[16px] font-bold font-mono tracking-tight text-blue-400 tabular-nums">
                            {entryDisplay}
                        </span>
                    </div>
                </div>

                {/* Targets & SL */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl p-4 border border-green-500/10 bg-green-500/[0.03]">
                        <div className="text-[9px] font-bold font-mono text-green-500/70 uppercase mb-1">Target</div>
                        <div className="text-[14px] font-bold font-mono text-green-400">
                            {targetDisplay}
                        </div>
                        <div className="text-[8px] font-mono text-green-500/50 mt-1">{rrRatio} RR</div>
                    </div>
                    <div className="rounded-xl p-4 border border-red-500/10 bg-red-500/[0.03]">
                        <div className="text-[9px] font-bold font-mono text-red-500/70 uppercase mb-1">Stop Loss</div>
                        <div className="text-[14px] font-bold font-mono text-red-500">
                            {slDisplay}
                        </div>
                    </div>
                </div>
            </div>

            {/* Reason Footer (Law 1 Purge) */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="text-[10px] font-medium font-mono tracking-tight p-3 rounded-lg bg-white/5 border border-white/10 text-slate-300 leading-relaxed min-h-[60px]">
                    {reasonDisplay}
                </div>
            </div>
        </div>
    );
}

export default React.memo(TradeSetupPanel);

