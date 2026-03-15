import React, { memo } from 'react';
import {
  Brain,
  TrendingUp,
  Target,
  Activity,
  Zap,
  Shield,
  Eye,
  Info
} from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';
import { safeMapBiasData } from '../utils/biasMapping';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

const AICommandCenter: React.FC = () => {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    
    // Direct selectors with fallbacks
    const regime = useWSStore(s => s.regime ?? 'EQUILIBRIUM');
    const bias = useWSStore(s => s.bias ?? 'NEUTRAL');
    const biasStrength = useWSStore(s => s.biasStrength ?? 0);
    const confidence = biasStrength;
    const riskRegime = useWSStore(s => s.summary ?? 'STABLE'); // Use summary as fallback for risk_regime
    const aiReady = useWSStore(s => s.aiReady);
    const tradePlan = useWSStore(s => s.tradePlan);
    const pcr = useWSStore(s => s.pcr ?? 0);
    
    const biasData = {
        label: bias,
        strength: biasStrength,
        direction: regime
    };

    const getStatusColor = (val: string) => {
        const v = val?.toUpperCase();
        if (v === 'BULLISH' || v === 'UPTREND' || v === 'STRENGTH') return { color: '#4ade80', glow: 'rgba(74,222,128,0.2)' };
        if (v === 'BEARISH' || v === 'DOWNTREND' || v === 'WEAKNESS') return { color: '#f87171', glow: 'rgba(239,68,68,0.2)' };
        return { color: '#60a5fa', glow: 'rgba(96,165,250,0.2)' };
    };

    if (!hasData) {
        return (
            <div className="space-y-8 opacity-40">
                <div className="flex items-center gap-4">
                    <SkeletonPulse className="w-12 h-12 rounded-2xl" />
                    <div className="space-y-2">
                        <SkeletonPulse className="w-32 h-6" />
                        <SkeletonPulse className="w-24 h-4" />
                    </div>
                </div>
                <div className="grid grid-cols-3 gap-5">
                    <SkeletonPulse className="h-24" />
                    <SkeletonPulse className="h-24" />
                    <SkeletonPulse className="h-24" />
                </div>
            </div>
        );
    }

    const regimeColor = getStatusColor(regime || 'NEUTRAL');

    return (
        <div className="space-y-8 p-6">
            {/* ── Header ───────────────────────────────────────────────────── */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <div className="w-12 h-12 flex items-center justify-center rounded-2xl bg-blue-500/10 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                            <Brain className="w-6 h-6 text-blue-400" />
                        </div>
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-[#090e1a] animate-pulse" />
                    </div>
                    <div className="flex flex-col">
                        <h2 className="text-xl font-black text-white tracking-widest uppercase">Intelligence Command</h2>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black font-mono tracking-[0.2em] text-slate-500 uppercase">Neural Pipeline Active</span>
                            <div className="w-1 h-1 rounded-full bg-slate-700" />
                            <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400">ENGINE v5.0_SUPRA</span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3 bg-white/[0.03] border border-white/5 p-1.5 rounded-xl">
                    <div
                        className="px-4 py-2 rounded-lg border text-[11px] font-black font-mono tracking-[0.2em] transition-all duration-500"
                        style={{
                            borderColor: `${regimeColor.color}30`,
                            background: `${regimeColor.color}05`,
                            color: regimeColor.color,
                            boxShadow: `0 0 15px ${regimeColor.glow}`
                        }}
                    >
                        {regime}
                    </div>
                </div>
            </div>

            {/* ── Layer 1: Market State ────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {[
                    {
                        icon: <Activity className="w-4 h-4" />,
                        label: 'Risk Topology',
                        value: riskRegime,
                        color: getStatusColor(riskRegime).color,
                        sub: `Conf: ${(confidence * 100).toFixed(1)}%`,
                    },
                    {
                        icon: <TrendingUp className="w-4 h-4" />,
                        label: 'Synthetic Bias',
                        value: biasData.label,
                        color: getStatusColor(biasData.label).color,
                        sub: `Strength: ${(biasData.strength * 100).toFixed(1)}%`,
                    },
                    {
                        icon: <Shield className="w-4 h-4" />,
                        label: 'Confidence Interval',
                        value: `${(confidence * 100).toFixed(1)}%`,
                        color: '#fff',
                        sub: 'Supra-Sync Validation',
                    },
                ].map((item, idx) => (
                    <div key={idx} className="group rounded-2xl p-5 bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-all duration-300">
                        <div className="flex items-center gap-2 mb-3">
                            <div className="p-1.5 rounded-lg bg-white/5 group-hover:bg-blue-500/10 transition-colors">
                                {item.icon}
                            </div>
                            <span className="text-[10px] font-black font-mono tracking-[0.2em] text-slate-500 uppercase">{item.label}</span>
                        </div>
                        <div className="text-xl font-black font-mono tracking-tight mb-1 uppercase" style={{ color: item.color }}>
                            {item.value}
                        </div>
                        <div className="text-[10px] font-black font-mono text-slate-600 uppercase tracking-widest">
                            {item.sub}
                        </div>
                    </div>
                ))}
            </div>

            {/* ── Layer 2: Tactics ───────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="rounded-2xl p-6 bg-white/[0.02] border border-white/5">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-2">
                            <Eye className="w-4 h-4 text-blue-400" />
                            <span className="text-[11px] font-black font-mono tracking-[0.2em] text-slate-400 uppercase">Flow Intelligence</span>
                        </div>
                        <div className="px-2 py-0.5 rounded border border-blue-500/20 text-[9px] font-black font-mono text-blue-400">REALTIME CLUSTER</div>
                    </div>
                    <div className="grid grid-cols-2 gap-y-8 gap-x-12">
                        {[
                            { l: 'ORDER FLOW', v: regime || 'NEUTRAL', c: getStatusColor(regime || 'NEUTRAL').color },
                            { l: 'SIGNAL VECTOR', v: biasData.label, c: getStatusColor(biasData.label).color },
                            { l: 'PRESSURE REGIME', v: riskRegime || 'NONE', c: '#fff' },
                            { l: 'ADAPTIVE SCORE', v: (biasData.strength * 10).toFixed(1), c: '#fff' },
                        ].map((m, i) => (
                            <div key={i} className="flex flex-col gap-1">
                                <span className="text-[9px] font-black font-mono tracking-[0.2em] text-slate-600 uppercase">{m.l}</span>
                                <span className="text-[14px] font-black font-mono uppercase tracking-tight" style={{ color: m.c }}>{m.v}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="rounded-2xl p-6 bg-white/[0.02] border border-white/5">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-2">
                            <Zap className="w-4 h-4 text-blue-400" />
                            <span className="text-[11px] font-black font-mono tracking-[0.2em] text-slate-400 uppercase">Structural Engine</span>
                        </div>
                        <div className="px-2 py-0.5 rounded border border-blue-500/20 text-[9px] font-black font-mono text-blue-400">SYNCED</div>
                    </div>
                    <div className="grid grid-cols-2 gap-y-8 gap-x-12">
                        {[
                            { l: 'ANALYSIS STATE', v: aiReady ? 'SYNCHRONIZED' : 'INITIALIZING', c: '#fff' },
                            { l: 'CONFIDENCE ALPHA', v: `${(confidence * 100).toFixed(1)}%`, c: '#fff' },
                            { l: 'CONTRADICTIONS', v: 0, c: '#4ade80' },
                            { l: 'MODEL PIPELINE', v: 'STRIKE_IQ_PRO', c: '#60a5fa' },
                        ].map((m, i) => (
                            <div key={i} className="flex flex-col gap-1">
                                <span className="text-[9px] font-black font-mono tracking-[0.2em] text-slate-600 uppercase">{m.l}</span>
                                <span className="text-[14px] font-black font-mono uppercase tracking-tight" style={{ color: m.c }}>{m.v}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>


            {/* ── Synthesis Reasoning ─────────────────────────────────── */}
            <div className="relative p-6 rounded-2xl bg-white/[0.01] border border-white/5 border-dashed">
                <div className="flex items-center gap-2 mb-4">
                    <Info className="w-4 h-4 text-slate-600" />
                    <span className="text-[10px] font-black font-mono tracking-[0.2em] text-slate-600 uppercase">Synthesis Reasoning Node</span>
                </div>
                <p className="text-[13px] font-medium leading-relaxed text-slate-300 italic tracking-tight">
                    "{riskRegime || (hasData ? `${regime} | PCR: ${pcr?.toFixed(2)}` : '—')}"
                </p>
            </div>
        </div>
    );
};

export default memo(AICommandCenter);
