import React, { memo } from 'react';
import { Brain, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';

interface AIInterpretation {
  narrative: string | null;
  risk_context: string | null;
  positioning_context: string | null;
  contradiction_flags: string[];
  confidence_tone: 'high' | 'medium' | 'cautious';
  interpreted_at?: string;
  fallback?: boolean;
}

interface AIInterpretationPanelProps {
  intelligence?: {
    interpretation: AIInterpretation;
  };
}

const AIInterpretationPanel: React.FC<AIInterpretationPanelProps> = ({ intelligence }) => {
  // Get real AI signals from store
  const analytics = useWSStore(state => state.analytics);
  
  const interpretation = intelligence?.interpretation ?? {
    narrative: analytics?.narrative || null,
    risk_context: analytics?.risk_context || null,
    positioning_context: analytics?.positioning_context || null,
    contradiction_flags: analytics?.contradiction_flags || [],
    confidence_tone: analytics?.confidence_tone || 'cautious',
    interpreted_at: analytics?.interpreted_at,
    fallback: !analytics || Object.keys(analytics).length === 0
  };

  const getToneConfig = (tone: string) => {
    switch (tone) {
      case 'high':
        return { color: '#00E5FF', icon: <CheckCircle className="w-4 h-4" />, label: 'HIGH CONFIDENCE' };
      case 'medium':
        return { color: '#fbbf24', icon: <Brain className="w-4 h-4" />, label: 'ADAPTIVE MODE' };
      default:
        return { color: '#f87171', icon: <AlertTriangle className="w-4 h-4" />, label: 'CAUTIOUS' };
    }
  };

  const config = getToneConfig(interpretation.confidence_tone);

  return (
    <div className="relative overflow-visible">
      {/* Narrative Section */}
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <span className="panel-label">Autonomous Intelligence Narrative</span>
            <div className="flex items-center gap-2">
              <div className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-40" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
              </div>
              <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400">ENGINE v2.1.0-LIVE_SYNC</span>
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

        {/* The Narrative */}
        <div className="relative p-6 rounded-2xl bg-white/[0.02] border border-white/5 backdrop-blur-sm group hover:bg-white/[0.04] transition-all duration-500">
          <div className="absolute top-0 left-0 w-12 h-[2px] bg-blue-500/50" />
          <div className="absolute top-0 left-0 w-[2px] h-12 bg-blue-500/50" />

          <h4 className="text-[11px] font-bold font-mono tracking-widest text-slate-500 mb-4 uppercase">Market Synthesis</h4>
          <p className="text-[15px] font-medium leading-relaxed text-slate-300 font-sans tracking-tight">
            {interpretation.narrative || (interpretation.fallback ? 'Aggregating order flow and market microstructure data for real-time synthesis...' : 'Market data stream incomplete.')}
          </p>
        </div>

        {/* Intelligence Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl p-4 bg-white/[0.02] border border-white/5 transition-all hover:bg-white/[0.04]">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1 h-3 rounded-full bg-orange-500" />
              <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Risk Topology</span>
            </div>
            <p className="text-[13px] font-bold text-white font-mono leading-relaxed">
              {interpretation.risk_context || 'QUANTITATIVE RISK SCAN IN PROGRESS...'}
            </p>
          </div>

          <div className="rounded-xl p-4 bg-white/[0.02] border border-white/5 transition-all hover:bg-white/[0.04]">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1 h-3 rounded-full bg-blue-500" />
              <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Pos. Structural</span>
            </div>
            <p className="text-[13px] font-bold text-white font-mono leading-relaxed">
              {interpretation.positioning_context || 'DEALER POSITIONING ANALYSIS STABLE'}
            </p>
          </div>
        </div>

        {/* Anomalies */}
        <div className="rounded-xl p-4 bg-red-500/[0.02] border border-red-500/10 border-dashed">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-[11px] font-bold font-mono tracking-widest text-red-400 uppercase">Structural Anomalies Detected</span>
            </div>
            <div className="px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-[9px] font-bold font-mono text-red-500">
              PRIORITY SCAN
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2">
            {(interpretation.contradiction_flags && interpretation.contradiction_flags.length > 0)
              ? interpretation.contradiction_flags.map((flag, index) => (
                <div key={index} className="flex items-center gap-2 text-[11px] font-mono text-red-300 opacity-80 hover:opacity-100 transition-opacity">
                  <div className="w-1 h-1 bg-red-400/50 rounded-full" />
                  <span>{flag}</span>
                </div>
              ))
              : <div className="text-[11px] font-mono text-slate-500 italic">No structural contradictions found in the current tape.</div>
            }
          </div>
        </div>

        <div className="flex items-center justify-between px-2 pt-2 border-t border-white/5">
          <div className="flex gap-4">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500/50" />
              <span className="text-[9px] font-bold font-mono text-slate-600 uppercase">Data Pipeline Stable</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
              <span className="text-[9px] font-bold font-mono text-slate-600 uppercase">Model: Strike_IQ_V4</span>
            </div>
          </div>
          <span className="text-[9px] font-bold font-mono text-slate-600 uppercase">
            SYNC: {interpretation.interpreted_at ? new Date(interpretation.interpreted_at).toLocaleTimeString() : 'REALTIME'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default memo(AIInterpretationPanel);

