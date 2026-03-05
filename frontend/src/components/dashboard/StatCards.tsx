"use client";
import React from 'react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

// ── Shared helpers ────────────────────────────────────────────────────────────
export function SectionLabel({ children }: { children: React.ReactNode }) {
    return (
        <div
            className="text-[10px] font-bold tracking-[0.20em] uppercase mb-1"
            style={{ color: 'rgba(148,163,184,0.55)', fontFamily: "'JetBrains Mono', monospace" }}
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
            className="flex flex-col justify-between p-4 sm:p-5 rounded-2xl transition-all duration-300"
            style={CARD}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = CARD_HOVER_BORDER)}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)')}
        >
            <div
                className="text-[10px] font-semibold tracking-[0.18em] uppercase mb-2"
                style={{ color: 'rgba(148,163,184,0.55)', fontFamily: "'JetBrains Mono', monospace" }}
            >
                {label}
            </div>
            <div
                className="text-2xl sm:text-3xl font-black tabular-nums leading-none mb-1"
                style={{
                    background: `linear-gradient(135deg, ${accent} 0%, #a78bfa 100%)`,
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    fontFamily: "'Space Grotesk', sans-serif",
                }}
            >
                {value}
            </div>
            {sub && (
                <div className="text-[11px] font-mono" style={{ color: 'rgba(148,163,184,0.5)' }}>
                    {sub}
                </div>
            )}
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
        <div id="section-analytics" className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 scroll-mt-20">
            <StatCard
                label="Expected Move"
                value={isAnalyticsEnabled ? (data?.intelligence?.probability?.expected_move || 0).toFixed(2) : 'N/A'}
                sub={isAnalyticsEnabled ? `±${(data?.intelligence?.probability?.upper_1sd || 0).toFixed(2)} SD` : 'Analysis disabled'}
                accent="#00E5FF"
            />
            <StatCard
                label="Put-Call Ratio"
                value={data?.analytics?.pcr?.toFixed(2) ?? '—'}
                sub={pcr > 1 ? '▲ Bullish Bias' : pcr < 1 ? '▼ Bearish Bias' : '— Neutral'}
                accent={pcr > 1 ? '#4ade80' : pcr < 1 ? '#f87171' : '#94a3b8'}
            />
            <StatCard
                label="Total OI"
                value={totalOI > 1e6 ? `${(totalOI / 1e6).toFixed(1)}M` : totalOI.toLocaleString()}
                sub={`Vol: ${(data?.analytics?.total_volume || 0).toLocaleString()}`}
                accent="#a78bfa"
            />
            <StatCard
                label="Breakout Risk"
                value={`${data?.intelligence?.probability?.breach_probability?.toFixed(0) ?? '0'}%`}
                sub={`VWAP: ${data?.analytics?.vwap?.toFixed(2) ?? '—'}`}
                accent="#fb923c"
            />
        </div>
    );
}
