"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface GammaExposurePanelProps {
    data: LiveMarketData | null;
}

export function GammaExposurePanel({ data }: GammaExposurePanelProps) {
    // Extract gamma analytics from intelligence data
    const gammaRegime = (data as any)?.intelligence?.structural_regime || 'unknown';
    const netGamma = (data as any)?.intelligence?.net_gamma || 0;
    const gammaFlipLevel = (data as any)?.intelligence?.gamma_flip_level || 0;
    const distanceFromFlip = (data as any)?.intelligence?.distance_from_flip || 0;
    const spot = (data as any)?.spot || 0;

    // Format gamma values for display
    const formatGamma = (value: number) => {
        if (Math.abs(value) >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`;
        } else if (Math.abs(value) >= 1000) {
            return `${(value / 1000).toFixed(0)}k`;
        }
        return value.toFixed(0);
    };

    // Get regime color and icon
    const getRegimeDisplay = (regime: string) => {
        switch (regime.toLowerCase()) {
            case 'positive_gamma':
                return {
                    label: 'Positive Gamma',
                    color: '#4ade80',
                    bgColor: 'rgba(34,197,94,0.12)',
                    borderColor: 'rgba(34,197,94,0.28)',
                    icon: <TrendingUp className="w-5 h-5" />
                };
            case 'negative_gamma':
                return {
                    label: 'Negative Gamma',
                    color: '#f87171',
                    bgColor: 'rgba(239,68,68,0.12)',
                    borderColor: 'rgba(239,68,68,0.28)',
                    icon: <TrendingDown className="w-5 h-5" />
                };
            default:
                return {
                    label: 'Neutral',
                    color: '#94a3b8',
                    bgColor: 'rgba(148,163,184,0.08)',
                    borderColor: 'rgba(148,163,184,0.18)',
                    icon: <Minus className="w-5 h-5" />
                };
        }
    };

    const regimeDisplay = getRegimeDisplay(gammaRegime);
    const distanceSign = distanceFromFlip >= 0 ? '+' : '';

    return (
        <div
            className="trading-panel h-full"
            onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = CARD_HOVER_BORDER;
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
            }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Gamma Exposure</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: regimeDisplay.bgColor,
                            border: `1px solid ${regimeDisplay.borderColor}`,
                            color: regimeDisplay.color,
                            boxShadow: `0 0 10px ${regimeDisplay.color}15`
                        }}
                    >
                        <span className="relative flex h-1.5 w-1.5">
                            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-70`} style={{ background: regimeDisplay.color }}></span>
                            <span className={`relative inline-flex rounded-full h-1.5 w-1.5`} style={{ background: regimeDisplay.color }}></span>
                        </span>
                        {regimeDisplay.label}
                    </span>
                </div>
            </div>

            {/* Main Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Net Gamma */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Net Gamma
                    </div>
                    <div className="text-xl font-bold text-white tabular-nums tracking-tight">
                        {formatGamma(netGamma)}
                    </div>
                    <div className="text-[10px] font-bold font-mono tracking-widest mt-1" style={{ color: netGamma > 0 ? '#4ade80' : netGamma < 0 ? '#f87171' : '#94a3b8' }}>
                        {netGamma > 0 ? 'BULLISH' : netGamma < 0 ? 'BEARISH' : 'NEUTRAL'}
                    </div>
                </div>

                {/* Flip Level */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Flip Level
                    </div>
                    <div className="text-xl font-bold text-white tabular-nums tracking-tight">
                        {gammaFlipLevel.toFixed(0)}
                    </div>
                    <div className="text-[10px] font-bold font-mono tracking-widest mt-1 text-cyan-400">
                        CRITICAL
                    </div>
                </div>
            </div>

            {/* Distance from Flip */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Distance from Flip
                    </span>
                    <span
                        className="text-[14px] font-bold font-mono tabular-nums tracking-tight"
                        style={{ color: distanceFromFlip >= 0 ? '#4ade80' : '#f87171', textShadow: `0 0 10px ${distanceFromFlip >= 0 ? '#4ade80' : '#f87171'}30` }}
                    >
                        {distanceSign}{distanceFromFlip.toFixed(1)}
                    </span>
                </div>

                {/* Distance Bar */}
                <div
                    className="w-full h-1.5 rounded-full overflow-hidden flex"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                            width: `${Math.min(100, Math.abs(distanceFromFlip) / 2)}%`,
                            background: distanceFromFlip >= 0
                                ? 'linear-gradient(90deg, #166534, #4ade80)'
                                : 'linear-gradient(90deg, #991b1b, #f87171)',
                            boxShadow: `0 0 8px ${distanceFromFlip >= 0 ? '#4ade80' : '#f87171'}40`
                        }}
                    />
                </div>

                {/* Distance Labels */}
                <div className="flex justify-between mt-2">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-red-500/50">NEGATIVE</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-slate-600">FLIP</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-green-500/50">POSITIVE</span>
                </div>
            </div>

            {/* Spot vs Flip Level */}
            <div className="mt-auto pt-3 border-t border-white/5 flex items-center justify-between">
                <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-600">Current Spot</span>
                <span className="text-[11px] font-bold font-mono text-white tracking-widest">{spot.toFixed(2)}</span>
            </div>
        </div>
    );
}

