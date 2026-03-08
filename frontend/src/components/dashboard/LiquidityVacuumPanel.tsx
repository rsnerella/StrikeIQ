"use client";
import React from 'react';
import { Wind, AlertTriangle, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface LiquidityVacuumPanelProps {
    data: LiveMarketData | null;
}

export function LiquidityVacuumPanel({ data }: LiquidityVacuumPanelProps) {
    // Extract liquidity vacuum data from backend
    const liquidityVacuum = (data as any)?.intelligence?.liquidity_vacuum || {};
    const liquidityPressure = (data as any)?.intelligence?.liquidity_pressure || 0.5;
    const supportLevel = (data as any)?.intelligence?.support_level || 0;
    const resistanceLevel = (data as any)?.intelligence?.resistance_level || 0;
    const spot = (data as any)?.spot || 0;

    // Get vacuum zone
    const getVacuumZone = () => {
        if (liquidityVacuum.zone_start && liquidityVacuum.zone_end) {
            return {
                start: liquidityVacuum.zone_start,
                end: liquidityVacuum.zone_end,
                width: liquidityVacuum.zone_end - liquidityVacuum.zone_start
            };
        }

        const range = resistanceLevel - supportLevel;
        const vacuumWidth = range * (1 - liquidityPressure);

        if (liquidityPressure < 0.3) {
            const center = (supportLevel + resistanceLevel) / 2;
            return {
                start: center - vacuumWidth / 2,
                end: center + vacuumWidth / 2,
                width: vacuumWidth
            };
        } else if (spot < supportLevel + range * 0.3) {
            return {
                start: supportLevel + range * 0.3,
                end: supportLevel + range * 0.7,
                width: vacuumWidth
            };
        } else if (spot > resistanceLevel - range * 0.3) {
            return {
                start: supportLevel + range * 0.3,
                end: supportLevel + range * 0.7,
                width: vacuumWidth
            };
        }

        const center = (supportLevel + resistanceLevel) / 2;
        return {
            start: center - vacuumWidth / 2,
            end: center + vacuumWidth / 2,
            width: vacuumWidth
        };
    };

    const vacuumZone = getVacuumZone();

    // Get vacuum severity
    const getVacuumSeverity = (pressure: number, width: number) => {
        const severityScore = (1 - pressure) * (width / 100);
        if (severityScore > 0.5) return { label: 'CRITICAL', color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)' };
        if (severityScore > 0.25) return { label: 'MODERATE', color: '#fb923c', bgColor: 'rgba(251,146,60,0.12)', borderColor: 'rgba(251,146,60,0.25)' };
        return { label: 'NORMAL', color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)' };
    };

    const vacuumSeverity = getVacuumSeverity(liquidityPressure, vacuumZone.width);

    // Check if spot is in vacuum zone
    const isInVacuumZone = spot >= vacuumZone.start && spot <= vacuumZone.end;

    // Get vacuum type
    const getVacuumType = () => {
        if (isInVacuumZone) {
            return {
                label: 'IN VACUUM',
                color: '#f87171',
                icon: <AlertTriangle className="w-4 h-4" />,
                message: 'Trading in low liquidity gap'
            };
        }

        const distanceToVacuum = Math.min(
            Math.abs(spot - vacuumZone.start),
            Math.abs(spot - vacuumZone.end)
        );

        if (distanceToVacuum < 20) {
            return {
                label: 'NEAR GAP',
                color: '#fb923c',
                icon: <Wind className="w-4 h-4" />,
                message: 'Approaching liquidity vacuum'
            };
        }

        return {
            label: 'CLEAR',
            color: '#4ade80',
            icon: <Activity className="w-4 h-4" />,
            message: 'Optimal liquidity profile'
        };
    };

    const vacuumType = getVacuumType();

    // Calculate fast move probability
    const calculateFastMoveProbability = () => {
        let probability = 0;
        if (liquidityPressure < 0.3) probability += 40;
        else if (liquidityPressure < 0.5) probability += 20;
        if (vacuumZone.width > 100) probability += 25;
        else if (vacuumZone.width > 50) probability += 15;
        if (isInVacuumZone) probability += 35;
        return Math.min(95, Math.max(5, probability));
    };

    const fastMoveProbability = calculateFastMoveProbability();

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
                <SectionLabel>Liquidity Vacuum</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: vacuumSeverity.bgColor,
                            border: `1px solid ${vacuumSeverity.borderColor}`,
                            color: vacuumSeverity.color,
                            boxShadow: `0 0 10px ${vacuumSeverity.color}15`
                        }}
                    >
                        {vacuumType.icon}
                        {vacuumSeverity.label}
                    </span>
                </div>
            </div>

            {/* Vacuum Zone Visualization */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Liquidity Gap Zone
                    </span>
                    <span className="text-[13px] font-bold font-mono tracking-tight text-white">
                        {vacuumZone.start.toFixed(0)} — {vacuumZone.end.toFixed(0)}
                    </span>
                </div>

                {/* Zone Visualization */}
                <div className="relative h-6 rounded-full overflow-hidden border border-white/5" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    {/* Support/Resistance markers */}
                    <div
                        className="absolute top-0 bottom-0 w-0.5 bg-blue-500/40 z-10"
                        style={{ left: '20%' }}
                    />
                    <div
                        className="absolute top-0 bottom-0 w-0.5 bg-red-500/40 z-10"
                        style={{ right: '20%' }}
                    />

                    {/* Vacuum zone highlight */}
                    <div
                        className="absolute top-1 bottom-1 rounded-full z-0"
                        style={{
                            left: '21%',
                            width: '58%',
                            background: 'linear-gradient(90deg, rgba(239,68,68,0.05), rgba(239,68,68,0.2), rgba(239,68,68,0.05))',
                            border: '1px solid rgba(239,68,68,0.1)',
                            animation: isInVacuumZone ? 'pulse 2s infinite' : 'none'
                        }}
                    />

                    {/* Current spot pointer */}
                    <div
                        className="absolute top-1 bottom-1 w-1.5 bg-white z-20 rounded-full transition-all duration-700 ease-out"
                        style={{
                            left: spot < vacuumZone.start ? '12%' : spot > vacuumZone.end ? '88%' : '50%',
                            transform: 'translateX(-50%)',
                            boxShadow: '0 0 8px #fff'
                        }}
                    />
                </div>

                <div className="flex justify-between mt-2">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-blue-500/50 uppercase">Sup: {supportLevel.toFixed(0)}</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-red-500/50 uppercase">Res: {resistanceLevel.toFixed(0)}</span>
                </div>
            </div>

            {/* Consolidated Metrics Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div
                    className="rounded-xl p-3.5 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Vacuum Width
                    </div>
                    <div className="text-xl font-bold text-white tabular-nums tracking-tight">
                        {vacuumZone.width.toFixed(1)}
                        <span className="text-[10px] ml-1 text-slate-500">PTS</span>
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-orange-500/50 uppercase italic">
                        SLIPPAGE RISK
                    </div>
                </div>

                <div
                    className="rounded-xl p-3.5 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Liquidity
                    </div>
                    <div className="text-xl font-bold tabular-nums tracking-tight" style={{ color: vacuumSeverity.color }}>
                        {((1 - liquidityPressure) * 100).toFixed(0)}%
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-slate-500 uppercase">
                        DEPTH SCORE
                    </div>
                </div>
            </div>

            {/* Fast Move Probability */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Rapid Expansion Risk
                    </span>
                    <span
                        className="text-[16px] font-bold font-mono tracking-tight"
                        style={{ color: fastMoveProbability > 60 ? '#f87171' : fastMoveProbability > 30 ? '#fb923c' : '#4ade80' }}
                    >
                        {fastMoveProbability.toFixed(0)}%
                    </span>
                </div>

                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                    <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{
                            width: `${fastMoveProbability}%`,
                            background: `linear-gradient(90deg, #1e293b, ${fastMoveProbability > 60 ? '#f87171' : fastMoveProbability > 30 ? '#fb923c' : '#4ade80'})`,
                        }}
                    />
                </div>
            </div>

            {/* Analysis Footer */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
                        <Wind className="w-4 h-4 text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-bold font-mono tracking-widest text-orange-400 uppercase mb-0.5">
                            Structural Analysis
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 truncate italic">
                            {vacuumType.message}
                        </div>
                    </div>
                </div>

                <div className="text-[10px] font-bold font-mono tracking-widest text-center py-2 px-3 rounded-lg bg-white/2 border border-white/5 uppercase opacity-80">
                    {fastMoveProbability > 60
                        ? '⚡️ SYSTEMIC SLIPPAGE - EXPECT RAPID CANDLES'
                        : fastMoveProbability > 30
                            ? '👀 MONITORING - REDUCED ORDER BOOK DEPTH'
                            : '✅ STABLE DEPTH - LOW SLIPPAGE CONDITIONS'
                    }
                </div>
            </div>
        </div>
    );
}

export default React.memo(LiquidityVacuumPanel);
