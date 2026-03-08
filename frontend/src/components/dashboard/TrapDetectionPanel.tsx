"use client";
import React from 'react';
import { AlertTriangle, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface TrapDetectionPanelProps {
    data: LiveMarketData | null;
}

export function TrapDetectionPanel({ data }: TrapDetectionPanelProps) {
    // Extract trap detection data from backend
    const optionsTrap = (data as any)?.intelligence?.options_trap || {};
    const trapProbability = optionsTrap.probability || 0;
    const trapDirection = optionsTrap.direction || 'neutral';
    const trapStrength = optionsTrap.strength || 0;
    const resistanceLevel = (data as any)?.intelligence?.resistance_level || 0;
    const supportLevel = (data as any)?.intelligence?.support_level || 0;

    // Get trap risk level
    const getTrapRiskLevel = (probability: number) => {
        if (probability >= 70) return { label: 'CRITICAL', color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)' };
        if (probability >= 40) return { label: 'MODERATE', color: '#fb923c', bgColor: 'rgba(251,146,60,0.12)', borderColor: 'rgba(251,146,60,0.25)' };
        return { label: 'NORMAL', color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)' };
    };

    const trapRisk = getTrapRiskLevel(trapProbability);

    // Get trap direction display
    const getTrapDirectionDisplay = (direction: string) => {
        switch (direction.toLowerCase()) {
            case 'bearish':
                return {
                    label: 'BEARISH TRAP',
                    color: '#f87171',
                    icon: <TrendingDown className="w-4 h-4" />,
                    message: 'Institutions absorption detected. Retail selling likely to fail.'
                };
            case 'bullish':
                return {
                    label: 'BULLISH TRAP',
                    color: '#4ade80',
                    icon: <TrendingUp className="w-4 h-4" />,
                    message: 'Aggressive buying absorption. Breakout likely a fakeout.'
                };
            default:
                return {
                    label: 'NEUTRAL',
                    color: '#94a3b8',
                    icon: <AlertTriangle className="w-4 h-4" />,
                    message: 'No institutional trap patterns identified.'
                };
        }
    };

    const trapDirectionDisplay = getTrapDirectionDisplay(trapDirection);

    // Get strength display
    const getStrengthDisplay = (strength: number) => {
        if (strength >= 0.7) return { label: 'AGGRESSIVE', color: '#f87171' };
        if (strength >= 0.4) return { label: 'STEADY', color: '#fb923c' };
        return { label: 'LATENT', color: '#4ade80' };
    };

    const strengthDisplay = getStrengthDisplay(trapStrength);

    // Calculate trap location
    const getTrapLocation = () => {
        if (trapDirection === 'bearish' && resistanceLevel > 0) {
            return `RESISTANCE: ${resistanceLevel.toFixed(0)}`;
        } else if (trapDirection === 'bullish' && supportLevel > 0) {
            return `SUPPORT: ${supportLevel.toFixed(0)}`;
        }
        return 'CONSOLIDATION RANGE';
    };

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
                <SectionLabel>Trap Detection</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: trapRisk.bgColor,
                            border: `1px solid ${trapRisk.borderColor}`,
                            color: trapRisk.color,
                            boxShadow: `0 0 10px ${trapRisk.color}15`
                        }}
                    >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        {trapRisk.label}
                    </span>
                </div>
            </div>

            {/* Trap Probability Indicator */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Confidence Score
                    </span>
                    <span
                        className="text-[16px] font-bold font-mono tracking-tight"
                        style={{ color: trapRisk.color }}
                    >
                        {trapProbability.toFixed(0)}%
                    </span>
                </div>

                <div
                    className="w-full h-1.5 rounded-full overflow-hidden"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                            width: `${trapProbability}%`,
                            background: `linear-gradient(90deg, #1e293b, ${trapRisk.color})`,
                        }}
                    />
                </div>
            </div>

            {/* Consolidated Metrics Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Trap Direction */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Bias
                    </div>
                    <div className="flex items-center gap-2">
                        <span style={{ color: trapDirectionDisplay.color }}>{trapDirectionDisplay.icon}</span>
                        <div className="text-[13px] font-bold text-white tabular-nums tracking-tight uppercase">
                            {trapDirectionDisplay.label.split(' ')[0]}
                        </div>
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-slate-500 uppercase">
                        {trapDirectionDisplay.label.split(' ')[1] || 'FLOW'}
                    </div>
                </div>

                {/* Trap Strength */}
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Intensity
                    </div>
                    <div
                        className="text-[14px] font-bold tabular-nums tracking-tight uppercase"
                        style={{ color: strengthDisplay.color }}
                    >
                        {strengthDisplay.label}
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-slate-500 uppercase">
                        MOMENTUM
                    </div>
                </div>
            </div>

            {/* Trap Context */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
                        <Users className="w-4 h-4 text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-bold font-mono tracking-widest text-slate-400 uppercase mb-0.5">
                            Retails Trapped: {getTrapLocation()}
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 truncate italic">
                            {trapDirectionDisplay.message}
                        </div>
                    </div>
                </div>

                <div className="text-[10px] font-bold font-mono tracking-widest text-center py-2 px-3 rounded-lg bg-white/2 border border-white/5 uppercase opacity-80">
                    {trapDirection === 'bearish'
                        ? '🚫 FAKEOUT RISK - CONSIDER CONTRARIAN LONG'
                        : trapDirection === 'bullish'
                            ? '🚫 FAKEOUT RISK - CONSIDER CONTRARIAN SHORT'
                            : '✅ NO ACTIVE RETAIL TRAP IDENTIFIED'
                    }
                </div>
            </div>
        </div>
    );
}

export default React.memo(TrapDetectionPanel);
