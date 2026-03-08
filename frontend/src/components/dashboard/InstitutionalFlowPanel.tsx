"use client";
import React from 'react';
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface InstitutionalFlowPanelProps {
    data: LiveMarketData | null;
}

export function InstitutionalFlowPanel({ data }: InstitutionalFlowPanelProps) {
    // Extract flow analytics from intelligence data
    const callFlowVelocity = (data as any)?.intelligence?.call_oi_velocity || 0;
    const putFlowVelocity = (data as any)?.intelligence?.put_oi_velocity || 0;
    const flowDirection = (data as any)?.intelligence?.flow_direction || 'neutral';
    const intentScore = (data as any)?.intelligence?.intent_score || 0;
    const flowImbalance = (data as any)?.intelligence?.flow_imbalance || 0;

    // Format flow values
    const formatFlow = (value: number) => {
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
                    label: 'CALL DOMINANT',
                    color: '#4ade80',
                    bgColor: 'rgba(34,197,94,0.12)',
                    borderColor: 'rgba(34,197,94,0.28)',
                    icon: <ArrowUpRight className="w-4 h-4" />
                };
            case 'put':
                return {
                    label: 'PUT DOMINANT',
                    color: '#f87171',
                    bgColor: 'rgba(239,68,68,0.12)',
                    borderColor: 'rgba(239,68,68,0.28)',
                    icon: <ArrowDownRight className="w-4 h-4" />
                };
            default:
                return {
                    label: 'BALANCED',
                    color: '#94a3b8',
                    bgColor: 'rgba(148,163,184,0.08)',
                    borderColor: 'rgba(148,163,184,0.18)',
                    icon: <Minus className="w-4 h-4" />
                };
        }
    };

    const flowDisplay = getFlowDirectionDisplay(flowDirection);
    const totalFlow = Math.abs(callFlowVelocity) + Math.abs(putFlowVelocity);
    const callPercentage = totalFlow > 0 ? (Math.abs(callFlowVelocity) / totalFlow) * 100 : 50;
    const putPercentage = totalFlow > 0 ? (Math.abs(putFlowVelocity) / totalFlow) * 100 : 50;

    // Get intent score color
    const getIntentColor = (score: number) => {
        if (score >= 70) return { color: '#4ade80', label: 'HIGH' };
        if (score >= 40) return { color: '#fb923c', label: 'MED' };
        return { color: '#94a3b8', label: 'LOW' };
    };

    const intentDisplay = getIntentColor(intentScore);

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
                <SectionLabel>Institutional Flow</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: flowDisplay.bgColor,
                            border: `1px solid ${flowDisplay.borderColor}`,
                            color: flowDisplay.color,
                            boxShadow: `0 0 10px ${flowDisplay.color}15`
                        }}
                    >
                        {flowDisplay.icon}
                        {flowDisplay.label}
                    </span>
                </div>
            </div>

            {/* Flow Velocities */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Call Flow */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Call Velocity
                    </div>
                    <div className="text-xl font-bold text-green-400 tabular-nums tracking-tight">
                        {formatFlow(callFlowVelocity)}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-green-500/50">
                        {callPercentage.toFixed(0)}% SHARE
                    </div>
                </div>

                {/* Put Flow */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Put Velocity
                    </div>
                    <div className="text-xl font-bold text-red-400 tabular-nums tracking-tight">
                        {formatFlow(putFlowVelocity)}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-red-500/50">
                        {putPercentage.toFixed(0)}% SHARE
                    </div>
                </div>
            </div>

            {/* Flow Imbalance Bar */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Flow Imbalance
                    </span>
                    <span
                        className="text-[14px] font-bold font-mono tabular-nums tracking-tight"
                        style={{ color: flowImbalance > 0 ? '#4ade80' : flowImbalance < 0 ? '#f87171' : '#94a3b8' }}
                    >
                        {flowImbalance > 0 ? '+' : ''}{(flowImbalance * 100).toFixed(1)}%
                    </span>
                </div>

                {/* Imbalance Bar */}
                <div
                    className="w-full h-1.5 rounded-full overflow-hidden relative"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    {/* Call side (green) */}
                    <div
                        className="absolute left-0 top-0 h-full rounded-l-full transition-all duration-700 ease-out"
                        style={{
                            width: `${callPercentage}%`,
                            background: 'linear-gradient(90deg, #166534, #4ade80)',
                            boxShadow: '0 0 10px rgba(74,222,128,0.2)'
                        }}
                    />
                    {/* Put side (red) - actually positioned from right but width calculates from total */}
                    <div
                        className="absolute right-0 top-0 h-full rounded-r-full transition-all duration-700 ease-out"
                        style={{
                            width: `${putPercentage}%`,
                            background: 'linear-gradient(90deg, #f87171, #991b1b)',
                            boxShadow: '0 0 10px rgba(248,113,113,0.2)'
                        }}
                    />
                    {/* Center divider */}
                    <div
                        className="absolute top-0 bottom-0 w-0.5 bg-white/20 z-10"
                        style={{ left: '50%', transform: 'translateX(-50%)' }}
                    />
                </div>

                {/* Flow Labels */}
                <div className="flex justify-between mt-2">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-green-500/50 uppercase">Calls</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-slate-500 uppercase">Neutral</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-red-500/50 uppercase">Puts</span>
                </div>
            </div>

            {/* Intent Score */}
            <div className="mt-auto pt-3 border-t border-white/5 flex items-center justify-between">
                <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-600">
                    Proprietary Intent Score
                </span>
                <div className="flex items-center gap-3">
                    <div
                        className="h-1.5 rounded-full overflow-hidden"
                        style={{ background: 'rgba(255,255,255,0.06)', width: '80px' }}
                    >
                        <div
                            className="h-full rounded-full transition-all duration-700 ease-out"
                            style={{
                                width: `${intentScore}%`,
                                background: `linear-gradient(90deg, #1e293b, ${intentDisplay.color})`,
                                boxShadow: `0 0 8px ${intentDisplay.color}30`
                            }}
                        />
                    </div>
                    <span
                        className="text-[12px] font-bold font-mono tabular-nums tracking-widest"
                        style={{ color: intentDisplay.color }}
                    >
                        {intentScore.toFixed(0)}%
                    </span>
                </div>
            </div>
        </div>
    );
}

