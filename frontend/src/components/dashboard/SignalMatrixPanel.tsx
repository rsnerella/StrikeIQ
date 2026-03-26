"use client";
import React from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Zap, Brain, Target } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';
import { useWSStore } from '../../core/ws/wsStore';
import { useShallow } from 'zustand/shallow';

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
    // FIX: Move ALL hooks to TOP - no hooks inside map/condition/inline
    const {
        pcr,
        netGex,
        tradePlan,
        earlyWarnings,
        bias,
        keyLevels,
        lastUpdate,
        spotPrice,
        gammaAnalysis,
        calls,
        puts,
        volState,
        technicals,
        regime,
        summary,
        gexFlip,
        callWall,
        putWall,
        biasStrength
    } = useWSStore(useShallow(s => ({
        pcr: s.pcr,
        netGex: s.netGex,
        tradePlan: s.tradePlan,
        earlyWarnings: s.earlyWarnings,
        bias: s.bias,
        keyLevels: s.keyLevels,
        lastUpdate: s.lastUpdate,
        spotPrice: s.spot,
        gammaAnalysis: s.gammaAnalysis,
        calls: s.calls,
        puts: s.puts,
        volState: s.volState,
        technicals: s.technicals,
        regime: s.regime,
        summary: s.summary ?? s.aiAnalysis?.reasoning?.[0],
        gexFlip: s.gexFlip ?? s.keyLevels?.gex_flip,
        callWall: s.callWall ?? s.keyLevels?.call_wall,
        putWall: s.putWall ?? s.keyLevels?.put_wall,
        biasStrength: s.biasStrength
    })))

    const hasData = lastUpdate > 0

    // Extract signal-related data
    const maxPain       = keyLevels?.max_pain ?? 0
    const netGexValue = netGex ?? gammaAnalysis?.net_gex ?? 0
    const gammaDisplay = netGexValue !== 0
      ? (Math.abs(netGexValue) >= 1e9
          ? (netGexValue / 1e9).toFixed(1) + 'B'
          : Math.abs(netGexValue) >= 1e6
            ? (netGexValue / 1e6).toFixed(0) + 'M'
            : netGexValue.toFixed(0))
      : '—'
    
    // FIX A: OI — use total call + put OI from option chain
    const totalCallOI = Object.values(calls).reduce(
      (sum: number, c: any) => sum + (c?.oi || 0), 0
    )
    const totalPutOI = Object.values(puts).reduce(
      (sum: number, p: any) => sum + (p?.oi || 0), 0
    )
    const totalOI = totalCallOI + totalPutOI
    const oiDisplay = totalOI > 0
      ? (totalOI / 1e6).toFixed(1) + 'M'
      : '—'
    
    // OI-to-PE ratio display
    const oiToPeRatio = pcr > 0 ? pcr.toFixed(2) : '—'
    
    // Market bias display
    const signalBias = tradePlan?.signals_used?.bias || bias
    
    // PINNED (max pain proximity)
    const isPinned = maxPain > 0
      ? Math.abs(spotPrice - maxPain) / spotPrice < 0.005
      : false
    const score = biasStrength * 100
    const scoreTier = score > 75 ? 'INSTITUTIONAL' : score > 50 ? 'CONVICTION' : score > 25 ? 'STRUCTURAL' : 'NOISE';
    
    // FIX C: ANALYSIS — build from real data
    const analysisText = summary && summary.length > 10
      ? summary
      : regime !== 'RANGING' || bias !== 'NEUTRAL'
        ? `Market is ${regime} with ${bias} bias (${(biasStrength * 100).toFixed(0)}% strength). Gamma profile indicates ${netGexValue < 0 ? 'SHORT_GAMMA' : 'LONG_GAMMA'}.` 
        : 'Analyzing market structure...'
    
    // Prepare anchor data array for rendering - using top-level variables
    const anchorData = [
        { label: 'GEX FLIP', value: gexFlip, color: WARN },
        { label: 'CALL WALL', value: callWall, color: BEAR },
        { label: 'PUT WALL', value: putWall, color: BULL }
    ]

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 border border-white/10 opacity-70">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Signal Matrix</SectionLabel>
                    <SkeletonPulse className="w-20 h-5 bg-white/10" />
                </div>
                <div className="space-y-4">
                    <SkeletonPulse className="w-full h-12 bg-white/5" />
                    <div className="grid grid-cols-2 gap-2">
                        {[1, 2, 3, 4, 5, 6].map(i => <SkeletonPulse key={i} className="h-16 bg-white/5" />)}
                    </div>
                </div>
            </div>
        );
    }

    const signals = [
        { label: 'GAMMA', val: gammaDisplay, color: netGexValue < 0 ? BEAR : BULL },
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
                    {(anchorData || []).map((k, i) => (
                        <div key={i} className="flex justify-between items-center px-2 py-1.5 rounded bg-white/5 border border-white/5">
                            <span className="text-[9px] font-mono text-slate-400">{k.label}</span>
                            <span className="text-[10px] font-black font-mono tabular-nums" style={{ color: k.value > 0 ? k.color : '#374151' }}>
                                {k.value > 0 ? `₹${k.value.toLocaleString()}` : '—'}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default React.memo(SignalMatrixPanel);
