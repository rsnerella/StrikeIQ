"use client";
import React from 'react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { useWSStore } from '../../core/ws/wsStore';
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

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

// ── Row 2: four stat cards ───────────────────────────────────────────────────
export const StatCardsRow = React.memo(function StatCardsRow() {
    // Law 7: Granular Subscriptions - Use direct selectors
    const regime       = useWSStore(s => s.regime        ?? 'RANGING')
    const bias         = useWSStore(s => s.bias          ?? 'NEUTRAL')
    const biasStrength = useWSStore(s => s.biasStrength  ?? 0)
    const pcr          = useWSStore(s => s.pcr           ?? 0)
    const vol          = useWSStore(s => s.volState)
    const gamma        = useWSStore(s => s.gammaAnalysis)
    const lastUpdate   = useWSStore(s => s.lastUpdate)
    const hasData      = useWSStore(s => s.spot > 0)

    // Loading State
    if (!hasData) {
        return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="trading-panel h-32 flex flex-col p-4 opacity-40">
                         <SkeletonPulse className="w-20 h-3 mb-4" />
                         <SkeletonPulse className="w-full h-8" />
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div
            id="section-analytics"
            className="scroll-mt-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
        >
            <StatCard
                label="VOLATILITY STATE"
                value={vol?.state || 'NORMAL'}
                sub={`IV ATM: ${vol?.iv_atm ? `${vol.iv_atm.toFixed(1)}%` : '—'}`}
                accent="#00E5FF"
            />
            <StatCard
                label="GAMMA REGIME"
                value={(gamma?.regime || 'NEUTRAL').split(' ')[0]}
                sub={`FLIP: ${gamma?.flip_level?.toLocaleString() || '—'}`}
                accent={(gamma?.regime || 'NEUTRAL').includes('SHORT') ? '#f87171' : '#4ade80'}
            />
            <StatCard
                label="MARKET PC RATIO"
                value={pcr > 0 ? pcr.toFixed(2) : '—'}
                sub={pcr > 1.2 ? 'SENTIMENT: BULLISH' : pcr < 0.8 ? 'SENTIMENT: BEARISH' : 'SENTIMENT: NEUTRAL'}
                accent={pcr > 1.2 ? '#4ade80' : pcr < 0.8 ? '#f87171' : '#94a3b8'}
            />
            <StatCard
                label="BIAS STRENGTH"
                value={`${(biasStrength * 100).toFixed(0)}%`}
                sub={bias || 'NEUTRAL'}
                accent="#a78bfa"
            />
        </div>
    );
});

