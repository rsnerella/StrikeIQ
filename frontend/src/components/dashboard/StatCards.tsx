"use client";
import React from 'react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

// ── Shared helpers ────────────────────────────────────────────────────────────
export function SectionLabel({ children }: { children: React.ReactNode }) {
    return (
        <div
            className="text-[10px] font-bold tracking-[0.22em] uppercase"
            style={{ color: 'rgba(148,163,184,0.50)', fontFamily: "'JetBrains Mono', monospace" }}
        >
            {children}
        </div>
    );
}

export function StatCard({
    label, value, sub, accent = '#00E5FF',
}: { label: string; value: React.ReactNode; sub?: React.ReactNode; accent?: string }) {
    return (
        <div
            className="trading-panel flex flex-col justify-between group overflow-visible"
            onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = CARD_HOVER_BORDER;
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
            }}
        >
            {/* Top highlight bar */}
            <div
                className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl opacity-50 group-hover:opacity-100 transition-opacity duration-300"
                style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }}
            />

            {/* Background glow */}
            <div
                className="absolute -top-10 -left-10 w-32 h-32 blur-[60px] pointer-events-none opacity-0 group-hover:opacity-20 transition-opacity duration-500"
                style={{ background: accent }}
            />

            <div className="flex flex-col gap-1 relative z-10">
                <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-slate-500 uppercase group-hover:text-slate-400 transition-colors">
                    {label}
                </span>
                <div
                    className="text-3xl sm:text-4xl font-black tabular-nums tracking-tighter"
                    style={{
                        background: `linear-gradient(135deg, white 0%, ${accent} 100%)`,
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        filter: `drop-shadow(0 0 10px ${accent}25)`,
                    }}
                >
                    {value}
                </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/5 relative z-10">
                <div className="text-[11px] font-mono text-slate-500 group-hover:text-slate-400 transition-colors uppercase tracking-tight">
                    {sub}
                </div>
            </div>
        </div>
    );
}

// ── Row 2: four stat cards ───────────────────────────────────────────────────
interface StatCardsRowProps {
    data: LiveMarketData | null;
    isAnalyticsEnabled: boolean;
}

export function StatCardsRow({ data, isAnalyticsEnabled }: StatCardsRowProps) {
    const pcr = data?.analytics?.pcr ?? 1;
    const totalOI = (data?.analytics?.total_call_oi || 0) + (data?.analytics?.total_put_oi || 0);

    return (
        <div
            id="section-analytics"
            className="scroll-mt-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
            <StatCard
                label="VOLATILITY σ"
                value={isAnalyticsEnabled ? (data?.intelligence?.probability?.expected_move || 0).toFixed(2) : 'N/A'}
                sub={isAnalyticsEnabled ? `RANGE: ±${(data?.intelligence?.probability?.upper_1sd || 0).toFixed(1)}` : 'Analysis disabled'}
                accent="#00E5FF"
            />
            <StatCard
                label="MARKET PCR"
                value={data?.analytics?.pcr?.toFixed(2) ?? '—'}
                sub={pcr > 1 ? 'SENTIMENT: BULLISH' : pcr < 1 ? 'SENTIMENT: BEARISH' : 'SENTIMENT: NEUTRAL'}
                accent={pcr > 1.2 ? '#4ade80' : pcr < 0.8 ? '#f87171' : '#94a3b8'}
            />
            <StatCard
                label="TOTAL OI"
                value={totalOI > 1e6 ? `${(totalOI / 1e6).toFixed(1)}M` : totalOI.toLocaleString()}
                sub={`VOL: ${((data?.analytics?.total_volume || 0) / 1e6).toFixed(1)}M UNITS`}
                accent="#a78bfa"
            />
            <StatCard
                label="BREACH RISK"
                value={`${data?.intelligence?.probability?.breach_probability?.toFixed(0) ?? '0'}%`}
                sub={`VWAP: ${data?.analytics?.vwap?.toFixed(1) ?? '—'}`}
                accent="#fb923c"
            />
        </div>
    );
}

