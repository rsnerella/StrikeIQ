import React, { memo } from 'react';
import { Brain, AlertTriangle, CheckCircle } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

const AIInterpretationPanel: React.FC = () => {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    
    // Direct selectors with fallbacks
    const interpretation = useWSStore(s => s.summary ?? '');
    const riskTopology = useWSStore(s => s.regime ?? 'STABLE');
    const structuralPos = useWSStore(s => s.regime ?? 'RANGING');
    const contradictions = [];
    const confidence = useWSStore(s => s.biasStrength ?? 0);

    if (!hasData) {
        return (
            <div className="relative p-6 opacity-40">
                <div className="flex justify-between mb-8">
                    <SkeletonPulse className="w-1/3 h-6" />
                    <SkeletonPulse className="w-24 h-6 rounded-full" />
                </div>
                <div className="space-y-6">
                    <SkeletonPulse className="w-full h-24" />
                    <div className="grid grid-cols-2 gap-4">
                        <SkeletonPulse className="h-16" />
                        <SkeletonPulse className="h-16" />
                    </div>
                </div>
            </div>
        );
    }

    const getToneConfig = (conf: number) => {
        if (conf > 0.8) return { color: '#00E5FF', icon: <CheckCircle className="w-4 h-4" />, label: 'HIGH CONFIDENCE' };
        if (conf > 0.5) return { color: '#fbbf24', icon: <Brain className="w-4 h-4" />, label: 'ADAPTIVE MODE' };
        return { color: '#f87171', icon: <AlertTriangle className="w-4 h-4" />, label: 'CAUTIOUS' };
    };

    const config = getToneConfig(confidence);

    return (
        <div className="relative overflow-visible p-6">
            {/* Header Cluster */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-black font-mono tracking-[0.2em] text-slate-500 uppercase">Autonomous Intelligence Synthesis</span>
                    <div className="flex items-center gap-2">
                        <div className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-40" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                        </div>
                        <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400">ENGINE v5.0_SUPRA_SYNC</span>
                    </div>
                </div>

                <div
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-500"
                    style={{
                        borderColor: `${config.color}30`,
                        background: `${config.color}05`,
                        color: config.color,
                        boxShadow: `0 0 15px ${config.color}10`
                    }}
                >
                    {config.icon}
                    <span className="text-[10px] font-bold font-mono tracking-widest">{config.label}</span>
                </div>
            </div>

            {/* Core Summary */}
            <div className="relative mb-8 p-6 rounded-2xl bg-white/[0.02] border border-white/5 backdrop-blur-sm group hover:bg-white/[0.04] transition-all duration-500">
                <div className="absolute top-0 left-0 w-12 h-[2px] bg-blue-500/50" />
                <div className="absolute top-0 left-0 w-[2px] h-12 bg-blue-500/50" />

                <h4 className="text-[9px] font-black font-mono tracking-[0.3em] text-slate-600 mb-4 uppercase text-center">Market Synthesis</h4>
                <p className="text-[16px] font-medium leading-relaxed text-slate-200 font-sans tracking-tight italic text-center">
                    "{interpretation || (hasData ? `${structuralPos} | Confidence: ${(confidence * 100).toFixed(1)}%` : '—')}"
                </p>
            </div>

            {/* Structural Intelligence Cluster */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                <div className="rounded-xl p-4 bg-white/[0.02] border border-white/5 transition-all hover:bg-white/[0.04]">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-1 h-3 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)]" />
                        <span className="text-[9px] font-black font-mono tracking-widest text-slate-500 uppercase">Risk Topology</span>
                    </div>
                    <p className="text-sm font-black text-white font-mono leading-tight tracking-tighter uppercase tabular-nums">
                        {riskTopology || 'STABLE'}
                    </p>
                </div>

                <div className="rounded-xl p-4 bg-white/[0.02] border border-white/5 transition-all hover:bg-white/[0.04]">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-1 h-3 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                        <span className="text-[9px] font-black font-mono tracking-widest text-slate-500 uppercase">Pos. Structural</span>
                    </div>
                    <p className="text-sm font-black text-white font-mono leading-tight tracking-tighter uppercase tabular-nums">
                        {structuralPos || 'EQUILIBRIUM'}
                    </p>
                </div>
            </div>

            {/* Abnormalities Module */}
            <div className="rounded-xl p-4 bg-red-500/[0.02] border border-red-500/10 border-dashed">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <span className="text-[10px] font-black font-mono tracking-widest text-red-500 uppercase">Structural Contradictions</span>
                    </div>
                </div>

                <div className="flex flex-wrap gap-2">
                    {contradictions.length > 0 ? contradictions.map((flag, idx) => (
                        <div key={idx} className="px-2 py-1 rounded bg-red-500/10 border border-red-500/20 text-[10px] font-black font-mono text-red-400 uppercase tracking-tighter">
                            {flag}
                        </div>
                    )) : (
                        <div className="text-[10px] font-mono text-slate-600 italic tracking-wider">NO STRUCTURAL ANOMALIES DETECTED IN CURRENT TAPE.</div>
                    )}
                </div>
            </div>

            {/* Footer Metrics */}
            <div className="mt-8 pt-4 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5 opacity-60">
                         <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                         <span className="text-[8px] font-black font-mono text-slate-500 uppercase">Pipeline Live</span>
                    </div>
                    <div className="flex items-center gap-1.5 opacity-60">
                         <div className="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_5px_rgba(59,130,246,0.5)]" />
                         <span className="text-[8px] font-black font-mono text-slate-500 uppercase">Model: Strike_IQ_v5</span>
                    </div>
                </div>
                <span className="text-[9px] font-black font-mono text-slate-600 uppercase tracking-[0.2em]">
                    Institutional Grade Analysis
                </span>
            </div>
        </div>
    );
};

export default memo(AIInterpretationPanel);

