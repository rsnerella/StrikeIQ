"use client";
import React, { useState, useRef, useEffect } from 'react';
import { TrendingUp, TrendingDown, Target, Shield, Activity, Search } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import { useWSStore } from '../../core/ws/wsStore';

// TypeScript interfaces for performance data
interface PerformanceData {
    total_trades?: number;
    wins?: number;
    losses?: number;
    win_rate?: number;
    total_pnl?: number;
}

interface StrategyWeights {
    [key: string]: number;
}

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function TradeSetupPanel() {
    const [riskMode, setRiskMode] = useState<'SAFE' | 'AGGRESSIVE'>('SAFE');

    const toggleRiskMode = async () => {
        const nextMode = riskMode === 'SAFE' ? 'AGGRESSIVE' : 'SAFE';
        setRiskMode(nextMode);
        try {
            // Call backend API (using both possible paths for reliability)
            await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/set-risk-mode?mode=${nextMode}`);
        } catch (err) {
            console.error("Risk toggle failed:", err);
        }
    };

    // Law 7: Granular Store Subscriptions with null-safe pattern
    const regime       = useWSStore(s => s.regime        ?? 'RANGING')
    const bias         = useWSStore(s => s.bias          ?? 'NEUTRAL')
    const pcr          = useWSStore(s => s.pcr           ?? 0)
    const analytics     = useWSStore(s => s.analytics)      // FIX: Read analytics for strategy/confidence
    const lastUpdate   = useWSStore(s => s.lastUpdate)
    
    // 🔥 ADD PERFORMANCE DATA FROM STORE
    const performance = useWSStore(s => s.performance) as PerformanceData | null;
    const strategyWeights = useWSStore(s => s.strategy_weights) as StrategyWeights | null;
    
    const hasData      = lastUpdate > 0
    
    // STEP 2: READ CORRECT DATA
    const strategy = analytics?.strategy;
    const confidence = analytics?.confidence;
    const execution = analytics?.execution || {};

    const tradeScore =
      analytics?.metadata?.trade_score !== undefined
        ? analytics.metadata.trade_score
        : null

    // STEP 4: Only log on data changes (Moved to top to avoid hook violation)
    const prevStrategyRef = useRef(strategy);
    const prevAnalyticsRef = useRef(analytics);

    useEffect(() => {
        if (prevStrategyRef.current !== strategy || prevAnalyticsRef.current !== analytics) {
            console.log("[UI STRATEGY DATA]", strategy, confidence);
            console.log("[UI DATA]", analytics);

            prevStrategyRef.current = strategy;
            prevAnalyticsRef.current = analytics;
        }
    }, [strategy, analytics]);

    // 🔥 STEP 4: UI GUARD (IMPORTANT) - Prevent blank UI
    if (!performance && !strategyWeights && !hasData) {
        return (
            <div className="trading-panel h-full flex items-center justify-center">
                <div className="text-center">
                    <div className="text-gray-400 text-sm mb-2">🔄</div>
                    <div className="text-gray-400 text-sm">Waiting for AI data...</div>
                    <div className="text-gray-500 text-xs mt-1">Performance metrics loading...</div>
                </div>
            </div>
        );
    }
    
    // STEP 6: CRITICAL CHECK - Debug full store if strategy undefined
    if (!strategy) {
        console.log("[CRITICAL] Strategy undefined - full store:", useWSStore.getState())
        console.log("[CRITICAL] Analytics path check:", {
            analytics: analytics,
            analyticsStrategy: analytics?.strategy,
            analyticsConfidence: analytics?.confidence
        })
    }

    // const score = analytics?.metadata?.trade_score || 0  // REMOVED IN FAVOR OF tradeScore
    const isNoTrade = (
        !strategy ||
        strategy === 'NO_TRADE' ||
        strategy === 'NEUTRAL' ||
        (confidence ?? 0) < 0.18 ||
        !execution.strike
    )
    const isBullish = strategy === 'BUY' || (strategy?.includes('BUY'));
    const isBearish = strategy === 'SELL' || (strategy?.includes('SELL'));
    
    // Directional Styling
    const directionStyle = isBullish 
        ? { color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)', icon: <TrendingUp className="w-4 h-4" /> }
        : isBearish 
        ? { color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)', icon: <TrendingDown className="w-4 h-4" /> }
        : { color: '#94a3b8', bgColor: 'rgba(148,163,184,0.08)', borderColor: 'rgba(148,163,184,0.18)', icon: <Activity className="w-4 h-4" /> };

    const entryDisplay = execution?.entry > 0
      ? `₹${execution.entry.toFixed(2)}` 
      : '—'

    const slDisplay = execution?.stop_loss > 0
      ? `₹${execution.stop_loss.toFixed(2)}` 
      : '—'

    const targetDisplay = execution?.target > 0
      ? `₹${execution.target.toFixed(2)}` 
      : '—'

    const reasonDisplay = analytics?.reasoning?.[0]
      ?? (hasData
            ? 'No high-conviction setup at current levels'
            : '—')

    // Risk/Reward (Law 2 Safeguard)
    const riskValue = Math.abs((execution?.entry || 0) - (execution?.stop_loss || 0));
    const rewardValue = Math.abs((execution?.target || 0) - (execution?.entry || 0));
    const rrRatioValue = riskValue > 0 ? (rewardValue / riskValue).toFixed(2) : '—';

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {/* Header - ALWAYS VISIBLE */}
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Institutional Trade Setup</SectionLabel>
                <div className="flex items-center gap-3">
                    {/* Risk Mode Toggle - ALWAYS VISIBLE */}
                    <button 
                        onClick={toggleRiskMode}
                        className={`text-[9px] font-bold font-mono px-3 py-1 rounded-full border transition-all flex items-center gap-2 ${
                            riskMode === 'SAFE' 
                            ? 'bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20' 
                            : 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                        }`}
                        title={`Current Mode: ${riskMode}`}
                    >
                        <span className={`w-1.5 h-1.5 rounded-full ${riskMode === 'SAFE' ? 'bg-green-400' : 'bg-red-400 animate-pulse'}`} />
                        {riskMode}
                    </button>

                    {/* Strategy Badge - ONLY IF ACTIVE TRADE */}
                    {!isNoTrade && hasData && (
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
                            {execution?.strike ? `${strategy} ${execution.strike} ${execution.option_type}` : strategy}
                            {tradeScore !== null && (
                                <span className="ml-2 opacity-60">
                                    {(tradeScore * 100).toFixed(0)}%
                                </span>
                            )}
                        </span>
                    )}
                </div>
            </div>

            {/* CONTENT AREA */}
            {!hasData ? (
                /* Loading State */
                <div className="flex-grow flex flex-col justify-center items-center gap-4 opacity-60">
                    <Search className="w-8 h-8 text-blue-500/50 animate-bounce" />
                    <div className="flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-blue-400 uppercase">
                            Initializing Market Data...
                        </span>
                        <div className="flex gap-1">
                            <SkeletonPulse className="w-2 h-2" />
                            <SkeletonPulse className="w-2 h-2" />
                            <SkeletonPulse className="w-2 h-2" />
                        </div>
                    </div>
                </div>
            ) : isNoTrade ? (
                /* No Trade State */
                <div className="flex-grow flex flex-col justify-center items-center gap-4 opacity-60">
                    <Shield className="w-8 h-8 text-slate-400/50" />
                    <div className="flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-400 uppercase">
                            No high conviction setup
                        </span>
                        <div className="text-[8px] font-mono text-slate-500 text-center">
                            Market conditions not meeting entry criteria
                        </div>
                        <div className="text-[8px] font-mono text-slate-600 text-center">
                            PCR: {pcr.toFixed(2)} | Regime: {regime}
                        </div>
                    </div>
                </div>
            ) : (
                /* Active Trade State */
                <>
                    {/* Market Context Grid */}
                    <div className="grid grid-cols-2 gap-4 mb-6">
                        <div className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/3 border border-white/5 bg-white/[0.02]">
                            <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">Regime</div>
                            <div className="text-[14px] font-bold font-mono text-cyan-400 uppercase truncate">
                                {regime.replace(/_/g, ' ')}
                            </div>
                        </div>

                        <div className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/3 border border-white/5 bg-white/[0.02]">
                            <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">Market Bias</div>
                            <div className={`text-[14px] font-bold font-mono tracking-tight uppercase truncate ${isBullish ? 'text-green-400' : isBearish ? 'text-red-400' : 'text-slate-300'}`}>
                                {bias}
                            </div>
                        </div>
                    </div>
                    
                    {/* Probabilistic Score */}
                    {tradeScore !== null && tradeScore !== 0 && (
                        <div className="rounded-xl p-3 flex items-center justify-between mb-4 border border-white/5 bg-white/[0.02]">
                            <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">Probabilistic Score</div>
                            <div className={`text-[14px] font-bold font-mono tracking-tight tabular-nums ${tradeScore > 0 ? 'text-green-400' : tradeScore < 0 ? 'text-red-400' : 'text-slate-300'}`}>
                                {tradeScore > 0 ? '+' : ''}{tradeScore.toFixed(2)}
                            </div>
                        </div>
                    )}

                    {/* Trade Levels Section */}
                    <div className="space-y-4 mb-6 flex-grow">
                        {/* Entry Zone */}
                        <div className="rounded-xl p-4 border border-white/10 bg-blue-500/[0.03]">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Target className="w-3.5 h-3.5 text-blue-400" />
                                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-400">Optimal Entry</span>
                                </div>
                                <span className="text-[16px] font-bold font-mono tracking-tight text-blue-400 tabular-nums">
                                    {entryDisplay}
                                </span>
                            </div>
                        </div>

                        {/* Targets & SL */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="rounded-xl p-4 border border-green-500/10 bg-green-500/[0.03]">
                                <div className="text-[9px] font-bold font-mono text-green-500/70 uppercase mb-1">Target</div>
                                <div className="text-[14px] font-bold font-mono text-green-400">
                                    {targetDisplay}
                                </div>
                                <div className="text-[8px] font-mono text-green-500/50 mt-1">{rrRatioValue} RR</div>
                            </div>
                            <div className="rounded-xl p-4 border border-red-500/10 bg-red-500/[0.03]">
                                <div className="text-[9px] font-bold font-mono text-red-500/70 uppercase mb-1">Stop Loss</div>
                                <div className="text-[14px] font-bold font-mono text-red-500">
                                    {slDisplay}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 🔥 PERFORMANCE DISPLAY */}
                    {(performance || strategyWeights) && (
                        <div className="mt-4 space-y-3">
                            {performance && (
                                <div className="rounded-xl p-3 border border-white/5 bg-white/[0.02]">
                                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500 mb-2">📊 Performance</div>
                                    <div className="grid grid-cols-3 gap-2 text-[11px]">
                                        <div>
                                            <div className="text-slate-400">Trades</div>
                                            <div className="font-bold text-white">{performance?.total_trades || 0}</div>
                                        </div>
                                        <div>
                                            <div className="text-slate-400">Win Rate</div>
                                            <div className="font-bold text-green-400">{performance?.win_rate?.toFixed(1) || 0}%</div>
                                        </div>
                                        <div>
                                            <div className="text-slate-400">PnL</div>
                                            <div className={`font-bold ${(performance?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {(performance?.total_pnl || 0) >= 0 ? '+' : ''}{(performance?.total_pnl || 0).toFixed(1)}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            
                            {strategyWeights && (
                                <div className="rounded-xl p-3 border border-white/5 bg-white/[0.02]">
                                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500 mb-2">🧠 Strategy Weights</div>
                                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                                        {Object.entries(strategyWeights).map(([key, value]) => (
                                            <div key={key} className="flex justify-between">
                                                <span className="text-slate-400">{key}:</span>
                                                <span className="font-bold text-white">{typeof value === 'number' ? value.toFixed(2) : '0.00'}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Reason Footer */}
                    <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                        <div className="text-[10px] font-medium font-mono tracking-tight p-3 rounded-lg bg-white/5 border border-white/10 text-slate-300 leading-relaxed min-h-[60px]">
                            {reasonDisplay}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

export default React.memo(TradeSetupPanel);

