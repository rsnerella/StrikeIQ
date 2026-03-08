"use client";
import React from 'react';
import { Zap, TrendingUp, Activity, Target } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface GammaSqueezePanelProps {
    data: LiveMarketData | null;
}

export function GammaSqueezePanel({ data }: GammaSqueezePanelProps) {
    // Extract gamma squeeze data from backend
    const gammaPressure = (data as any)?.intelligence?.gamma_pressure || {};
    const netGamma = (data as any)?.intelligence?.net_gamma || 0;
    const gammaRegime = (data as any)?.intelligence?.structural_regime || 'unknown';
    const gammaFlipLevel = (data as any)?.intelligence?.gamma_flip_level || 0;
    const distanceFromFlip = (data as any)?.intelligence?.distance_from_flip || 0;

    // Get gamma pressure level
    const getGammaPressureLevel = (pressure: any) => {
        const pressureValue = pressure.level || 0;
        if (pressureValue >= 0.7) return { label: 'EXTREME', color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)' };
        if (pressureValue >= 0.4) return { label: 'ELEVATED', color: '#fb923c', bgColor: 'rgba(251,146,60,0.12)', borderColor: 'rgba(251,146,60,0.25)' };
        return { label: 'NORMAL', color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)' };
    };

    const pressureLevel = getGammaPressureLevel(gammaPressure);

    // Calculate squeeze probability
    const calculateSqueezeProbability = () => {
        let probability = 0;
        if (gammaPressure.level >= 0.7) probability += 30;
        else if (gammaPressure.level >= 0.4) probability += 15;
        if (gammaRegime === 'negative_gamma') probability += 25;
        else if (gammaRegime === 'positive_gamma') probability -= 10;
        if (Math.abs(distanceFromFlip) < 25) probability += 20;
        else if (Math.abs(distanceFromFlip) < 50) probability += 10;
        if (Math.abs(netGamma) > 100000) probability += 15;
        else if (Math.abs(netGamma) > 50000) probability += 8;
        return Math.min(95, Math.max(5, probability));
    };

    const squeezeProbability = calculateSqueezeProbability();

    // Format gamma values
    const formatGamma = (value: number) => {
        if (Math.abs(value) >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`;
        } else if (Math.abs(value) >= 1000) {
            return `${(value / 1000).toFixed(0)}k`;
        }
        return value.toFixed(0);
    };

    // Get squeeze condition display
    const getSqueezeCondition = () => {
        if (squeezeProbability >= 60) {
            return {
                label: 'SQUEEZE LIKELY',
                color: '#f87171',
                message: 'Market conditions favor a systemic gamma squeeze'
            };
        } else if (squeezeProbability >= 35) {
            return {
                label: 'SQUEEZE WATCH',
                color: '#fb923c',
                message: 'Monitor for rising dealer hedging pressure'
            };
        } else {
            return {
                label: 'LOW RISK',
                color: '#4ade80',
                message: 'Squeeze conditions are currently latent'
            };
        }
    };

    const squeezeCondition = getSqueezeCondition();

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
                <SectionLabel>Gamma Squeeze</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: pressureLevel.bgColor,
                            border: `1px solid ${pressureLevel.borderColor}`,
                            color: pressureLevel.color,
                            boxShadow: `0 0 10px ${pressureLevel.color}15`
                        }}
                    >
                        <Zap className="w-3.5 h-3.5" />
                        {pressureLevel.label}
                    </span>
                </div>
            </div>

            {/* Gamma Pressure Bar */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Hedging Pressure
                    </span>
                    <span
                        className="text-[13px] font-bold font-mono tracking-tight"
                        style={{ color: pressureLevel.color }}
                    >
                        {((gammaPressure.level || 0) * 100).toFixed(0)}%
                    </span>
                </div>

                <div
                    className="w-full h-1.5 rounded-full overflow-hidden"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                            width: `${(gammaPressure.level || 0) * 100}%`,
                            background: `linear-gradient(90deg, #1e293b, ${pressureLevel.color})`,
                        }}
                    />
                </div>
            </div>

            {/* Consolidated Metrics Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Net Gamma */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Total Gamma
                    </div>
                    <div className="text-xl font-bold text-white tabular-nums tracking-tight">
                        {formatGamma(netGamma)}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 uppercase" style={{ color: netGamma > 0 ? '#4ade80' : '#f87171' }}>
                        {netGamma > 0 ? 'Bullish Dist' : 'Bearish Dist'}
                    </div>
                </div>

                {/* Flip Level */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Dealer Flip
                    </div>
                    <div className="text-xl font-bold text-blue-400 tabular-nums tracking-tight">
                        {gammaFlipLevel.toFixed(0)}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-slate-500 uppercase">
                        {distanceFromFlip > 0 ? '+' : ''}{distanceFromFlip.toFixed(0)} PTS AWAY
                    </div>
                </div>
            </div>

            {/* Squeeze Probability Indicator */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Squeeze Probability
                    </span>
                    <div className="flex items-center gap-3">
                        <span
                            className="text-[16px] font-bold font-mono tracking-tight"
                            style={{ color: squeezeCondition.color, textShadow: `0 0 10px ${squeezeCondition.color}30` }}
                        >
                            {squeezeProbability.toFixed(0)}%
                        </span>
                        <span
                            className="text-[9px] font-bold font-mono px-2 py-0.5 rounded tracking-widest uppercase border"
                            style={{
                                background: `${squeezeCondition.color}15`,
                                borderColor: `${squeezeCondition.color}30`,
                                color: squeezeCondition.color
                            }}
                        >
                            {squeezeCondition.label.split(' ')[0]}
                        </span>
                    </div>
                </div>

                <div
                    className="w-full h-1.5 rounded-full overflow-hidden"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{
                            width: `${squeezeProbability}%`,
                            background: `linear-gradient(90deg, #1e293b, ${squeezeCondition.color})`,
                        }}
                    />
                </div>
            </div>

            {/* Analysis Footer */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
                        <Activity className="w-4 h-4 text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-bold font-mono tracking-widest text-slate-400 uppercase mb-0.5">
                            Structural Regime: {gammaRegime.replace('_', ' ').toUpperCase()}
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 truncate lowercase italic">
                            {squeezeCondition.message}
                        </div>
                    </div>
                </div>

                <div className="text-[10px] font-bold font-mono tracking-widest text-center py-2 px-3 rounded-lg bg-white/2 border border-white/5 uppercase opacity-80">
                    {squeezeProbability >= 60
                        ? '⚡️ HIGH SQUEEZE RISK - EXPECT DELTA EXPLOSION'
                        : squeezeProbability >= 35
                            ? '👀 WATCHING - VOLATILITY EXPANSION POSSIBLE'
                            : '✅ STABLE - HEDGING FLOWS BALANCED'
                    }
                </div>
            </div>
        </div>
    );
}

export default React.memo(GammaSqueezePanel);
