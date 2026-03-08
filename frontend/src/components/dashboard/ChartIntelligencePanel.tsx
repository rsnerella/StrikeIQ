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
            <div style={{ color: NEUT }}>O: {d?.open?.toFixed(2)}  C: {d?.close?.toFixed(2)}</div>
            <div style={{ color: NEUT }}>H: {d?.high?.toFixed(2)}  L: {d?.low?.toFixed(2)}</div>
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

// ── Main component ─────────────────────────────────────────────────────────────
export function ChartIntelligencePanel() {
    const chartAnalysis = useWSStore(s => s.chartAnalysis);
    const optionChain = useWSStore(s => s.optionChainSnapshot);

    // Build mock candle bars from option chain spot history for visual
    // (real candles come from candle_builder; we use spot as proxy when no history yet)
    const spot = optionChain?.spot ?? chartAnalysis?.price ?? 0;

    const hasData = !!(chartAnalysis && chartAnalysis.signal);
    const signal = chartAnalysis?.signal ?? 'WAIT';
    const confidence = chartAnalysis?.confidence ?? 0;
    const wave = chartAnalysis?.wave ?? '?';
    const wavePattern = chartAnalysis?.wave_pattern ?? '';
    const neoPattern = chartAnalysis?.neo_pattern ?? '';
    const trend = chartAnalysis?.trend ?? 'UNKNOWN';
    const bos = chartAnalysis?.bos ?? false;
    const mss = chartAnalysis?.mss ?? false;
    const candlePattern = chartAnalysis?.candle_pattern;
    const supplyZone = chartAnalysis?.supply_zone ?? [];
    const demandZone = chartAnalysis?.demand_zone ?? [];
    const targetZone = chartAnalysis?.target_zone ?? [];
    const stopZone = chartAnalysis?.stop_zone ?? [];
    const computeMs = chartAnalysis?.computation_ms ?? 0;
    const bullScore = chartAnalysis?.bull_score ?? 0;
    const bearScore = chartAnalysis?.bear_score ?? 0;

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
                    {signal === 'BUY' ? <TrendingUp size={11} style={{ color: sigColor }} /> :
                        signal === 'SELL' ? <TrendingDown size={11} style={{ color: sigColor }} /> :
                            <Minus size={11} style={{ color: sigColor }} />}
                    <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 800, color: sigColor }}>
                        {signal}
                    </span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.55)' }}>
                        {(confidence * 100).toFixed(0)}%
                    </span>
                </div>
            </div>

            {/* No data state */}
            {!hasData && (
                <div style={{
                    flex: 1, display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 8,
                }}>
                    <Activity size={22} style={{ color: 'rgba(148,163,184,0.20)' }} />
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(148,163,184,0.25)', letterSpacing: '0.12em' }}>
                        AWAITING MARKET DATA
                    </span>
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.15)', letterSpacing: '0.08em' }}>
                        Chart signals generated each analytics cycle
                    </span>
                </div>
            )}

            {hasData && (
                <>
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
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
                                <span style={{ fontSize: 22, fontFamily: 'monospace', fontWeight: 900, color: GOLD, lineHeight: 1 }}>
                                    {wave === '?' ? '—' : wave}
                                </span>
                                <span style={{ fontSize: 8, fontFamily: 'monospace', color: GOLD, opacity: 0.7 }}>
                                    {wavePattern.replace('IMPULSE_', '').replace('_', ' ')}
                                </span>
                            </div>
                            {neoPattern && neoPattern !== 'INSUFFICIENT_DATA' && (
                                <div style={{ fontSize: 8, fontFamily: 'monospace', color: WARN, marginTop: 3, opacity: 0.8 }}>
                                    ◆ {neoPattern.replace(/_/g, ' ')}
                                </div>
                            )}
                        </div>

                        {/* Market Structure */}
                        <div style={{
                            padding: '8px 10px', borderRadius: 10,
                            background: `${trendCol}05`,
                            border: `1px solid ${trendCol}18`,
                        }}>
                            <div style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.40)', letterSpacing: '0.15em', marginBottom: 4 }}>STRUCTURE</div>
                            <div style={{ fontSize: 12, fontFamily: 'monospace', fontWeight: 800, color: trendCol, marginBottom: 4 }}>
                                {trend}
                            </div>
                            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                                {bos && (
                                    <span style={{ fontSize: 7, fontFamily: 'monospace', fontWeight: 700, color: CYAN, background: `${CYAN}15`, padding: '1px 5px', borderRadius: 4 }}>BOS</span>
                                )}
                                {mss && (
                                    <span style={{ fontSize: 7, fontFamily: 'monospace', fontWeight: 700, color: WARN, background: `${WARN}15`, padding: '1px 5px', borderRadius: 4 }}>MSS</span>
                                )}
                                {candlePattern && (
                                    <span style={{ fontSize: 7, fontFamily: 'monospace', fontWeight: 700, color: NEUT, background: 'rgba(148,163,184,0.08)', padding: '1px 5px', borderRadius: 4 }}>
                                        {candlePattern.split(' ')[0]}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Zones */}
                    <div style={{ marginBottom: 10 }}>
                        <div style={{ fontSize: 8, fontFamily: 'monospace', fontWeight: 700, letterSpacing: '0.15em', color: 'rgba(148,163,184,0.35)', textTransform: 'uppercase', marginBottom: 5 }}>
                            Price Zones
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <ZoneBadge label="SUPPLY" zone={supplyZone} color={BEAR} />
                            <ZoneBadge label="DEMAND" zone={demandZone} color={BULL} />
                            {signal !== 'WAIT' && <ZoneBadge label="TARGET" zone={targetZone} color={CYAN} />}
                            {signal !== 'WAIT' && <ZoneBadge label="STOP" zone={stopZone} color={WARN} />}
                        </div>
                    </div>

                    {/* Confidence bar */}
                    <div style={{ marginBottom: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                            <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.40)', letterSpacing: '0.12em' }}>SIGNAL CONFIDENCE</span>
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
                </>
            )}

            {/* Footer meta */}
            <div className="mt-auto pt-3 border-t border-white/5 flex items-center justify-between">
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Layers size={10} style={{ color: 'rgba(148,163,184,0.30)' }} />
                    <span style={{ fontSize: 8, fontFamily: 'monospace', color: 'rgba(148,163,184,0.30)', letterSpacing: '0.10em' }}>
                        WAVE + STRUCTURE + ZONES + PATTERNS
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
}

export default React.memo(ChartIntelligencePanel);
