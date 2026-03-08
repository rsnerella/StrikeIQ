"use client";
import React from 'react';
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Users, Target } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface InstitutionalActivityPanelProps {
    data: LiveMarketData | null;
}

export function InstitutionalActivityPanel({ data }: InstitutionalActivityPanelProps) {
    // Extract institutional activity data from backend
    const intentScore = (data as any)?.intelligence?.intent_score || 0;
    const flowDirection = (data as any)?.intelligence?.flow_direction || 'neutral';
    const flowImbalance = (data as any)?.intelligence?.flow_imbalance || 0;
    const callOiVelocity = (data as any)?.intelligence?.call_oi_velocity || 0;
    const putOiVelocity = (data as any)?.intelligence?.put_oi_velocity || 0;

    // Format velocity values
    const formatVelocity = (value: number) => {
        if (Math.abs(value) >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`;
        } else if (Math.abs(value) >= 1000) {
            return `${(value / 1000).toFixed(0)}k`;
        }
        return value.toFixed(0);
    };

    // Get flow direction display
    const getFlowDirectionDisplay = (direction: string) => {
        switch (direction.toLowerCase()) {
            case 'call':
                return {
                    label: 'CALL DOMINANCE',
                    color: '#4ade80',
                    bgColor: 'rgba(34,197,94,0.12)',
                    borderColor: 'rgba(34,197,94,0.25)',
                    icon: <ArrowUpRight className="w-4 h-4" />
                };
            case 'put':
                return {
                    label: 'PUT DOMINANCE',
                    color: '#f87171',
                    bgColor: 'rgba(239,68,68,0.12)',
                    borderColor: 'rgba(239,68,68,0.25)',
                    icon: <ArrowDownRight className="w-4 h-4" />
                };
            default:
                return {
                    label: 'BALANCED',
                    color: '#94a3b8',
                    bgColor: 'rgba(148,163,184,0.08)',
                    borderColor: 'rgba(148,163,184,0.18)',
                    icon: <Users className="w-4 h-4" />
                };
        }
    };

    const flowDisplay = getFlowDirectionDisplay(flowDirection);

    // Get intent level display
    const getIntentLevel = (score: number) => {
        if (score >= 80) return { label: 'CRITICAL', color: '#4ade80', barColor: 'linear-gradient(90deg, #14532d, #4ade80)' };
        if (score >= 60) return { label: 'HIGH', color: '#22c55e', barColor: 'linear-gradient(90deg, #14532d, #22c55e)' };
        if (score >= 40) return { label: 'MODERATE', color: '#fb923c', barColor: 'linear-gradient(90deg, #7c2d12, #fb923c)' };
        return { label: 'LOW', color: '#94a3b8', barColor: 'linear-gradient(90deg, #1e293b, #94a3b8)' };
    };

    const intentLevel = getIntentLevel(intentScore);

    // Calculate total flow and percentages
    const totalFlow = Math.abs(callOiVelocity) + Math.abs(putOiVelocity);
    const callPercentage = totalFlow > 0 ? (Math.abs(callOiVelocity) / totalFlow) * 100 : 50;
    const putPercentage = totalFlow > 0 ? (Math.abs(putOiVelocity) / totalFlow) * 100 : 50;

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
                <SectionLabel>Institutional Intensity</SectionLabel>
                <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 shadow-[0_0_10px_rgba(59,130,246,0.1)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                        <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400 uppercase">Live Flow</span>
                    </span>
                </div>
            </div>

            {/* Intent Score Indicator */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Commitment Score
                    </span>
                    <div className="flex items-center gap-3">
                        <span
                            className="text-[16px] font-bold font-mono tracking-tight"
                            style={{ color: intentLevel.color, textShadow: `0 0 10px ${intentLevel.color}30` }}
                        >
                            {intentScore.toFixed(0)}%
                        </span>
                        <span
                            className="text-[9px] font-bold font-mono px-2 py-0.5 rounded tracking-widest uppercase border"
                            style={{
                                background: `${intentLevel.color}15`,
                                borderColor: `${intentLevel.color}25`,
                                color: intentLevel.color
                            }}
                        >
                            {intentLevel.label}
                        </span>
                    </div>
                </div>

                <div
                    className="w-full h-1.5 rounded-full overflow-hidden"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                            width: `${intentScore}%`,
                            background: intentLevel.barColor,
                        }}
                    />
                </div>
            </div>

            {/* Flow Direction & Imbalance */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Flow Imbalance
                    </span>
                    <div className="flex items-center gap-2">
                        <span style={{ color: flowDisplay.color }}>{flowDisplay.icon}</span>
                        <span
                            className="text-[11px] font-bold font-mono tracking-widest uppercase"
                            style={{ color: flowDisplay.color }}
                        >
                            {flowDisplay.label}
                        </span>
                    </div>
                </div>

                <div
                    className="w-full h-1.5 rounded-full overflow-hidden relative"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <div
                        className="absolute left-0 top-0 h-full transition-all duration-700 ease-out"
                        style={{
                            width: `${callPercentage}%`,
                            background: 'linear-gradient(90deg, #166534, #4ade80)',
                        }}
                    />
                    <div
                        className="absolute right-0 top-0 h-full transition-all duration-700 ease-out"
                        style={{
                            width: `${putPercentage}%`,
                            background: 'linear-gradient(270deg, #991b1b, #f87171)',
                        }}
                    />
                    <div
                        className="absolute top-0 bottom-0 w-0.5 bg-white/40 z-10"
                        style={{ left: '50%', transform: 'translateX(-50%)' }}
                    />
                </div>

                <div className="flex justify-between mt-2">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-green-500/50 uppercase">Calls: {callPercentage.toFixed(0)}%</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-red-500/50 uppercase">Puts: {putPercentage.toFixed(0)}%</span>
                </div>
            </div>

            {/* Velocity Metrics Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Call Velocity
                    </div>
                    <div className="text-xl font-bold text-green-400 tabular-nums tracking-tight">
                        {formatVelocity(callOiVelocity)}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-green-500/40 uppercase">
                        OI ACCUMULATION
                    </div>
                </div>

                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Put Velocity
                    </div>
                    <div className="text-xl font-bold text-red-500 tabular-nums tracking-tight">
                        {formatVelocity(putOiVelocity)}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-red-500/40 uppercase">
                        OI ACCUMULATION
                    </div>
                </div>
            </div>

            {/* Summary Footer */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <Target className="w-4 h-4 text-blue-400" />
                        </div>
                        <div className="text-[11px] font-bold font-mono tracking-widest text-slate-400 uppercase">
                            Smart Money Regime
                        </div>
                    </div>
                    <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-white/2 border border-white/5">
                        <div
                            className="w-1.5 h-1.5 rounded-full animate-pulse"
                            style={{
                                backgroundColor: totalFlow > 1000 ? '#4ade80' :
                                    totalFlow > 500 ? '#fb923c' : '#94a3b8'
                            }}
                        />
                        <span className="text-[10px] font-bold font-mono tracking-widest" style={{
                            color: totalFlow > 1000 ? '#4ade80' :
                                totalFlow > 500 ? '#fb923c' : '#94a3b8'
                        }}>
                            {totalFlow > 1000 ? 'AGGRESSIVE' : totalFlow > 500 ? 'ACTIVE' : 'LATENT'}
                        </span>
                    </div>
                </div>

                <div className="text-[10px] font-mono leading-relaxed text-slate-500 italic px-1">
                    {Math.abs(flowImbalance) > 0.3
                        ? `Structural ${flowDirection} imbalance detected. Institutions are positioning for directional expansion.`
                        : 'Institutional activity is currently balanced with no clear directional commitment.'
                    }
                </div>
            </div>
        </div>
    );
}

export default React.memo(InstitutionalActivityPanel);

