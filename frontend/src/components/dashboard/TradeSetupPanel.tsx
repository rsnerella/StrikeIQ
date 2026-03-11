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

    const tradeSetupData = (data as any)?.analytics?.trade_setup;

    // Calculate trade setup
    const calculateTradeSetup = () => {
        // AI Real Options Trade (Exclusively)
        if (tradeSetupData) {
            return {
                direction: tradeSetupData.option_type === 'CE' ? 'BULLISH' : 'BEARISH',
                strike: tradeSetupData.strike,
                optionType: tradeSetupData.option_type,
                optionLtp: tradeSetupData.option_ltp,
                entry: tradeSetupData.entry,
                target: tradeSetupData.target,
                stopLoss: tradeSetupData.stop_loss,
                lots: tradeSetupData.lots,
                maxLoss: tradeSetupData.max_loss,
                expectedProfit: tradeSetupData.expected_profit,
                confidence: (tradeSetupData.confidence || 0.85) * 100,
                regime: structuralRegime ? structuralRegime.replace(/_/g, ' ').toUpperCase() : 'ALPHA OPTION SETUP',
                isRealOption: true
            };
        }

        return {
            direction: 'NEUTRAL',
            entry: 0,
            target: 0,
            stopLoss: 0,
            confidence: 0,
            regime: 'SEARCHING FOR ALPHA',
            isRealOption: false
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
    const risk = Math.abs((tradeSetup as any).entry - tradeSetup.stopLoss);
    const reward = Math.abs(tradeSetup.target - (tradeSetup as any).entry);
    const rrRatio = risk > 0 ? (reward / risk).toFixed(2) : '0.00';

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
                        {(tradeSetup as any).isRealOption ? `BUY ${(tradeSetup as any).optionType}` : tradeSetup.direction}
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
                        Option LTP
                    </div>
                    <div className="text-[15px] font-bold font-mono text-cyan-400">
                        {tradeSetup.isRealOption ? `₹${(tradeSetup as any).optionLtp.toFixed(2)}` : '--'}
                    </div>
                </div>

                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Market Bias
                    </div>
                    <div
                        className="text-[13px] font-bold font-mono tracking-tight uppercase truncate"
                        style={{ color: hasLiveData ? '#e2e8f0' : '#475569' }}
                    >
                        {bias}
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
                            <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                                {(tradeSetup as any).isRealOption ? `${(tradeSetup as any).strike} ${(tradeSetup as any).optionType} Entry` : 'Optimal Entry'}
                            </span>
                        </div>
                        <span className="text-[15px] font-bold font-mono tracking-tight text-blue-400 tabular-nums">
                            {(tradeSetup as any).entry.toFixed(2)}
                        </span>
                    </div>
                    {/* Lot Info if real option */}
                    {(tradeSetup as any).isRealOption && (
                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
                            <span className="text-[10px] font-mono text-slate-500 uppercase">Quantity</span>
                            <span className="text-[11px] font-bold font-mono text-white">{(tradeSetup as any).lots} LOTS</span>
                        </div>
                    )}
                </div>

                {/* Targets & SL */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(34,197,94,0.03)', border: '1px solid rgba(34,197,94,0.1)' }}>
                        <div className="text-[9px] font-bold font-mono text-green-500/70 uppercase mb-1">Target</div>
                        <div className="text-[14px] font-bold font-mono text-green-400">{(tradeSetup as any).target.toFixed(2)}</div>
                        <div className="text-[8px] font-mono text-green-500/50 mt-1">{rrRatio} RR</div>
                    </div>
                    <div className="rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(239,68,68,0.03)', border: '1px solid rgba(239,68,68,0.1)' }}>
                        <div className="text-[9px] font-bold font-mono text-red-500/70 uppercase mb-1">Stop Loss</div>
                        <div className="text-[14px] font-bold font-mono text-red-500">{(tradeSetup as any).stopLoss.toFixed(2)}</div>
                    </div>
                </div>

                {/* Profit/Loss projections for real options */}
                {(tradeSetup as any).isRealOption && (
                    <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-xl p-3 bg-red-500/5 border border-red-500/10">
                            <div className="text-[8px] font-mono text-red-500 uppercase">Max Loss</div>
                            <div className="text-[11px] font-bold font-mono text-red-400">₹{(tradeSetup as any).maxLoss}</div>
                        </div>
                        <div className="rounded-xl p-3 bg-green-500/5 border border-green-500/10">
                            <div className="text-[8px] font-mono text-green-500 uppercase">Exp. Profit</div>
                            <div className="text-[11px] font-bold font-mono text-green-400">₹{(tradeSetup as any).expectedProfit}</div>
                        </div>
                    </div>
                )}
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

