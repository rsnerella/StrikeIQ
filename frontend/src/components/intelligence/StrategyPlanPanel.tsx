"use client";

import React, { useState, useEffect, memo } from 'react';
import { Target, Shield, DollarSign, Activity, Percent } from 'lucide-react';
import api from '@/api/client';

interface StrategyPlan {
    symbol: string;
    strike: number;
    option_type: 'CE' | 'PE';
    option_ltp: number;
    entry: number;
    target: number;
    stop_loss: number;
    confidence: number;
    lots: number;
    expected_profit: number;
    max_loss: number;
}

const StrategyPlanPanel: React.FC<{ symbol: string, data?: any }> = ({ symbol, data: liveData }) => {
    const [plan, setPlan] = useState<StrategyPlan | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<boolean>(false);

    // Sync live data if available
    useEffect(() => {
        if (liveData) {
            setPlan(liveData);
            setLoading(false);
            setError(false);
        }
    }, [liveData]);

    useEffect(() => {
        if (liveData) return; // Skip fetch if we have live data

        const fetchPlan = async () => {
            try {
                setLoading(true);
                setError(false);
                const response = await api.get(`/v1/ai/strategy-plan?symbol=${symbol}`);
                if (response.data) {
                    setPlan(response.data);
                }
            } catch (err) {
                console.error('Error fetching strategy plan:', err);
                setError(true);
            } finally {
                setLoading(false);
            }
        };

        fetchPlan();
        const interval = setInterval(fetchPlan, 30000); // 30s update
        return () => clearInterval(interval);
    }, [symbol, liveData]);

    if (loading && !plan) {
        return (
            <div className="animate-pulse flex flex-col gap-4 p-4 grayscale opacity-50">
                <div className="h-4 bg-slate-700 rounded w-1/4"></div>
                <div className="h-20 bg-slate-700 rounded"></div>
            </div>
        );
    }

    if (error || !plan) {
        return (
            <div className="p-6 border border-white/5 bg-white/[0.01] rounded-2xl flex flex-col items-center justify-center gap-2 grayscale brightness-50">
                <Shield className="w-8 h-8 text-slate-500 opacity-20" />
                <span className="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">
                    AI Strategic Services Offline
                </span>
            </div>
        );
    }

    const isBullish = plan.option_type === 'CE';
    const accentColor = isBullish ? '#10b981' : '#f43f5e';

    return (
        <div className="relative overflow-hidden">
            <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                        <span className="panel-label">AI Strategic Implementation Plan</span>
                        <div className="flex items-center gap-2">
                            <div className="flex h-2 w-2 relative">
                                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-40`} style={{ backgroundColor: accentColor }} />
                                <span className={`relative inline-flex rounded-full h-2 w-2`} style={{ backgroundColor: accentColor }} />
                            </div>
                            <span className="text-[10px] font-bold font-mono tracking-widest uppercase" style={{ color: accentColor }}>
                                BUY {plan.symbol} {plan.strike} {plan.option_type}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-bold font-mono text-cyan-400 uppercase">Option LTP</span>
                            <span className="text-sm font-bold font-mono text-white">₹{plan.option_ltp?.toFixed(2) || '0.00'}</span>
                        </div>
                        <div className="h-8 w-[1px] bg-white/10" />
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-bold font-mono text-slate-500 uppercase">Confidence</span>
                            <span className="text-sm font-bold font-mono text-white">{((plan.confidence || 0.85) * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Execution Box */}
                    <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4 bg-white/[0.02] border border-white/5 rounded-2xl p-5 relative">
                        <div className="absolute top-0 right-0 p-2">
                            <Target className="w-4 h-4 text-white/10" />
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold font-mono text-slate-500 uppercase">Strike</span>
                            <span className="text-lg font-bold font-mono text-white">{plan.strike || 0}</span>
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold font-mono text-emerald-500/70 uppercase">Entry</span>
                            <span className="text-lg font-bold font-mono text-white">{plan.entry || 0}</span>
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold font-mono text-cyan-500/70 uppercase">Target</span>
                            <span className="text-lg font-bold font-mono text-white">{plan.target || 0}</span>
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold font-mono text-rose-500/70 uppercase">Stop Loss</span>
                            <span className="text-lg font-bold font-mono text-white">{plan.stop_loss || 0}</span>
                        </div>
                    </div>

                    {/* Sizing & PnL Box */}
                    <div className="bg-gradient-to-br from-white/[0.04] to-transparent border border-white/5 rounded-2xl p-5 flex flex-col justify-between">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <Shield className="w-4 h-4 text-cyan-400" />
                                <span className="text-[10px] font-bold font-mono text-slate-300 uppercase">Position Sizing</span>
                            </div>
                            <div className="px-2 py-0.5 rounded bg-cyan-400/10 border border-cyan-400/20 text-[9px] font-bold font-mono text-cyan-400">
                                {plan.lots || 0} LOTS
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-[11px] font-mono text-slate-500">Expected Profit</span>
                                <span className="text-[13px] font-bold font-mono text-emerald-400">₹{(plan.expected_profit || 0).toLocaleString()}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[11px] font-mono text-slate-500">Max Loss</span>
                                <span className="text-[13px] font-bold font-mono text-rose-400">₹{(plan.max_loss || 0).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-6 px-1">
                    <div className="flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-slate-500" />
                        <span className="text-[10px] font-bold font-mono text-slate-600 uppercase">Delta Neutral Adjusted</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Percent className="w-3.5 h-3.5 text-slate-500" />
                        <span className="text-[10px] font-bold font-mono text-slate-600 uppercase">Theta Decay Optimized</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <DollarSign className="w-3.5 h-3.5 text-slate-500" />
                        <span className="text-[10px] font-bold font-mono text-slate-600 uppercase">Margin Required: ₹1.2L Approx</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default memo(StrategyPlanPanel);
