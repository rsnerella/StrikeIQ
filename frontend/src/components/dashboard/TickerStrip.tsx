"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Activity, Zap, AlertTriangle, ShieldCheck } from 'lucide-react';
import { useWSStore } from '../../core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function TickerStrip({ symbol }: { symbol: string }) {
    // Law 7: Granular Store Subscriptions
    const spot = useWSStore(s => s.spotPrice);
    const effectiveSpot = spot || 0;
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    
    // Direct selectors with fallbacks
    const changePct = useWSStore(s => s.technicals?.change_pct ?? 0);
    const changePositive = changePct >= 0;
    const earlyWarnings = useWSStore(s => s.earlyWarnings) || [];
    const bias = useWSStore(s => s.bias ?? 'NEUTRAL');
    const regime = useWSStore(s => s.regime ?? 'RANGING');
    const aiReady = useWSStore(s => s.aiReady);

    return (
        <div
            id="section-dashboard"
            className="trading-panel scroll-mt-20 overflow-hidden relative group p-4 sm:p-6"
        >
            {/* Real-time status line */}
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />

            <div className="flex flex-wrap items-center justify-between gap-8 relative z-10">
                {/* Left: Identity & Price */}
                <div className="flex items-center gap-8">
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-500 uppercase">ASSET</span>
                            <span className="flex h-1.5 w-1.5 rounded-full bg-green-400 shadow-[0_0_8px_#4ade80]" />
                        </div>
                        <span className="text-2xl font-black tracking-tighter text-white font-sans flex items-baseline">
                            {symbol}<span className="text-blue-400/50 text-sm ml-1">.IDX</span>
                        </span>
                    </div>

                    <div className="h-10 w-px bg-white/10" />

                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-cyan-500/60 uppercase mb-1">Institutional Spot</span>
                        <div className="flex items-baseline gap-4">
                            <span className="text-4xl font-black tabular-nums tracking-tighter text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                                {effectiveSpot > 0 
                                    ? effectiveSpot.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) 
                                    : <SkeletonPulse className="w-32 h-10" />}
                            </span>
                            {effectiveSpot > 0 && (
                                <div className={`flex items-center gap-1 text-[13px] font-bold font-mono px-2 py-0.5 rounded-md ${changePositive ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                    {changePositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                    {changePct !== 0 ? `${changePositive ? '+' : ''}${changePct.toFixed(2)}%` : '0.00%'}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Center: Institutional Warnings Ticker (Law 5 Compliance) */}
                <div className="flex-grow max-w-2xl px-8 hidden xl:block">
                    <div className="h-14 bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden flex items-center px-4 gap-4 relative">
                        <div className="flex items-center gap-2 text-yellow-500 bg-yellow-500/10 self-stretch px-3 border-r border-white/5">
                            <AlertTriangle size={14} className="animate-pulse" />
                            <span className="text-[9px] font-black font-mono tracking-widest">ALERTS</span>
                        </div>
                        
                        <div className="flex-grow overflow-hidden relative h-full">
                            <div className="absolute inset-0 flex items-center">
                                {earlyWarnings.length > 0 ? (
                                    <div className="animate-[ticker_30s_linear_infinite] whitespace-nowrap flex gap-12 items-center">
                                        {earlyWarnings.map((w: any, i: number) => (
                                            <div key={i} className="flex items-center gap-2">
                                                <div className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                                                <span className="text-[10px] font-bold font-mono text-slate-300 uppercase tracking-wide">
                                                    {typeof w === 'string' ? w : w.message || 'CAUTION: LIQUIDITY IMBALANCE DETECTED'}
                                                </span>
                                            </div>
                                        ))}
                                        {/* Duplicate for infinite loop */}
                                        {earlyWarnings.map((w: any, i: number) => (
                                            <div key={`dup-${i}`} className="flex items-center gap-2">
                                                <div className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                                                <span className="text-[10px] font-bold font-mono text-slate-300 uppercase tracking-wide">
                                                    {typeof w === 'string' ? w : w.message || 'CAUTION: LIQUIDITY IMBALANCE DETECTED'}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-3 opacity-40">
                                        <ShieldCheck size={14} className="text-green-500" />
                                        <span className="text-[10px] font-bold font-mono text-slate-400 tracking-widest uppercase">
    {bias} {regime} · {changePositive ? '+' : ''}{changePct.toFixed(2)}% · 
    {earlyWarnings.length > 0 ? `${earlyWarnings.length} WARNINGS` : 'CLEAR'}
</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right: Engine Status */}
                <div className="flex items-center gap-6">
                    <div className="hidden lg:flex flex-col items-end">
                        <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-500 uppercase mb-1">Compute Health</span>
                        <div className="flex items-center gap-4 text-slate-400 text-[11px] font-mono">
                            <div className="flex items-center gap-1.5">
                                <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
                                <span>L2:STREAMING</span>
                            </div>
                        </div>
                    </div>

                    <div className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-[11px] font-black font-mono tracking-[0.2em] border transition-all duration-500 ${
                        aiReady ? 'bg-green-500/10 border-green-500/30 text-green-400 shadow-[0_0_20px_rgba(34,197,94,0.1)]' : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                    }`}>
                        {aiReady ? <Zap size={14} className="fill-current" /> : <Activity size={14} className="animate-spin" />}
                        {aiReady ? 'STRIKE_AI:ACTIVE' : 'STRIKE_AI:INIT'}
                    </div>
                </div>
            </div>

            <style jsx>{`
                @keyframes ticker {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
            `}</style>
        </div>
    );
}
