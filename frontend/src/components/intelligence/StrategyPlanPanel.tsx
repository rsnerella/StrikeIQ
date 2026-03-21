"use client";

import React, { memo } from 'react';
import { Target, Shield, DollarSign, Activity, Percent } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';
import { SectionLabel } from '../dashboard/StatCards';
import { CARD_HOVER_BORDER } from '../dashboard/DashboardTypes';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

const StrategyPlanPanel: React.FC = () => {
    // Law 7: Separate Store Subscriptions to prevent infinite loops
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const analytics = useWSStore(s => s.analytics);  // FIX: Read from analytics field
    const biasStrength = useWSStore(s => s.biasStrength ?? 0);
    
    const confidence = analytics?.confidence ?? biasStrength;
    
    // DEBUG LOG
    console.log("[UI DATA]", analytics)

    const gamma = analytics?.gamma ?? null
    const oi = analytics?.oi ?? null
    const liquidity = analytics?.liquidity ?? null
    const volatility = analytics?.volatility ?? null

    const hasData = lastUpdate > 0;
    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col justify-center items-center gap-6 opacity-40">
                <Activity className="w-8 h-8 text-slate-700 animate-pulse mb-2" />
                <span className="text-[10px] font-black font-mono tracking-[0.25em] text-slate-600 uppercase text-center max-w-[180px]">
                    Initializing Neural Pipeline...
                </span>
            </div>
        );
    }

    if (!analytics) {
        return (
            <div className="trading-panel h-full flex flex-col justify-center items-center gap-6 opacity-40">
                <Activity className="w-8 h-8 text-slate-700 animate-pulse mb-2" />
                <span className="text-[10px] font-black font-mono tracking-[0.25em] text-slate-600 uppercase text-center max-w-[180px]">
                    Awaiting Market Structure Analysis
                </span>
            </div>
        );
    }

    const isLowConviction = (analytics.confidence ?? 0) < 0.65;
    const isBullish = (analytics.bias || '').toUpperCase() === 'BULLISH';
    
    // Theme selection: Muted for low conviction, Vibrant for high
    const accentColor = isLowConviction ? '#64748b' : (isBullish ? '#10b981' : '#f43f5e');
    const headerTitle = isLowConviction ? "Neural Hypothesis Matrix" : "AI Strategic Architecture";
    const statusLabel = isLowConviction ? "OBSERVING" : "ANALYZE";

    return (
        <div
            className={`trading-panel h-full flex flex-col transition-all duration-700 ${isLowConviction ? 'grayscale-[0.5] opacity-95' : ''}`}
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {isLowConviction && (
                <div className="absolute top-0 right-0 px-4 py-1.5 bg-slate-800/80 rounded-bl-2xl border-b border-l border-white/10 z-20 backdrop-blur-md">
                    <span className="text-[9px] font-black font-mono text-slate-400 tracking-[0.2em] uppercase leading-none">Hypothesis</span>
                </div>
            )}

            <div className="flex flex-col gap-6 h-full">
                {/* Header Cluster */}
                <div className="flex items-center justify-between mb-2">
                    <div className="flex flex-col gap-1.5">
                        <SectionLabel>{headerTitle}</SectionLabel>
                        <div className="flex items-center gap-3">
                            <span className="text-[12px] font-black font-mono tracking-[0.1em] uppercase" style={{ color: accentColor }}>
                                {statusLabel}: {analytics.strategy || 'ANALYZING'}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest opacity-60">Bias</span>
                            <span className={`text-lg font-black font-mono tabular-nums ${isLowConviction ? 'text-slate-400' : 'text-white'}`}>
                                {analytics.bias}
                            </span>
                        </div>
                        <div className="h-8 w-[1px] bg-white/10" />
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest opacity-60">Confidence</span>
                            <span className={`text-lg font-black font-mono tabular-nums ${isLowConviction ? 'text-slate-400' : 'text-white'}`}>
                                {(analytics.confidence * 100).toFixed(1)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Component Analysis */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                    {[
                        { label: 'Gamma', val: gamma !== null ? gamma.toFixed(2) : '—', color: 'text-violet-400' },
                        { label: 'OI', val: oi !== null ? oi.toFixed(2) : '—', color: 'text-blue-400' },
                        { label: 'Liquidity', val: liquidity !== null ? liquidity.toFixed(2) : '—', color: 'text-emerald-400' },
                        { label: 'Volatility', val: volatility !== null ? volatility.toFixed(2) : '—', color: 'text-orange-400' }
                    ].map((item, i) => (
                        <div key={i} className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 flex flex-col gap-1">
                            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">{item.label}</span>
                            <span className={`text-sm font-black font-mono tabular-nums ${item.color}`}>{item.val}</span>
                        </div>
                    ))}
                </div>

                {/* Reasoning */}
                <div className="p-4 rounded-xl border border-slate-500/10 bg-slate-500/[0.03] space-y-2">
                    <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Analysis</span>
                    <div className="text-[8px] font-mono text-slate-300 leading-relaxed">
                        {analytics.reasoning?.map((reason, index) => (
                            <div key={index} className="flex items-start gap-2 mb-1">
                                <span className="text-slate-500 mt-0.5">•</span>
                                <span>{reason}</span>
                            </div>
                        )) || 'No analysis available'}
                    </div>
                </div>

                {/* Market Regime */}
                <div className="p-4 rounded-xl border border-cyan-500/10 bg-cyan-500/[0.03]">
                    <span className="text-[9px] font-bold font-mono text-cyan-500/70 uppercase mb-2">Market Regime</span>
                    <div className="text-[14px] font-bold font-mono text-cyan-400 uppercase">
                        {analytics.regime || 'UNKNOWN'}
                    </div>
                </div>

                {/* Trade Score Probability */}
                <div className="mt-auto pt-4 border-t border-white/5">
                    <div className="flex items-center justify-between">
                        <span className="text-[8px] font-bold font-mono text-slate-500 uppercase">Trade Quality Score</span>
                        <span className={`text-[14px] font-bold font-mono tabular-nums ${isLowConviction ? 'text-slate-400' : 'text-green-400'}`}>
                            {((analytics.metadata?.trade_score ?? 0) * 100).toFixed(1)}%
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default memo(StrategyPlanPanel);
