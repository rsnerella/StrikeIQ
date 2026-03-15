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

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function SignalMatrixPanel() {
    // Law 7: Granular Store Subscriptions with null-safe pattern
    const pcr           = useWSStore(s => s.pcr           ?? 0)
    const netGex        = useWSStore(s => s.netGex        ?? 0)
    const tradePlan     = useWSStore(s => s.tradePlan)
    const earlyWarnings = useWSStore(s => s.earlyWarnings ?? [])
    const bias          = useWSStore(s => s.bias          ?? 'NEUTRAL')
    const keyLevels     = useWSStore(s => s.keyLevels     ?? {})
    const lastUpdate    = useWSStore(s => s.lastUpdate)
    const hasData       = lastUpdate > 0
    
    // Extract signal-related data
    const maxPain       = keyLevels?.max_pain ?? 0
    const spotPrice     = useWSStore(s => s.spot) ?? 0
    
    // OI-to-PE ratio display
    const oiToPeRatio = pcr > 0 ? pcr.toFixed(2) : '—'
    
    // Market bias display
    const signalBias = tradePlan?.signals_used?.bias || bias
    
    // PINNED (max pain proximity)
    const isPinned = maxPain > 0
      ? Math.abs(spotPrice - maxPain) / spotPrice < 0.005
      : false
    const biasStrength = useWSStore(s => s.biasStrength ?? 0)
    const score = biasStrength * 100
    const scoreTier = score > 75 ? 'INSTITUTIONAL' : score > 50 ? 'CONVICTION' : score > 25 ? 'STRUCTURAL' : 'NOISE';
    const gammaAnalysis = useWSStore(s => s.gammaAnalysis ?? {})
    const volState = useWSStore(s => s.volState ?? {})
    const technicals = useWSStore(s => s.technicals ?? {})

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 border border-white/5 opacity-40">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Signal Matrix</SectionLabel>
                    <SkeletonPulse className="w-20 h-5" />
                </div>
                <div className="space-y-4">
                    <SkeletonPulse className="w-full h-12" />
                    <div className="grid grid-cols-2 gap-2">
                        {[1, 2, 3, 4, 5, 6].map(i => <SkeletonPulse key={i} className="h-16" />)}
                    </div>
                </div>
            </div>
        );
    }

    const signals = [
        { label: 'GAMMA', val: (gammaAnalysis?.regime || 'NEUTRAL').split(' ')[0], color: (gammaAnalysis?.regime || '').includes('SHORT') ? BEAR : BULL },
        { label: 'VOL', val: volState?.state || 'NORMAL', color: volState?.state === 'EXTREME' ? BEAR : CYAN },
        { label: 'PCR', val: pcr > 0 ? pcr.toFixed(2) : '—', color: pcr > 1.2 ? BULL : pcr < 0.8 ? BEAR : NEUT },
        { label: 'RSI', val: technicals?.rsi?.toFixed(1) || '—', color: (technicals?.rsi || 0) > 70 ? BEAR : (technicals?.rsi || 0) < 30 ? BULL : CYAN },
        { label: 'GAP', val: 'CLOSED', color: NEUT },
        { label: 'BIAS', val: signalBias, color: signalBias === 'BULLISH' ? BULL : signalBias === 'BEARISH' ? BEAR : NEUT },
    ];

    const badge = tierBadge(scoreTier);

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <SectionLabel>Institutional Signals</SectionLabel>
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-blue-500/20 bg-blue-500/5">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                    <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400 uppercase">L2 Flow</span>
                </div>
            </div>

            {/* Signal Score */}
            <div className="mb-6 p-4 rounded-xl bg-blue-500/[0.03] border border-blue-500/10">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Brain size={12} className="text-blue-400" />
                        <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Confidence Score</span>
                    </div>
                    <div className="px-3 py-1 rounded-md border border-white/10 bg-white/5 text-[11px] font-black font-mono" style={{ color: badge.color }}>
                        {score.toFixed(1)}
                    </div>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                        className="h-full transition-all duration-1000" 
                        style={{ 
                            width: `${score}%`, 
                            background: `linear-gradient(90deg, ${dirColor(bias)}, ${CYAN})` 
                        }} 
                    />
                </div>
                <div className="flex justify-between mt-2">
                    <span className="text-[8px] font-mono text-slate-500">{scoreTier}</span>
                    <span className="text-[9px] font-bold font-mono uppercase" style={{ color: dirColor(bias) }}>{bias}</span>
                </div>
            </div>

            {/* Signal Grid */}
            <div className="grid grid-cols-2 gap-2 mb-6">
                {signals.map((s, i) => (
                    <div key={i} className="p-3 rounded-lg bg-white/[0.01] border border-white/5 flex flex-col gap-1">
                        <span className="text-[8px] font-bold font-mono text-slate-600 uppercase tracking-wider">{s.label}</span>
                        <span className="text-[11px] font-black font-mono uppercase" style={{ color: s.color }}>{s.val}</span>
                    </div>
                ))}
            </div>

            {/* Liquidity Matrix */}
            <div className="mt-auto space-y-2 pt-4 border-t border-white/5">
                <div className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-[0.2em] mb-3">Order Flow Anchors</div>
                <div className="space-y-1.5">
                    {[
                        { label: 'GEX FLIP', value: gammaAnalysis?.flip_level, color: WARN },
                        { label: 'CALL WALL', value: keyLevels?.call_wall, color: BEAR },
                        { label: 'PUT WALL', value: keyLevels?.put_wall, color: BULL }
                    ].map((k, i) => (
                        <div key={i} className="flex justify-between items-center px-2 py-1.5 rounded bg-white/5 border border-white/5">
                            <span className="text-[9px] font-mono text-slate-400">{k.label}</span>
                            <span className="text-[10px] font-black font-mono tabular-nums" style={{ color: k.color }}>
                                {k.value ? `₹${k.value.toLocaleString()}` : '—'}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default React.memo(SignalMatrixPanel);
