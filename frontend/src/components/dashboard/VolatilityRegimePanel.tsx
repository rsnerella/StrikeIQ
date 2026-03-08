"use client";
import React from 'react';
import { Activity, TrendingUp, AlertTriangle, BarChart3 } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface VolatilityRegimePanelProps {
    data: LiveMarketData | null;
}

export function VolatilityRegimePanel({ data }: VolatilityRegimePanelProps) {
    // Extract volatility data from backend
    const volatilityRegime = (data as any)?.intelligence?.volatility_regime || 'normal';
    const breachProbability = (data as any)?.intelligence?.breach_probability || 0;
    const expectedMove = (data as any)?.intelligence?.expected_move || 0;
    const spot = (data as any)?.spot || 0;

    // Get regime display properties
    const getRegimeDisplay = (regime: string) => {
        switch (regime.toLowerCase()) {
            case 'extreme':
                return {
                    label: 'EXTREME',
                    color: '#f87171',
                    bgColor: 'rgba(239,68,68,0.12)',
                    borderColor: 'rgba(239,68,68,0.25)',
                    icon: <AlertTriangle className="w-4 h-4" />,
                    description: 'Systemic volatility risk detected'
                };
            case 'elevated':
                return {
                    label: 'ELEVATED',
                    color: '#fb923c',
                    bgColor: 'rgba(251,146,60,0.12)',
                    borderColor: 'rgba(251,146,60,0.25)',
                    icon: <Activity className="w-4 h-4" />,
                    description: 'Structural expansion in progress'
                };
            case 'low':
                return {
                    label: 'LOW',
                    color: '#60a5fa',
                    bgColor: 'rgba(59,130,246,0.12)',
                    borderColor: 'rgba(59,130,246,0.25)',
                    icon: <BarChart3 className="w-4 h-4" />,
                    description: 'Mean reversion regime'
                };
            default:
                return {
                    label: 'NORMAL',
                    color: '#4ade80',
                    bgColor: 'rgba(34,197,94,0.12)',
                    borderColor: 'rgba(34,197,94,0.25)',
                    icon: <TrendingUp className="w-4 h-4" />,
                    description: 'Standard market conditions'
                };
        }
    };

    const regimeDisplay = getRegimeDisplay(volatilityRegime);

    // Get probability color
    const getProbabilityColor = (probability: number) => {
        if (probability >= 70) return { color: '#f87171', label: 'HIGH' };
        if (probability >= 40) return { color: '#fb923c', label: 'MEDIUM' };
        return { color: '#4ade80', label: 'LOW' };
    };

    const probabilityDisplay = getProbabilityColor(breachProbability);

    // Calculate range percentages
    const upperRange = spot + expectedMove;
    const lowerRange = spot - expectedMove;
    const rangePercentage = ((expectedMove / spot) * 100).toFixed(1);

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
                <SectionLabel>Volatility Intelligence</SectionLabel>
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
                        {regimeDisplay.icon}
                        {regimeDisplay.label} REGIME
                    </span>
                </div>
            </div>

            {/* Price Range Section */}
            <div className="mb-6 rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-4">
                    <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                            Expected Move (1σ)
                        </span>
                        <span className="text-[11px] font-mono text-slate-600 uppercase">Implied Deviation: {rangePercentage}%</span>
                    </div>
                    <span className="text-[18px] font-bold font-mono tracking-tight text-white tabular-nums">
                        ±{expectedMove.toFixed(1)}
                    </span>
                </div>

                {/* Range Bar Visualization */}
                <div className="space-y-3">
                    <div className="relative h-6 rounded-lg overflow-hidden border border-white/5" style={{ background: 'rgba(0,0,0,0.3)' }}>
                        {/* The Gradient Base */}
                        <div
                            className="absolute inset-0 opacity-40"
                            style={{
                                background: 'linear-gradient(90deg, #f87171, #fb923c, #4ade80 50%, #fb923c, #f87171)'
                            }}
                        />
                        {/* Centered Current Spot Pointer */}
                        <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 flex items-center z-10">
                            <div className="w-1.5 h-full bg-white shadow-[0_0_12px_rgba(255,255,255,0.8)]" />
                        </div>
                    </div>
                    <div className="flex justify-between items-center px-1">
                        <div className="flex flex-col">
                            <span className="text-[9px] font-bold font-mono text-slate-500 tracking-wider">LOWER BOUND</span>
                            <span className="text-[12px] font-bold font-mono text-red-400 tabular-nums">{lowerRange.toFixed(1)}</span>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-bold font-mono text-slate-500 tracking-wider">UPPER BOUND</span>
                            <span className="text-[12px] font-bold font-mono text-green-400 tabular-nums">{upperRange.toFixed(1)}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Breakout Risk Section */}
            <div className="mb-6 rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Expansion Probability
                    </span>
                    <div className="flex items-center gap-3">
                        <span
                            className="text-[18px] font-bold font-mono tracking-tight"
                            style={{ color: probabilityDisplay.color, textShadow: `0 0 10px ${probabilityDisplay.color}30` }}
                        >
                            {breachProbability.toFixed(0)}%
                        </span>
                    </div>
                </div>

                <div className="w-full h-1.5 rounded-full overflow-hidden bg-white/5 mb-2">
                    <div
                        className="h-full rounded-full transition-all duration-1000 ease-out shadow-[0_0_8px_rgba(0,0,0,0.5)]"
                        style={{
                            width: `${breachProbability}%`,
                            background: `linear-gradient(90deg, #1e293b, ${probabilityDisplay.color})`
                        }}
                    />
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-slate-600 uppercase">STABILITY</span>
                    <span
                        className="text-[9px] font-bold font-mono tracking-widest uppercase px-2 py-0.5 rounded-md border"
                        style={{ background: `${probabilityDisplay.color}10`, borderColor: `${probabilityDisplay.color}20`, color: probabilityDisplay.color }}
                    >
                        {probabilityDisplay.label} EXPANSION RISK
                    </span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-slate-600 uppercase">VOLATILITY</span>
                </div>
            </div>

            {/* Trading Summary Footer */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/2 border border-white/5">
                    <div style={{ color: regimeDisplay.color }}>{regimeDisplay.icon}</div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold font-mono tracking-widest text-slate-400 uppercase">Regime Outlook</span>
                        <span className="text-[11px] font-mono text-slate-500 italic">{regimeDisplay.description}</span>
                    </div>
                </div>

                <div className="text-[10px] font-bold font-mono tracking-widest text-center py-2 px-3 rounded-lg bg-white/2 border border-white/5 uppercase opacity-80">
                    {volatilityRegime === 'extreme'
                        ? '🚫 SYSTEMIC RISK - DE-LEVERAGE IMMEDIATELY'
                        : volatilityRegime === 'elevated'
                            ? '⚡ INCREASE STOP BUFFER - NOISY MOVES'
                            : volatilityRegime === 'low'
                                ? '📉 MEAN REVERSION LIKELY - SELL TAILS'
                                : '✅ CONVENTIONAL VOLATILITY - MODEL ALIGNED'
                    }
                </div>
            </div>
        </div>
    );
}

export default React.memo(VolatilityRegimePanel);


