"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, Layers } from 'lucide-react';
import { CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import { useWSStore } from '../../core/ws/wsStore';
import { useShallow } from 'zustand/shallow';

// ── Colours ────────────────────────────────────────────────────────────────────
const BULL = '#4ade80';
const BEAR = '#f87171';
const NEUT = '#94a3b8';
const WARN = '#fb923c';
const CYAN = '#00E5FF';
const GOLD = '#fbbf24';

function signalColor(sig?: string) {
    if (!sig) return NEUT;
    if (sig === 'BUY' || sig === 'BULLISH') return BULL;
    if (sig === 'SELL' || sig === 'BEARISH') return BEAR;
    return NEUT;
}
function trendColor(t?: string) {
    if (!t) return NEUT;
    if (t === 'BULLISH') return BULL;
    if (t === 'BEARISH') return BEAR;
    return NEUT;
}

// ── Zone badge ────────────────────────────────────────────────────────────────
const ZoneBadge = React.memo(({ label, zone, color }: { label: string; zone: number[]; color: string }) => {
    if (!zone || zone.length < 2) return null;
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 8px', borderRadius: 7,
            background: `${color}10`, border: `1px solid ${color}25`,
        }}>
            <div style={{ width: 6, height: 6, borderRadius: 2, background: color }} />
            <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.60)', fontWeight: 600 }}>{label}</span>
            <span style={{ fontSize: 9, fontFamily: 'monospace', color, fontWeight: 700 }}>
                {zone[0].toFixed(0)}–{zone[1].toFixed(0)}
            </span>
        </div>
    );
});

ZoneBadge.displayName = 'ZoneBadge';

// ── Main component ─────────────────────────────────────────────────────────────
export const ChartIntelligencePanel = React.memo(function ChartIntelligencePanel() {
    // Law 7: Granular, Shallow Selection
    const analysis = useWSStore(useShallow(s => s.chartAnalysis));
    const spotPrice = useWSStore(s => s.spot);
    const hasData = spotPrice > 0 && !!analysis;

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Chart Intelligence</SectionLabel>
                    <Activity size={12} className="text-slate-500 animate-pulse" />
                </div>
                <div style={{
                    flex: 1, display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 8,
                }}>
                    <div className="w-full space-y-4">
                        <div className="h-20 bg-white/5 rounded-xl animate-pulse" />
                        <div className="grid grid-cols-2 gap-4">
                            <div className="h-16 bg-white/5 rounded-xl animate-pulse" />
                            <div className="h-16 bg-white/5 rounded-xl animate-pulse" />
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const signal = analysis?.bias ?? 'WAIT';
    const confidence = analysis?.confidence ?? 0;
    const wave = analysis?.wave ?? '?';
    const wavePattern = analysis?.wave_pattern ?? '—';
    const neoPattern = analysis?.neo_wave_pattern;
    const trend = analysis?.regime ?? 'RANGE';
    const spot = spotPrice || analysis?.price || 0;
    const bos = analysis?.bos_detected;
    const mss = analysis?.mss_detected;
    const candlePattern = analysis?.candle_pattern;
    const supplyZone = analysis?.supply_zone ?? [];
    const demandZone = analysis?.demand_zone ?? [];
    const targetZone = analysis?.target_zone ?? [];
    const stopZone = analysis?.stop_zone ?? [];
    const computeMs = analysis?.computation_ms ?? 0;
    const bullScore = analysis?.bull_score ?? 0;
    const bearScore = analysis?.bear_score ?? 0;

    const sigColor = signalColor(signal);
    const trendCol = trendColor(trend);

    // Bull/Bear gauge bar
    const totalScore = bullScore + bearScore;
    const bullPct = totalScore > 0 ? Math.round(bullScore / totalScore * 100) : 50;
    const bearPct = 100 - bullPct;

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <SectionLabel>Chart Intelligence</SectionLabel>
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '3px 9px', borderRadius: 20,
                    background: `${sigColor}12`, border: `1px solid ${sigColor}30`,
                }}>
                    {signal === 'BUY' || signal === 'BULLISH' ? <TrendingUp size={11} style={{ color: sigColor }} /> :
                        signal === 'SELL' || signal === 'BEARISH' ? <TrendingDown size={11} style={{ color: sigColor }} /> :
                            <Minus size={11} style={{ color: sigColor }} />}
                    <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 800, color: sigColor }}>
                        {signal}
                    </span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.55)' }}>
                        {(confidence * 100).toFixed(0)}%
                    </span>
                </div>
            </div>

            {/* Bull/Bear gauge */}
            <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: BULL, fontWeight: 700 }}>BULL {bullPct}%</span>
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: BEAR, fontWeight: 700 }}>BEAR {bearPct}%</span>
                </div>
                <div style={{ display: 'flex', height: 6, borderRadius: 6, overflow: 'hidden', gap: 1 }}>
                    <div style={{
                        width: `${bullPct}%`, height: '100%',
                        background: `linear-gradient(90deg, ${BULL}80, ${BULL})`,
                        borderRadius: '6px 0 0 6px', transition: 'width 0.5s ease',
                    }} />
                    <div style={{
                        width: `${bearPct}%`, height: '100%',
                        background: `linear-gradient(90deg, ${BEAR}, ${BEAR}80)`,
                        borderRadius: '0 6px 6px 0', transition: 'width 0.5s ease',
                    }} />
                </div>
            </div>

            {/* Wave + Structure row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 10 }}>
                {/* Elliott Wave */}
                <div style={{
                    padding: '8px 10px', borderRadius: 10,
                    background: 'rgba(251,191,36,0.05)',
                    border: '1px solid rgba(251,191,36,0.15)',
                }}>
                    <div style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.40)', letterSpacing: '0.15em', marginBottom: 4 }}>ELLIOTT WAVE</div>
                    <div className="flex items-baseline gap-1">
                        <span style={{ fontSize: 18, fontFamily: 'monospace', fontWeight: 900, color: GOLD, lineHeight: 1 }}>
                            {wave === '?' ? '—' : wave}
                        </span>
                        <span style={{ fontSize: 8, fontFamily: 'monospace', color: GOLD, opacity: 0.7, textTransform: 'uppercase' }}>
                            {wavePattern.replace('IMPULSE_', '').replace(/_/g, ' ')}
                        </span>
                    </div>
                </div>

                {/* Market Structure */}
                <div style={{
                    padding: '8px 10px', borderRadius: 10,
                    background: `${trendCol}05`,
                    border: `1px solid ${trendCol}18`,
                }}>
                    <div style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.40)', letterSpacing: '0.15em', marginBottom: 4 }}>STRUCTURE</div>
                    <div style={{ fontSize: 13, fontFamily: 'monospace', fontWeight: 800, color: trendCol, marginBottom: 4 }}>
                        {trend}
                    </div>
                </div>
            </div>

            {/* Zones */}
            <div style={{ marginBottom: 10 }}>
                <SectionLabel>Price Zones</SectionLabel>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                    <ZoneBadge label="SUPPLY" zone={supplyZone} color={BEAR} />
                    <ZoneBadge label="DEMAND" zone={demandZone} color={BULL} />
                    {targetZone.length > 0 && <ZoneBadge label="TARGET" zone={targetZone} color={CYAN} />}
                </div>
            </div>

            {/* Confidence bar */}
            <div style={{ marginBottom: 10 }}>
                <div className="flex items-center justify-between mb-1.5">
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.40)', letterSpacing: '0.12em' }}>ENGINE CONVICTION</span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 800, color: sigColor }}>
                        {(confidence * 100).toFixed(1)}%
                    </span>
                </div>
                <div style={{ height: 4, borderRadius: 4, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
                    <div style={{
                        height: '100%',
                        width: `${(confidence * 100).toFixed(1)}%`,
                        background: `linear-gradient(90deg, ${sigColor}80, ${sigColor})`,
                        borderRadius: 4,
                        transition: 'width 0.5s ease',
                    }} />
                </div>
            </div>

            {/* Spot price */}
            {spot > 0 && (
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '6px 10px', borderRadius: 8,
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.05)',
                }}>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.45)' }}>SPOT</span>
                    <span style={{ fontSize: 13, fontFamily: 'monospace', fontWeight: 800, color: '#e2e8f0' }}>
                        {spot.toFixed(2)}
                    </span>
                </div>
            )}

            {/* Footer meta */}
            <div className="mt-auto pt-3 border-t border-white/5 flex items-center justify-between">
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Layers size={10} style={{ color: 'rgba(148,163,184,0.30)' }} />
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.30)', letterSpacing: '0.10em' }}>
                        WAVE + STRUCTURE + ZONES
                    </span>
                </div>
                {computeMs > 0 && (
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.20)' }}>
                        {computeMs}ms
                    </span>
                )}
            </div>
        </div>
    );
});

export default ChartIntelligencePanel;
