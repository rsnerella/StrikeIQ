"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Target, Shield, Activity } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface TradeSetupPanelProps {
    data: LiveMarketData | null;
}

export function TradeSetupPanel({ data }: TradeSetupPanelProps) {
    // Extract trade setup metrics from intelligence and analytics data
    const bias = (data as any)?.intelligence?.bias?.label || 'neutral';
    const structuralRegime = (data as any)?.intelligence?.structural_regime || '';
    const tradeSuggestion = (data as any)?.intelligence?.trade_suggestion;
    const expectedMove = (data as any)?.intelligence?.expected_move || 0;
    const supportLevel = (data as any)?.intelligence?.support_level || 0;
    const resistanceLevel = (data as any)?.intelligence?.resistance_level || 0;
    const breachProbability = (data as any)?.intelligence?.breach_probability || 0;
    const spot = (data as any)?.spot || 0;
    const regimeConfidence = (data as any)?.intelligence?.regime_confidence || 0;

    // True if we have live market data
    const hasLiveData = spot > 0;

    // Calculate trade setup
    const calculateTradeSetup = () => {
        if (tradeSuggestion) {
            return {
                direction: tradeSuggestion.signal?.replace('BUY_', '') || 'NEUTRAL',
                entryZone: tradeSuggestion.entry || spot,
                target1: tradeSuggestion.target || spot,
                target2: tradeSuggestion.target || spot, // Fallback to target1
                stopLoss: tradeSuggestion.stop_loss || spot,
                confidence: tradeSuggestion.confidence || (hasLiveData ? regimeConfidence : 0),
                regime: tradeSuggestion.regime || (structuralRegime ? structuralRegime.replace(/_/g, ' ').toUpperCase() : 'SCANNING')
            };
        }

        const isBullish = bias?.toLowerCase() === 'bullish';
        const isBearish = bias?.toLowerCase() === 'bearish';
        const isPositiveGamma = structuralRegime?.toLowerCase() === 'positive_gamma';

        // Entry zone calculation
        let entryZone = spot;
        if (isBullish && supportLevel > 0) {
            entryZone = supportLevel + (spot - supportLevel) * 0.3;
        } else if (isBearish && resistanceLevel > 0) {
            entryZone = resistanceLevel - (resistanceLevel - spot) * 0.3;
        }

        // Targets calculation
        let target1 = spot;
        let target2 = spot;
        if (isBullish) {
            target1 = spot + expectedMove * 0.5;
            target2 = spot + expectedMove * 0.8;
        } else if (isBearish) {
            target1 = spot - expectedMove * 0.5;
            target2 = spot - expectedMove * 0.8;
        }

        // Stop loss calculation
        let stopLoss = spot;
        if (isBullish && supportLevel > 0) {
            stopLoss = supportLevel - (spot - supportLevel) * 0.1;
        } else if (isBearish && resistanceLevel > 0) {
            stopLoss = resistanceLevel + (resistanceLevel - spot) * 0.1;
        }

        // Confidence calculation — zero out when no live data
        let confidence = hasLiveData ? regimeConfidence : 0;
        if (hasLiveData) {
            if (breachProbability < 30) confidence += 10;
            if (isPositiveGamma && isBullish) confidence += 5;
            if (!isPositiveGamma && isBearish) confidence += 5;
            confidence = Math.min(95, Math.max(25, confidence));
        }

        // Regime label: show 'AWAITING DATA' instead of 'UNKNOWN'
        const regimeLabel = !hasLiveData
            ? 'AWAITING DATA'
            : structuralRegime
                ? structuralRegime.replace(/_/g, ' ').toUpperCase()
                : 'SCANNING';

        return {
            direction: isBullish ? 'BULLISH' : isBearish ? 'BEARISH' : 'NEUTRAL',
            entryZone,
            target1,
            target2,
            stopLoss,
            confidence,
            regime: regimeLabel
        };
    };

    const tradeSetup = calculateTradeSetup();

    // Get direction styling
    const getDirectionStyle = (direction: string) => {
        switch (direction.toLowerCase()) {
            case 'bullish':
                return { color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)', icon: <TrendingUp className="w-4 h-4" /> };
            case 'bearish':
                return { color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)', icon: <TrendingDown className="w-4 h-4" /> };
            default:
                return { color: '#94a3b8', bgColor: 'rgba(148,163,184,0.08)', borderColor: 'rgba(148,163,184,0.18)', icon: <Activity className="w-4 h-4" /> };
        }
    };

    const directionStyle = getDirectionStyle(tradeSetup.direction);

    // Risk/Reward calculation
    const risk = Math.abs(tradeSetup.entryZone - tradeSetup.stopLoss);
    const reward1 = Math.abs(tradeSetup.target1 - tradeSetup.entryZone);
    const reward2 = Math.abs(tradeSetup.target2 - tradeSetup.entryZone);
    const rrRatio1 = risk > 0 ? (reward1 / risk).toFixed(2) : '0.00';
    const rrRatio2 = risk > 0 ? (reward2 / risk).toFixed(2) : '0.00';

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
                <SectionLabel>Alpha Trade Setup</SectionLabel>
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
                        {tradeSetup.direction}
                    </span>
                </div>
            </div>

            {/* Market Context Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Signal Bias
                    </div>
                    <div className="text-[13px] font-bold text-white tracking-tight uppercase">
                        {bias}
                    </div>
                </div>

                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Market Regime
                    </div>
                    <div
                        className="text-[13px] font-bold font-mono tracking-tight uppercase truncate"
                        style={{ color: hasLiveData ? '#e2e8f0' : '#475569' }}
                    >
                        {tradeSetup.regime}
                    </div>
                </div>
            </div>

            {/* Trade Levels Section */}
            <div className="space-y-4 mb-6">
                {/* Entry Zone */}
                <div className="rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            <Target className="w-3.5 h-3.5 text-blue-400" />
                            <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">Optimal Entry</span>
                        </div>
                        <span className="text-[15px] font-bold font-mono tracking-tight text-blue-400 tabular-nums">
                            {tradeSetup.entryZone.toFixed(2)}
                        </span>
                    </div>
                    <div className="w-full h-1 rounded-full bg-blue-500/20" />
                </div>

                {/* Targets */}
                <div className="rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500 mb-3">Profit Objectives</div>
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono text-slate-400">TARGET 1 (CONSERVATIVE)</span>
                            <div className="flex items-center gap-3">
                                <span className="text-[13px] font-bold font-mono text-green-400 tabular-nums">{tradeSetup.target1.toFixed(2)}</span>
                                <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded bg-green-500/10 text-green-500 border border-green-500/20">{rrRatio1} RR</span>
                            </div>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono text-slate-400">TARGET 2 (AGGRESSIVE)</span>
                            <div className="flex items-center gap-3">
                                <span className="text-[13px] font-bold font-mono text-green-400 tabular-nums">{tradeSetup.target2.toFixed(2)}</span>
                                <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded bg-green-500/10 text-green-500 border border-green-500/20">{rrRatio2} RR</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stop Loss */}
                <div className="rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(239,68,68,0.03)', border: '1px solid rgba(239,68,68,0.1)' }}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Shield className="w-3.5 h-3.5 text-red-500" />
                            <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-red-500/70">Hard Stop Loss</span>
                        </div>
                        <span className="text-[15px] font-bold font-mono tracking-tight text-red-500 tabular-nums">
                            {tradeSetup.stopLoss.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Confidence & RR Summary Footer */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Activity className="w-4 h-4 text-slate-500" />
                        <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Signal Confidence</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="w-16 h-1.5 rounded-full bg-white/5 overflow-hidden">
                            <div
                                className="h-full rounded-full transition-all duration-1000 ease-out"
                                style={{
                                    width: `${tradeSetup.confidence}%`,
                                    background: tradeSetup.confidence === 0
                                        ? 'transparent'
                                        : `linear-gradient(90deg, #1e293b, ${tradeSetup.confidence >= 70 ? '#4ade80' : tradeSetup.confidence >= 50 ? '#fb923c' : '#94a3b8'})`
                                }}
                            />
                        </div>
                        <span className="text-[12px] font-bold font-mono tracking-tight"
                            style={{ color: tradeSetup.confidence === 0 ? '#475569' : '#fff' }}
                        >
                            {tradeSetup.confidence === 0 ? '--' : `${tradeSetup.confidence.toFixed(0)}%`}
                        </span>
                    </div>
                </div>

                <div className="text-[10px] font-bold font-mono tracking-widest text-center py-2 px-3 rounded-lg bg-blue-500/5 border border-blue-500/10 uppercase text-blue-400/80">
                    {tradeSuggestion?.reason ? (
                        <span className="flex flex-col gap-1">
                            <span className="opacity-60">{tradeSetup.direction === 'NEUTRAL' ? 'SCANNING' : `${tradeSetup.direction} CONFIRMED`}</span>
                            <span className="text-[9px] lowercase italic">{tradeSuggestion.reason}</span>
                        </span>
                    ) : (
                        tradeSetup.direction === 'NEUTRAL'
                            ? 'WAIT FOR STRUCTURAL CONFIRMATION'
                            : `HIGH CONVICTION ${tradeSetup.direction} ASCERTAINED`
                    )}
                </div>
            </div>
        </div>
    );
}

export default React.memo(TradeSetupPanel);

