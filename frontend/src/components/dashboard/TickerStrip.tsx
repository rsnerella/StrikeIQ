"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Activity, Zap } from 'lucide-react';
import { CARD } from './DashboardTypes';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface TickerStripProps {
    symbol: string;
    data: LiveMarketData | null;
    effectiveSpot: number | null;
    mode: string;
    modeLabel: string;
    modeColor: string;
}

export function TickerStrip({
    symbol,
    data,
    effectiveSpot,
    mode,
    modeLabel,
    modeColor
}: TickerStripProps) {
    const changePositive = (data?.change ?? 0) >= 0;
    const changePct = (data as any)?.change_percent ?? 0;
    const ltp = effectiveSpot ?? 0;

    return (
        <div
            id="section-dashboard"
            className="trading-panel scroll-mt-20 overflow-visible relative group"
            style={{
                padding: '16px 24px',
                borderColor: 'rgba(0, 229, 255, 0.15)',
                background: 'rgba(6, 9, 18, 0.85)'
            }}
        >
            {/* Global scanning line animation */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-[18px]">
                <div className="absolute top-0 left-[-100%] w-full h-[1px] bg-gradient-to-r from-transparent via-blue-400/30 to-transparent animate-[scan_3s_linear_infinite]" />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
                {/* Left: Identity & Price */}
                <div className="flex items-center gap-6">
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-500 uppercase">Instrument</span>
                            {mode === 'live' && (
                                <span className="flex h-1.5 w-1.5 rounded-full bg-green-400 shadow-[0_0_8px_#4ade80]" />
                            )}
                        </div>
                        <span className="text-2xl font-black tracking-tighter text-white font-sans">
                            {symbol}<span className="text-blue-400/50">.IDX</span>
                        </span>
                    </div>

                    <div className="h-10 w-px bg-white/5 mx-2" />

                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-500 uppercase mb-1">Last Traded Price</span>
                        <div className="flex items-baseline gap-3">
                            <span className="text-4xl font-black tabular-nums tracking-tighter text-white drop-shadow-2xl">
                                {ltp.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                            <div
                                className={`flex items-center gap-1 text-[13px] font-bold font-mono px-2 py-0.5 rounded-md ${changePositive ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                    }`}
                            >
                                {changePositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {changePositive ? '+' : ''}{changePct.toFixed(2)}%
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right: Market Status & System Health */}
                <div className="flex items-center gap-4">
                    <div className="hidden lg:flex flex-col items-end">
                        <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-500 uppercase mb-1">Data Engine</span>
                        <div className="flex items-center gap-4 text-slate-400 text-[11px] font-mono">
                            <div className="flex items-center gap-1.5">
                                <Activity className="w-3 h-3 text-blue-400" />
                                <span>WS:CONNECTED</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-1 h-1 rounded-full bg-slate-600" />
                                <span>LATENCY: 12ms</span>
                            </div>
                        </div>
                    </div>

                    <div
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-[11px] font-bold font-mono tracking-[0.15em] border transition-all duration-300"
                        style={{
                            background: mode === 'live' ? 'rgba(34,197,94,0.05)' : 'rgba(59,130,246,0.05)',
                            borderColor: `${modeColor}30`,
                            color: modeColor,
                            boxShadow: mode === 'live' ? '0 0 20px rgba(74,222,128,0.05)' : 'none'
                        }}
                    >
                        {mode === 'live' ? <Zap className="w-3.5 h-3.5 fill-current" /> : <Activity className="w-3.5 h-3.5" />}
                        {modeLabel} ENGINE
                    </div>
                </div>
            </div>

            <style jsx>{`
                @keyframes scan {
                    0% { left: -100%; opacity: 0; }
                    50% { opacity: 0.5; }
                    100% { left: 100%; opacity: 0; }
                }
            `}</style>
        </div>
    );
}

