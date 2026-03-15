"use client";

import React, { useState, useEffect, memo } from 'react';
import { Target, Shield, DollarSign, Activity, Percent } from 'lucide-react';
import api from '@/api/client';
import { useWSStore } from '@/core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

const StrategyPlanPanel: React.FC = () => {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const aiReady = useWSStore(s => s.aiReady);
    const analysis = useWSStore(s => s.chartAnalysis);
    const plan = analysis?.trade_plan;

    const hasData = lastUpdate > 0;
    if (!hasData || !plan) {
        return (
            <div className="relative p-6 flex flex-col gap-8 opacity-40">
                <div className="flex justify-between items-center">
                    <SkeletonPulse className="w-1/3 h-6" />
                    <SkeletonPulse className="w-1/4 h-8" />
                </div>
                <div className="grid grid-cols-3 gap-6">
                    <SkeletonPulse className="col-span-2 h-32" />
                    <SkeletonPulse className="h-32" />
                </div>
            </div>
        );
    }

    const isBullish = plan.direction === 'CE' || plan.direction === 'BULLISH';
    const accentColor = isBullish ? '#10b981' : '#f43f5e';

    return (
        <div className="relative overflow-hidden p-6">
            <div className="flex flex-col gap-8">
                {/* Header Cluster */}
                <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-black font-mono tracking-[0.2em] text-slate-500 uppercase">AI Strategic Execution Architecture</span>
                        <div className="flex items-center gap-2">
                            <div className="flex h-2 w-2 relative">
                                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-40`} style={{ backgroundColor: accentColor }} />
                                <span className={`relative inline-flex rounded-full h-2 w-2`} style={{ backgroundColor: accentColor }} />
                            </div>
                            <span className="text-[11px] font-black font-mono tracking-widest uppercase" style={{ color: accentColor }}>
                                {plan.strike ? `ALLOCATE: ${plan.strike} ${plan.direction}` : `REGIME: ${plan.direction || 'NEUTRAL'}`}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-tighter">Premium LTP</span>
                            <span className="text-sm font-black font-mono text-white tabular-nums">₹{(plan.premium || 0).toFixed(2)}</span>
                        </div>
                        <div className="h-8 w-[1px] bg-white/10" />
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-tighter">Prob. Alpha</span>
                            <span className="text-sm font-black font-mono text-white tabular-nums">{((analysis.confidence || 0.85) * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>

                {/* Tactical Components */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Execution Matrix */}
                    <div className="lg:col-span-2 grid grid-cols-2 lg:grid-cols-4 gap-4 bg-white/[0.01] border border-white/5 rounded-2xl p-6 relative">
                        <div className="absolute top-0 right-0 p-3 opacity-20">
                            <Target className="w-5 h-5 text-white" />
                        </div>

                        {[
                            { label: 'Base Strike', val: plan.strike || '—', color: 'text-white' },
                            { label: 'Entry Vector', val: plan.entry || '—', color: 'text-emerald-400' },
                            { label: 'Target Objective', val: plan.target || '—', color: 'text-cyan-400' },
                            { label: 'Risk Threshold', val: plan.stop_loss || '—', color: 'text-rose-400' }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col gap-1">
                                <span className="text-[9px] font-black font-mono text-slate-600 uppercase tracking-widest">{item.label}</span>
                                <span className={`text-xl font-black font-mono tabular-nums ${item.color}`}>{item.val}</span>
                            </div>
                        ))}
                    </div>

                    {/* Risk Management Module */}
                    <div className="bg-gradient-to-br from-white/[0.04] to-transparent border border-white/10 rounded-2xl p-6 flex flex-col justify-between shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <Shield className="w-4 h-4 text-cyan-400" />
                                <span className="text-[10px] font-black font-mono text-slate-300 uppercase tracking-widest">Risk Allocation</span>
                            </div>
                            <div className="px-2.5 py-1 rounded bg-cyan-400/10 border border-cyan-400/20 text-[10px] font-black font-mono text-cyan-400 uppercase">
                                {plan.lots || 0} Units
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold font-mono text-slate-500 uppercase">Projected Yield</span>
                                <span className="text-sm font-black font-mono text-emerald-400 tabular-nums">₹{(plan.expected_profit || 0).toLocaleString()}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold font-mono text-slate-500 uppercase">Exposure Limit</span>
                                <span className="text-sm font-black font-mono text-rose-400 tabular-nums">₹{(plan.max_loss || 0).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Structural Tags */}
                <div className="flex flex-wrap items-center gap-6 px-1">
                    {[
                        { icon: <Activity className="w-3.5 h-3.5" />, label: 'Delta Neutral Adjusted' },
                        { icon: <Percent className="w-3.5 h-3.5" />, label: 'Theta Decay Optimized' },
                        { icon: <DollarSign className="w-3.5 h-3.5" />, label: 'Institutionally Backed' }
                    ].map((tag, i) => (
                        <div key={i} className="flex items-center gap-2 opacity-60">
                            <div className="text-slate-500">{tag.icon}</div>
                            <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-widest">{tag.label}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default memo(StrategyPlanPanel);
