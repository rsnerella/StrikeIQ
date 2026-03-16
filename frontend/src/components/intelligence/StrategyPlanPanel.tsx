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
    // Law 7: Granular Store Subscriptions
    const lastUpdate    = useWSStore(s => s.lastUpdate);
    const plan          = useWSStore(s => s.tradePlan);
    const confidence    = useWSStore(s => s.biasStrength ?? 0);

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

    if (!plan) {
        return (
            <div className="trading-panel h-full flex flex-col justify-center items-center gap-6 opacity-40">
                <Activity className="w-8 h-8 text-slate-700 animate-pulse mb-2" />
                <span className="text-[10px] font-black font-mono tracking-[0.25em] text-slate-600 uppercase text-center max-w-[180px]">
                    Awaiting Market Structure Confluence
                </span>
            </div>
        );
    }

    const isLowConviction = (plan.conviction || '').toUpperCase() === 'LOW';
    const isBullish = (plan.direction || '').toUpperCase() === 'CE' || (plan.direction || '').toUpperCase() === 'BULLISH';
    
    // Theme selection: Muted for low conviction, Vibrant for high
    const accentColor = isLowConviction ? '#64748b' : (isBullish ? '#10b981' : '#f43f5e');
    const headerTitle = isLowConviction ? "Neural Hypothesis Matrix" : "AI Strategic Architecture";
    const statusLabel = isLowConviction ? "OBSERVING" : "ALLOCATE";

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
                                {statusLabel}: {plan.strike || '—'}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest opacity-60">LTP</span>
                            <span className="text-lg font-black font-mono text-white tabular-nums">₹{(plan.premium || 0).toFixed(2)}</span>
                        </div>
                        <div className="h-8 w-[1px] bg-white/10" />
                        <div className="flex flex-col items-end">
                            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest opacity-60">Alpha</span>
                            <span className={`text-lg font-black font-mono tabular-nums ${isLowConviction ? 'text-slate-400' : 'text-white'}`}>
                                {(confidence * 100).toFixed(1)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Tactical Matrix Cluster */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                    {[
                        { label: 'Direction', val: plan.direction || '—', color: isBullish ? 'text-green-400' : 'text-red-400' },
                        { label: 'Entry', val: plan.entry ? `₹${plan.entry.toFixed(2)}` : '—', color: 'text-emerald-400' },
                        { label: 'Target', val: plan.target ? `₹${plan.target.toFixed(2)}` : '—', color: 'text-cyan-400' },
                        { label: 'Stop Loss', val: plan.stop_loss ? `₹${plan.stop_loss.toFixed(2)}` : '—', color: 'text-rose-400' }
                    ].map((item, i) => (
                        <div key={i} className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5 flex flex-col gap-1">
                            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">{item.label}</span>
                            <span className={`text-sm font-black font-mono tabular-nums uppercase ${item.color}`}>{item.val}</span>
                        </div>
                    ))}
                </div>

                {/* Final Risk Module */}
                <div className="p-4 rounded-xl border border-blue-500/10 bg-blue-500/[0.03] space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Shield className="w-3.5 h-3.5 text-blue-400" />
                            <span className="text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest">Sizing</span>
                        </div>
                        <span className="text-[14px] font-bold font-mono text-blue-400 tabular-nums">
                            {plan.lots || 0} Units
                        </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/5">
                        <div className="flex flex-col">
                            <span className="text-[8px] font-bold font-mono text-slate-500 uppercase">Est. P/L</span>
                            <span className={`text-sm font-black font-mono tabular-nums ${isLowConviction ? 'text-slate-500' : 'text-green-400'}`}>
                                ₹{(plan.expected_profit || 0).toLocaleString()}
                            </span>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-[8px] font-bold font-mono text-slate-500 uppercase">Exposure</span>
                            <span className={`text-sm font-black font-mono tabular-nums ${isLowConviction ? 'text-slate-500' : 'text-rose-400'}`}>
                                ₹{(plan.max_loss || 0).toLocaleString()}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Integrity Markers */}
                <div className="flex items-center justify-between px-1 mt-auto pt-4 border-t border-white/5 pb-1">
                    {[
                        { icon: <Activity className="w-3 h-3" />, label: 'Delta' },
                        { icon: <Percent className="w-3 h-3" />, label: 'Theta' },
                        { icon: <DollarSign className="w-3 h-3" />, label: 'LBM' }
                    ].map((tag, i) => (
                        <div key={i} className="flex items-center gap-1.5 opacity-40 hover:opacity-100 transition-opacity cursor-help">
                            <div className="text-slate-400">{tag.icon}</div>
                            <span className="text-[8px] font-bold font-mono text-slate-500 uppercase tracking-widest">{tag.label}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default memo(StrategyPlanPanel);
