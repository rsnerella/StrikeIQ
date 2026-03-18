"use client";
import React, { useMemo } from 'react';
import {
    ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
    ResponsiveContainer, ReferenceLine, Rectangle
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, Activity, Layers, Target, Shield, Zap } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import { useWSStore } from '../../core/ws/wsStore';
import { StrikeIQPriceChart } from '../charts/StrikeIQPriceChart';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

// ── Colours ────────────────────────────────────────────────────────────────────
const BULL = '#4ade80';
const BEAR = '#f87171';
const NEUT = '#94a3b8';
const WARN = '#fb923c';
const CYAN = '#00E5FF';
const GOLD = '#fbbf24';

function signalColor(sig?: string) {
    if (!sig) return NEUT;
    if (sig === 'BUY') return BULL;
    if (sig === 'SELL') return BEAR;
    return NEUT;
}
function trendColor(t?: string) {
    if (!t) return NEUT;
    if (t === 'BULLISH') return BULL;
    if (t === 'BEARISH') return BEAR;
    return NEUT;
}

// ── Mini OHLC bar using Recharts custom shape ─────────────────────────────────
function OHLCBar(props: any) {
    const { x, y, width, height, open, close } = props;
    const isUp = close >= open;
    const fill = isUp ? BULL : BEAR;
    const barW = Math.max(2, width * 0.6);
    const xMid = x + width / 2;
    return (
        <g>
            {/* Body */}
            <rect
                x={xMid - barW / 2}
                y={Math.min(y, y + height)}
                width={barW}
                height={Math.abs(height) || 1}
                fill={fill}
                opacity={0.85}
            />
            {/* Wick */}
            <line x1={xMid} y1={y - 3} x2={xMid} y2={y + height + 3} stroke={fill} strokeWidth={1} opacity={0.5} />
        </g>
    );
}

// ── Tooltip ────────────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload }: any) {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
        <div style={{
            background: 'rgba(15,20,30,0.97)',
            border: '1px solid rgba(0,229,255,0.2)',
            borderRadius: 8, padding: '8px 12px',
            fontSize: 10, fontFamily: 'monospace',
        }}>
            <div style={{ color: CYAN, fontWeight: 700, marginBottom: 4 }}>{d?.label}</div>
            <div style={{ color: NEUT }}>
                O: {typeof d?.open === 'number' && d.open > 0 ? d.open.toFixed(2) : '—'}  
                C: {typeof d?.close === 'number' && d.close > 0 ? d.close.toFixed(2) : '—'}
              </div>
            <div style={{ color: NEUT }}>
                H: {typeof d?.high === 'number' && d.high > 0 ? d.high.toFixed(2) : '—'}  
                L: {typeof d?.low === 'number' && d.low > 0 ? d.low.toFixed(2) : '—'}
              </div>
        </div>
    );
}

// ── Zone badge ────────────────────────────────────────────────────────────────
function ZoneBadge({ label, zone, color }: { label: string; zone: number[]; color: string }) {
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
}

// ── Skeleton Pulse ─────────────────────────────────────────────────────────────
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

// ── Main component ─────────────────────────────────────────────────────────────
export function ChartIntelligencePanel() {
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    
    // Direct selectors with fallbacks
    const signal = useWSStore(s => s.bias ?? 'NEUTRAL');
    const confidence = useWSStore(s => s.biasStrength ?? 0);
    const gamma = useWSStore(s => s.gammaAnalysis);
    const vol = useWSStore(s => s.volState);
    const tech = useWSStore(s => s.technicals);
    const summary = useWSStore(s => s.summary ?? '');
    const keyLevels = useWSStore(s => s.keyLevels);
    const spot = useWSStore(s => s.spotPrice ?? 0);
    const regime = useWSStore(s => s.regime ?? 'RANGING');
    const pcr = useWSStore(s => s.pcr ?? 0);
    
    const sigColor = signalColor(signal === 'BULLISH' ? 'BUY' : signal === 'BEARISH' ? 'SELL' : 'WAIT');

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col p-6 border border-white/5 hover:border-blue-500/30 transition-all duration-500 min-h-[500px]">
                 <div className="flex items-center justify-between mb-8">
                    <SectionLabel>Institutional Intelligence</SectionLabel>
                    <SkeletonPulse className="w-20 h-6 rounded-full" />
                </div>
                <div className="flex-grow flex flex-col gap-6 justify-center">
                    <div className="space-y-3">
                        <SkeletonPulse className="w-full h-12" />
                        <SkeletonPulse className="w-3/4 h-12" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <SkeletonPulse className="h-24" />
                        <SkeletonPulse className="h-24" />
                    </div>
                </div>
                <div className="mt-auto pt-4 border-t border-white/5 flex justify-between items-center opacity-40">
                    <span className="text-[10px] font-mono tracking-widest uppercase">Institutional Scan Active</span>
                    <Activity size={12} className="animate-spin text-blue-500" />
                </div>
            </div>
        );
    }

    return (
        <div
            className="trading-panel h-full flex flex-col"
            onMouseEnter={e => { e.currentTarget.style.borderColor = CARD_HOVER_BORDER; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <SectionLabel>Institutional Intelligence</SectionLabel>
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '3px 9px', borderRadius: 20,
                    background: `${sigColor}12`, border: `1px solid ${sigColor}30`,
                }}>
                    {signal === 'BULLISH' ? <TrendingUp size={11} style={{ color: sigColor }} /> :
                        signal === 'BEARISH' ? <TrendingDown size={11} style={{ color: sigColor }} /> :
                            <Minus size={11} style={{ color: sigColor }} />}
                    <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 800, color: sigColor }}>
                        {signal}
                    </span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.55)' }}>
                        {(confidence * 100).toFixed(0)}%
                    </span>
                </div>
            </div>

            {/* AI Summary */}
            <div className="mb-6 p-4 rounded-xl bg-blue-500/[0.03] border border-blue-500/10">
                <div className="text-[9px] font-bold font-mono text-blue-400 uppercase mb-2">Market Sentiment Logic</div>
                <div className="text-[11px] font-medium font-mono text-slate-300 leading-relaxed italic">
                    "{summary || (hasData ? `${regime} | PCR: ${pcr?.toFixed(2)}` : '—')}"
                </div>
            </div>

            {/* Analysis Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <div className="text-[9px] font-bold font-mono text-slate-500 uppercase mb-2">Gamma Regime</div>
                    <div className={`text-[15px] font-bold font-mono ${gamma?.regime?.includes('SHORT') ? 'text-red-400' : 'text-green-400'}`}>
                        {gamma?.regime || 'NEUTRAL'}
                    </div>
                    <div className="text-[8px] font-mono text-slate-400 mt-1 uppercase opacity-60">
                         Bias: {gamma?.bias || 'Balanced'}
                    </div>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <div className="text-[9px] font-bold font-mono text-slate-500 uppercase mb-2">Volatility</div>
                    <div className="text-[15px] font-bold font-mono text-cyan-400 uppercase">
                        {vol?.state || 'NORMAL'}
                    </div>
                    <div className="text-[8px] font-mono text-slate-400 mt-1 uppercase opacity-60">
                        IV ATM: {vol?.iv_atm ? vol.iv_atm.toFixed(1) : '—'}%
                    </div>
                </div>
            </div>

            {/* Technical Matrix */}
            <div className="space-y-3 mb-6">
                <div className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-widest">Execution Matrix</div>
                <div className="grid grid-cols-3 gap-2">
                    {[
                        { label: 'RSI (14)', val: tech?.rsi?.toFixed(1) || '—', color: tech?.rsi > 70 ? BEAR : tech?.rsi < 30 ? BULL : CYAN },
                        { label: 'Momentum', val: tech?.momentum_15m?.toFixed(2) || '—', color: tech?.momentum_15m > 0 ? BULL : BEAR },
                        { label: 'Structure', val: regime || '—', color: GOLD }
                    ].map((m, i) => (
                        <div key={i} className="bg-white/[0.01] border border-white/5 p-2 rounded-lg text-center">
                            <div className="text-[8px] text-slate-500 font-mono mb-1">{m.label}</div>
                            <div className="text-[10px] font-bold font-mono truncate" style={{ color: m.color }}>{m.val}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Key Levels Section */}
            <div className="space-y-2 mb-6 flex-grow">
                <div className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-widest">Liquidations & Walls</div>
                <div className="space-y-1">
                    {[
                        { label: 'Call Wall', price: keyLevels?.call_wall, color: BEAR },,
                        { label: 'Put Wall', price: keyLevels?.put_wall, color: BULL },,
                        { label: 'Flip Level', price: keyLevels?.gex_flip, color: WARN }
                    ].map((l, i) => (
                        l.price && (
                            <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.01] border border-white/5">
                                <span className="text-[9px] font-mono text-slate-400 uppercase">{l.label}</span>
                                <span className="text-[11px] font-bold font-mono tabular-nums" style={{ color: l.color }}>₹{l.price.toLocaleString()}</span>
                            </div>
                        )
                    ))}
                </div>
            </div>

            {/* Footer meta */}
            <div className="mt-auto pt-3 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap size={10} className="text-yellow-500 animate-pulse" />
                    <span className="text-[8px] font-mono text-slate-500 tracking-[0.2em] uppercase">
                        REAL-TIME INSTITUTIONAL FLOW
                    </span>
                </div>
                <span className="text-[11px] font-bold font-mono text-slate-100 tabular-nums">
                    {spot > 0 ? `₹${spot.toFixed(2)}` : '—'}
                </span>
            </div>
        </div>
    );
}

export default React.memo(ChartIntelligencePanel);
