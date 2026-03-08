"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Zap, Brain, Target } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';
import { useWSStore } from '../../core/ws/wsStore';

interface SignalMatrixPanelProps {
    data: LiveMarketData | null;
}

// ── Colour helpers ────────────────────────────────────────────────────────────
const BULL = '#4ade80';
const BEAR = '#f87171';
const NEUT = '#94a3b8';
const WARN = '#fb923c';
const CYAN = '#00E5FF';

function dirColor(d?: string) {
    if (!d) return NEUT;
    const l = d.toLowerCase();
    if (l === 'bullish' || l === 'buy') return BULL;
    if (l === 'bearish' || l === 'sell') return BEAR;
    if (l === 'watch') return WARN;
    return NEUT;
}

function tierBadge(tier: string) {
    switch (tier) {
        case 'HIGH': return { bg: 'rgba(74,222,128,0.12)', border: 'rgba(74,222,128,0.30)', color: BULL };
        case 'MEDIUM': return { bg: 'rgba(0,229,255,0.10)', border: 'rgba(0,229,255,0.28)', color: CYAN };
        case 'LOW': return { bg: 'rgba(251,146,60,0.10)', border: 'rgba(251,146,60,0.28)', color: WARN };
        default: return { bg: 'rgba(148,163,184,0.06)', border: 'rgba(148,163,184,0.15)', color: NEUT };
    }
}

export function SignalMatrixPanel({ data }: SignalMatrixPanelProps) {
    // ── Standard analytics signals ────────────────────────────────────────────
    const pcr = (data as any)?.intelligence?.pcr || 1.0;
    const gammaRegime = (data as any)?.intelligence?.structural_regime || 'unknown';
    const flowDirection = (data as any)?.intelligence?.flow_direction || 'neutral';
    const flowImbalance = (data as any)?.intelligence?.flow_imbalance || 0;
    const breachProbability = (data as any)?.intelligence?.breach_probability || 0;
    const volatilityRegime = (data as any)?.intelligence?.volatility_regime || 'normal';
    const bias = (data as any)?.intelligence?.bias?.label || 'neutral';

    // ── Step 14 / 15 — Advanced signals from wsStore ─────────────────────────
    const signalScore = useWSStore(s => s.signalScore);
    const advancedStrategies = useWSStore(s => s.advancedStrategies);

    const score: number = signalScore?.score ?? 0;
    const scoreTier: string = signalScore?.confidence_tier ?? 'NOISE';
    const scoreBias: string = signalScore?.bias ?? 'neutral';
    const topSignals: any[] = signalScore?.top_signals ?? [];
    const components: any = signalScore?.components ?? {};

    // SMC data
    const smc = advancedStrategies?.smc ?? {};
    const ict = advancedStrategies?.ict ?? {};
    const crt = advancedStrategies?.crt ?? {};
    const msnr = advancedStrategies?.msnr ?? {};

    // ── Legacy signal processing ──────────────────────────────────────────────
    const getPCRSignal = (v: number) => {
        if (v > 1.2) return { label: 'BULLISH', color: BULL, icon: <TrendingUp className="w-3.5 h-3.5" /> };
        if (v < 0.8) return { label: 'BEARISH', color: BEAR, icon: <TrendingDown className="w-3.5 h-3.5" /> };
        return { label: 'NEUTRAL', color: NEUT, icon: <Minus className="w-3.5 h-3.5" /> };
    };
    const getGammaSignal = (r: string) => {
        if (r.toLowerCase().includes('positive')) return { label: 'POSITIVE', color: BULL, icon: <TrendingUp className="w-3.5 h-3.5" /> };
        if (r.toLowerCase().includes('negative')) return { label: 'NEGATIVE', color: BEAR, icon: <TrendingDown className="w-3.5 h-3.5" /> };
        return { label: 'NEUTRAL', color: NEUT, icon: <Minus className="w-3.5 h-3.5" /> };
    };
    const getFlowSignal = (d: string) => {
        if (d.toLowerCase() === 'call') return { label: 'CALL BIAS', color: BULL, icon: <TrendingUp className="w-3.5 h-3.5" /> };
        if (d.toLowerCase() === 'put') return { label: 'PUT BIAS', color: BEAR, icon: <TrendingDown className="w-3.5 h-3.5" /> };
        return { label: 'BALANCED', color: NEUT, icon: <Minus className="w-3.5 h-3.5" /> };
    };
    const getSmartMoneySignal = (imb: number) => {
        if (Math.abs(imb) > 0.3) return imb > 0
            ? { label: 'ABSORPTION', color: BULL, icon: <TrendingUp className="w-3.5 h-3.5" /> }
            : { label: 'DISTRIBUTION', color: BEAR, icon: <TrendingDown className="w-3.5 h-3.5" /> };
        return { label: 'NEUTRAL', color: NEUT, icon: <Minus className="w-3.5 h-3.5" /> };
    };
    const getVolatilitySignal = (r: string) => {
        switch (r.toLowerCase()) {
            case 'extreme': return { label: 'EXTREME', color: BEAR, icon: <AlertTriangle className="w-3.5 h-3.5" /> };
            case 'elevated': return { label: 'ELEVATED', color: WARN, icon: <AlertTriangle className="w-3.5 h-3.5" /> };
            case 'low': return { label: 'LOW', color: '#60a5fa', icon: <Minus className="w-3.5 h-3.5" /> };
            default: return { label: 'NORMAL', color: BULL, icon: <Minus className="w-3.5 h-3.5" /> };
        }
    };
    const getBiasSignal = (b: string) => {
        switch (b?.toLowerCase()) {
            case 'bullish': return { label: 'BULLISH', color: BULL, icon: <TrendingUp className="w-3.5 h-3.5" /> };
            case 'bearish': return { label: 'BEARISH', color: BEAR, icon: <TrendingDown className="w-3.5 h-3.5" /> };
            default: return { label: 'NEUTRAL', color: NEUT, icon: <Minus className="w-3.5 h-3.5" /> };
        }
    };

    const pcrSignal = getPCRSignal(pcr);
    const gammaSignal = getGammaSignal(gammaRegime);
    const flowSignal = getFlowSignal(flowDirection);
    const smartMoneySignal = getSmartMoneySignal(flowImbalance);
    const volatilitySignal = getVolatilitySignal(volatilityRegime);
    const biasSignal = getBiasSignal(bias);

    const legacySignals = [
        { label: 'PCR', value: pcrSignal.label, color: pcrSignal.color, icon: pcrSignal.icon },
        { label: 'GAMMA', value: gammaSignal.label, color: gammaSignal.color, icon: gammaSignal.icon },
        { label: 'FLOW', value: flowSignal.label, color: flowSignal.color, icon: flowSignal.icon },
        { label: 'INTENT', value: smartMoneySignal.label, color: smartMoneySignal.color, icon: smartMoneySignal.icon },
        { label: 'BREACH', value: `${breachProbability.toFixed(0)}%`, color: breachProbability > 50 ? BEAR : BULL, icon: breachProbability > 50 ? <AlertTriangle className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" /> },
        { label: 'VOL', value: volatilitySignal.label, color: volatilitySignal.color, icon: volatilitySignal.icon },
        { label: 'BIAS', value: biasSignal.label, color: biasSignal.color, icon: biasSignal.icon },
    ];

    const bullishCount = legacySignals.filter(s => ['BULLISH', 'POSITIVE', 'CALL BIAS', 'ABSORPTION'].some(k => s.value.includes(k))).length;
    const bearishCount = legacySignals.filter(s => ['BEARISH', 'NEGATIVE', 'PUT BIAS', 'DISTRIBUTION'].some(k => s.value.includes(k))).length;
    const overallSent = bullishCount > bearishCount ? 'BULLISH' : bearishCount > bullishCount ? 'BEARISH' : 'NEUTRAL';
    const sentColor = overallSent === 'BULLISH' ? BULL : overallSent === 'BEARISH' ? BEAR : NEUT;

    const badge = tierBadge(scoreTier);
    const scoreBar = Math.min(100, score);
    const crtPhase = crt?.phase ?? '';
    const msnrTrend = msnr?.trend ?? '';
    const ictKz = ict?.kill_zone?.zone;
    const smcBias = smc?.smc_bias ?? '';

    // True only when backend has sent at least one advanced strategies payload
    const hasSMCData = !!(advancedStrategies && Object.keys(advancedStrategies).length > 0);

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {/* ── Header ─────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between mb-4">
                <SectionLabel>Signal Matrix</SectionLabel>
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-green-500/20 bg-green-500/5">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                    <span className="text-[10px] font-bold font-mono tracking-widest text-green-400">REALTIME</span>
                </div>
            </div>

            {/* ── Step 15: Unified Score Bar ────────────────────────────── */}
            {score > 0 && (
                <div style={{
                    marginBottom: 14,
                    padding: '10px 12px',
                    borderRadius: 10,
                    background: 'rgba(0,229,255,0.04)',
                    border: '1px solid rgba(0,229,255,0.12)',
                }}>
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            <Brain size={12} style={{ color: CYAN }} />
                            <span style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 700, letterSpacing: '0.18em', color: 'rgba(148,163,184,0.60)', textTransform: 'uppercase' }}>
                                Signal Score
                            </span>
                        </div>
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '2px 8px', borderRadius: 6,
                            background: badge.bg, border: `1px solid ${badge.border}`,
                        }}>
                            <span style={{ fontSize: 10, fontFamily: 'monospace', fontWeight: 700, color: badge.color }}>
                                {scoreTier}
                            </span>
                            <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 800, color: badge.color }}>
                                {score.toFixed(0)}
                            </span>
                        </div>
                    </div>
                    {/* Score bar */}
                    <div style={{ height: 4, borderRadius: 4, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                        <div style={{
                            height: '100%',
                            width: `${scoreBar}%`,
                            borderRadius: 4,
                            background: scoreTier === 'HIGH' ? `linear-gradient(90deg, ${BULL}, #22d3ee)` :
                                scoreTier === 'MEDIUM' ? `linear-gradient(90deg, ${CYAN}, #818cf8)` :
                                    `linear-gradient(90deg, ${WARN}, #94a3b8)`,
                            transition: 'width 0.5s ease',
                        }} />
                    </div>
                    <div className="flex items-center justify-between mt-1.5">
                        <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.45)' }}>BIAS</span>
                        <span style={{ fontSize: 10, fontFamily: 'monospace', fontWeight: 700, color: dirColor(scoreBias) }}>
                            {scoreBias.toUpperCase()}
                        </span>
                    </div>
                </div>
            )}

            {/* ── Standard Signal Grid ──────────────────────────────────── */}
            <div className="grid grid-cols-2 gap-2 mb-4">
                {legacySignals.map((signal, index) => (
                    <div
                        key={index}
                        className="rounded-xl p-2.5 flex flex-col gap-1 transition-all hover:bg-white/5 group"
                        style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}
                    >
                        <div className="flex items-center gap-1.5">
                            <span style={{ color: signal.color }}>{signal.icon}</span>
                            <span className="text-[9px] font-bold font-mono tracking-widest uppercase text-slate-500 group-hover:text-slate-400 transition-colors">
                                {signal.label}
                            </span>
                        </div>
                        <span className="text-[11px] font-mono font-bold tracking-tight uppercase" style={{ color: signal.color }}>
                            {signal.value}
                        </span>
                    </div>
                ))}
            </div>

            {/* ── Step 14: SMC / ICT / CRT / MSNR row — always shown ──────── */}
            <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <div style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 700, letterSpacing: '0.18em', color: 'rgba(148,163,184,0.40)', textTransform: 'uppercase' }}>
                        Advanced Strategies
                    </div>
                    {!hasSMCData && (
                        <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.25)', letterSpacing: '0.1em' }}>MARKET CLOSED</span>
                    )}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
                    {([
                        {
                            src: 'SMC',
                            val: hasSMCData ? (smcBias || 'NEUTRAL').toUpperCase() : '—',
                            col: hasSMCData ? dirColor(smcBias || 'neutral') : NEUT,
                        },
                        {
                            src: 'CRT',
                            val: hasSMCData ? (crtPhase || 'UNKNOWN').toUpperCase() : '—',
                            col: hasSMCData ? (crtPhase === 'expansion' ? BULL : crtPhase === 'consolidation' ? WARN : NEUT) : NEUT,
                        },
                        {
                            src: 'MSS',
                            val: hasSMCData ? (msnrTrend || 'UNKNOWN').toUpperCase() : '—',
                            col: hasSMCData ? dirColor(msnrTrend || 'neutral') : NEUT,
                        },
                        {
                            src: 'ICT',
                            val: hasSMCData ? (ictKz ? 'KZ ACTIVE' : 'CLEAR') : '—',
                            col: hasSMCData ? (ictKz ? WARN : NEUT) : NEUT,
                        },
                    ] as { src: string; val: string; col: string }[]).map(({ src, val, col }) => (
                        <div key={src} style={{
                            padding: '6px 8px', borderRadius: 8,
                            background: 'rgba(255,255,255,0.02)',
                            border: '1px solid rgba(255,255,255,0.06)',
                        }}>
                            <div style={{ fontSize: 8, fontFamily: 'monospace', fontWeight: 700, color: 'rgba(148,163,184,0.40)', letterSpacing: '0.15em', marginBottom: 2 }}>{src}</div>
                            <div style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 800, color: col }}>{val}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── Step 15: Top Signals — always shown ─────────────────────── */}
            <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 700, letterSpacing: '0.18em', color: 'rgba(148,163,184,0.40)', textTransform: 'uppercase', marginBottom: 6 }}>
                    Active Signals
                </div>
                {topSignals.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {topSignals.slice(0, 3).map((sig, i) => (
                            <div key={i} style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                padding: '5px 8px', borderRadius: 8,
                                background: `${dirColor(sig.direction)}08`,
                                border: `1px solid ${dirColor(sig.direction)}20`,
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <span style={{ fontSize: 8, fontFamily: 'monospace', fontWeight: 700, color: 'rgba(148,163,184,0.50)', letterSpacing: '0.12em' }}>
                                        {sig.source}
                                    </span>
                                    <span style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 700, color: dirColor(sig.direction) }}>
                                        {sig.signal}
                                    </span>
                                </div>
                                <span style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: 700, color: dirColor(sig.direction) }}>
                                    {sig.confidence ?? 0}%
                                </span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div style={{
                        padding: '8px 10px', borderRadius: 8, textAlign: 'center',
                        background: 'rgba(255,255,255,0.015)',
                        border: '1px solid rgba(255,255,255,0.04)',
                    }}>
                        <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.25)', letterSpacing: '0.12em' }}>
                            NO ACTIVE SIGNALS
                        </span>
                    </div>
                )}
            </div>

            {/* ── Aggregate Sentiment ───────────────────────────────────── */}
            <div className="mt-auto pt-3 border-t border-white/5 flex items-center justify-between">
                <span className="text-[10px] font-bold font-mono tracking-widest uppercase text-slate-500">
                    Aggregate Sentiment
                </span>
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '4px 10px', borderRadius: 8,
                    background: `${sentColor}10`, border: `1px solid ${sentColor}25`,
                }}>
                    {overallSent === 'BULLISH' ? <TrendingUp className="w-3.5 h-3.5" style={{ color: sentColor }} /> :
                        overallSent === 'BEARISH' ? <TrendingDown className="w-3.5 h-3.5" style={{ color: sentColor }} /> :
                            <Minus className="w-3.5 h-3.5" style={{ color: sentColor }} />}
                    <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 700, color: sentColor }}>
                        {overallSent}
                    </span>
                </div>
            </div>
        </div>
    );
}

export default React.memo(SignalMatrixPanel);
