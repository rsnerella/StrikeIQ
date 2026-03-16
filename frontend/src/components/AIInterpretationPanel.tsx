import React, { memo } from 'react';
import { Brain, AlertTriangle, CheckCircle, Activity } from 'lucide-react';
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
    const earlyWarnings = useWSStore(s => s.earlyWarnings ?? []);
    const confidence = useWSStore(s => s.biasStrength ?? 0);

    if (!hasData) {
        return (
            <div className="relative p-5 opacity-40 h-full flex flex-col justify-center">
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
        <div className="relative overflow-visible p-5 flex flex-col h-full scanline-overlay">
            {/* Header Cluster */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex flex-col gap-1.5">
                    <span className="text-[10px] font-black font-mono tracking-[0.4em] text-slate-500 uppercase opacity-80">Autonomous Logic Synthesis</span>
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-2.5 w-2.5 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-30 px-1" />
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.6)]" />
                        </div>
                        <span className="text-[11px] font-black font-mono tracking-widest text-slate-200 uppercase">COGNITIVE_ENGINE_v5</span>
                    </div>
                </div>

                <div
                    className="flex items-center gap-2.5 px-4 py-2 rounded-xl border-2 transition-all duration-700 shadow-lg"
                    style={{
                        borderColor: `${config.color}40`,
                        background: `${config.color}10`,
                        color: config.color,
                        boxShadow: `0 0 25px ${config.color}15`
                    }}
                >
                    {config.icon}
                    <span className="text-[10px] font-black font-mono tracking-[0.2em]">{config.label}</span>
                </div>
            </div>

            {/* Core Summary */}
            <div className="relative mb-6 p-5 rounded-3xl bg-white/[0.015] border border-white/10 backdrop-blur-2xl group hover:bg-white/[0.03] transition-all duration-700 shadow-2xl flex-grow overflow-hidden">
                <div className="absolute top-0 left-0 w-12 h-[1px] bg-gradient-to-r from-blue-500/80 to-transparent" />
                <div className="absolute top-0 left-0 w-[1px] h-12 bg-gradient-to-b from-blue-500/80 to-transparent" />
                <div className="absolute bottom-0 right-0 w-12 h-[1px] bg-gradient-to-l from-blue-500/40 to-transparent" />
                <div className="absolute bottom-0 right-0 w-[1px] h-12 bg-gradient-to-t from-blue-500/40 to-transparent" />

                <h4 className="text-[9px] font-black font-mono tracking-[0.4em] text-slate-500 mb-4 uppercase text-center opacity-60">Neural Narrative Analysis</h4>
                <p className="text-[16px] font-medium leading-[1.6] text-slate-100 font-sans tracking-tight italic text-center drop-shadow-sm px-2">
                    "{interpretation || (hasData ? `${structuralPos} | Bias: ${(confidence * 100).toFixed(1)}%` : '—')}"
                </p>
                
                <div className="mt-8 flex justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500/20 animate-pulse" />
                </div>
            </div>

            {/* Structural Intelligence Cluster */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="rounded-2xl p-4 bg-white/[0.02] border border-white/10 transition-all hover:bg-white/[0.05] shadow-sm">
                    <div className="flex items-center gap-2 mb-2.5">
                        <div className="w-1 h-3 rounded-full bg-orange-500 shadow-[0_0_12px_rgba(249,115,22,0.6)]" />
                        <span className="text-[9px] font-black font-mono tracking-widest text-slate-500 uppercase">Topology</span>
                    </div>
                    <p className="text-sm font-black text-white font-mono leading-none tracking-normal uppercase tabular-nums">
                        {riskTopology || 'STABLE'}
                    </p>
                </div>

                <div className="rounded-2xl p-4 bg-white/[0.02] border border-white/10 transition-all hover:bg-white/[0.05] shadow-sm">
                    <div className="flex items-center gap-2 mb-2.5">
                        <div className="w-1 h-3 rounded-full bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.6)]" />
                        <span className="text-[9px] font-black font-mono tracking-widest text-slate-500 uppercase">Structure</span>
                    </div>
                    <p className="text-sm font-black text-white font-mono leading-none tracking-normal uppercase tabular-nums">
                        {structuralPos || 'EQUILIBRIUM'}
                    </p>
                </div>
            </div>

            {/* Contradictions Module */}
            <div className="rounded-2xl p-4 bg-red-500/[0.03] border border-red-500/20 border-dashed backdrop-blur-sm">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                        <span className="text-[10px] font-black font-mono tracking-[0.25em] text-red-500 uppercase">Neural Contradictions</span>
                    </div>
                </div>

                <div className="flex flex-wrap gap-2.5">
                    {earlyWarnings.length > 0 ? earlyWarnings.map((flag, idx) => (
                        <div key={idx} className="px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-[10px] font-black font-mono text-red-400 uppercase tracking-tighter shadow-md">
                            {flag.alert_type || flag.type || 'WARNING'}
                        </div>
                    )) : (
                        <div className="text-[10px] font-black font-mono text-slate-600 italic tracking-widest pl-1 uppercase opacity-60">Zero Abnormalities Identified</div>
                    )}
                </div>
            </div>

            {/* Footer Metrics */}
            <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2 opacity-60">
                         <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                         <span className="text-[8px] font-black font-mono text-slate-500 uppercase tracking-widest">Pipeline Live</span>
                    </div>
                    <div className="flex items-center gap-2 opacity-60 md:flex hidden">
                         <div className="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                         <span className="text-[8px] font-black font-mono text-slate-500 uppercase tracking-widest">Strike_IQ_Engine</span>
                    </div>
                </div>
                <span className="text-[9px] font-black font-mono text-slate-600 uppercase tracking-[0.3em] opacity-40">
                    Institutional Standard
                </span>
            </div>
        </div>
    );
};

export default memo(AIInterpretationPanel);
