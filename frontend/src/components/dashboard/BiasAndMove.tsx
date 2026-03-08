"use client";
import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface BiasAndMoveProps {
    data: LiveMarketData | null;
    isSnapshotMode: boolean;
}

export function BiasPanel({ data }: { data: LiveMarketData | null }) {
    const biasLabel = (data as any)?.intelligence?.bias?.label;
    const biasScore = (data as any)?.intelligence?.bias?.score ?? 0;

    const getBiasConfig = (label: string) => {
        switch (label?.toUpperCase()) {
            case 'BULLISH':
                return { color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)', bgGradient: 'linear-gradient(90deg, #166534, #4ade80)' };
            case 'BEARISH':
                return { color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)', bgGradient: 'linear-gradient(90deg, #991b1b, #f87171)' };
            default:
                return { color: '#94a3b8', bgColor: 'rgba(148,163,184,0.08)', borderColor: 'rgba(148,163,184,0.18)', bgGradient: 'linear-gradient(90deg, #334155, #94a3b8)' };
        }
    };

    const config = getBiasConfig(biasLabel);

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
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Market Bias</SectionLabel>
                <span
                    className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full border uppercase"
                    style={{ background: config.bgColor, borderColor: config.borderColor, color: config.color, boxShadow: `0 0 10px ${config.color}15` }}
                >
                    {biasLabel ?? 'HOLD'}
                </span>
            </div>

            <div className="mb-6 rounded-xl p-4 transition-all hover:bg-white/5" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Strength Score
                    </span>
                    <span className="text-[16px] font-bold font-mono text-white tabular-nums">
                        {Math.abs(biasScore).toFixed(1)}
                    </span>
                </div>
                <div className="w-full h-1.5 rounded-full overflow-hidden bg-white/5">
                    <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{
                            width: `${Math.min(100, Math.abs(biasScore) * 10)}%`,
                            background: config.bgGradient,
                            boxShadow: `0 0 8px ${config.color}30`
                        }}
                    />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-auto">
                {[
                    { label: 'CONFIDENCE', value: Math.abs(biasScore) > 0.7 ? 'HIGH' : Math.abs(biasScore) > 0.4 ? 'MED' : 'LOW', color: Math.abs(biasScore) > 0.7 ? '#4ade80' : '#fb923c' },
                    { label: 'FLOW', value: biasLabel === 'BULLISH' ? 'BUYING' : biasLabel === 'BEARISH' ? 'SELLING' : 'FLAT', color: '#fff' },
                ].map(({ label, value, color }) => (
                    <div
                        key={label}
                        className="rounded-xl p-3 flex flex-col gap-1 transition-all hover:bg-white/5"
                        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                    >
                        <div className="text-[9px] font-bold font-mono tracking-widest text-slate-500 uppercase">{label}</div>
                        <div className="text-[12px] font-bold font-mono tracking-tight uppercase" style={{ color }}>{value}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export function ExpectedMovePanel({ data, isSnapshotMode }: { data: LiveMarketData | null; isSnapshotMode: boolean }) {
    const spot = (data as any)?.spot ?? 0;
    const expectedMove = (data as any)?.intelligence?.probability?.expected_move ?? 0;
    const breachProbability = (data as any)?.intelligence?.probability?.breach_probability ?? 0;

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
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Expected Move Range</SectionLabel>
                {isSnapshotMode && (
                    <span className="text-[9px] font-bold font-mono px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 tracking-widest uppercase">
                        RESTRICTED MODE
                    </span>
                )}
            </div>

            <div className="space-y-6">
                {/* Lower Bound */}
                <div className="relative">
                    <div className="flex items-center justify-between mb-3 px-1">
                        <div className="flex flex-col">
                            <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Lower Target (1σ)</span>
                            <span className="text-[20px] font-bold font-mono text-red-400 tracking-tighter tabular-nums">
                                {(spot - expectedMove).toFixed(2)}
                            </span>
                        </div>
                        <div className="h-10 w-px bg-white/5" />
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase text-right">Upper Target (1σ)</span>
                            <span className="text-[20px] font-bold font-mono text-green-400 tracking-tighter tabular-nums text-right">
                                {(spot + expectedMove).toFixed(2)}
                            </span>
                        </div>
                    </div>

                    <div className="relative h-4 rounded-full overflow-hidden border border-white/5" style={{ background: 'rgba(0,0,0,0.3)' }}>
                        <div
                            className="absolute inset-0 opacity-40"
                            style={{
                                background: 'linear-gradient(90deg, #f87171, rgba(99,102,241,0.2) 50%, #4ade80)'
                            }}
                        />
                        <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 flex items-center z-10">
                            <div className="w-1 h-full bg-white shadow-[0_0_8px_white]" />
                        </div>
                    </div>
                    <div className="flex justify-center mt-2">
                        <span className="text-[10px] font-bold font-mono text-slate-400 tracking-widest uppercase bg-white/5 px-2 py-0.5 rounded">
                            CURRENT SPOT: {spot.toFixed(2)}
                        </span>
                    </div>
                </div>

                {/* Risk Indicator */}
                <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/20">
                            <AlertTriangle className="w-4 h-4 text-orange-400" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Breach Risk</span>
                            <span className="text-[11px] font-mono text-slate-400 italic">Expansion beyond expected σ range</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="w-20 h-1.5 rounded-full bg-white/5 overflow-hidden">
                            <div
                                className="h-full rounded-full transition-all duration-1000 ease-out"
                                style={{
                                    width: `${breachProbability}%`,
                                    background: breachProbability > 40 ? 'linear-gradient(90deg, #fb923c, #f87171)' : 'linear-gradient(90deg, #1e293b, #fb923c)'
                                }}
                            />
                        </div>
                        <span className="text-[14px] font-bold font-mono text-white tracking-tight tabular-nums">
                            {breachProbability.toFixed(0)}%
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Keeping the combined component for compatibility if needed, but exports components separately
export function BiasAndMove({ data, isSnapshotMode }: BiasAndMoveProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-full">
            <div className="lg:col-span-4 h-full">
                <BiasPanel data={data} />
            </div>
            <div className="lg:col-span-8 h-full">
                <ExpectedMovePanel data={data} isSnapshotMode={isSnapshotMode} />
            </div>
        </div>
    );
}

