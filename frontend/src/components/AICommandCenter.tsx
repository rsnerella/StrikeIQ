import React, { memo, useMemo } from 'react';
import { Brain, TrendingUp, Target, Activity,
         Zap, Shield, Eye, Info } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';

const SkeletonPulse = ({ className }: { className: string }) => (
  <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

export function AICommandCenter() {
  // Single store subscription to prevent infinite loops
  const storeData = useWSStore(s => ({ 
    lastUpdate: s.lastUpdate,
    chartAnalysis: s.chartAnalysis,
    spot: s.spot ?? s.spotPrice ?? 0
  }));
  
  const { lastUpdate, chartAnalysis: analysis, spot } = storeData;
  const hasData = lastUpdate > 0 && !!analysis;

  // v5.2 SUPRA-ORCHESTRATOR Mapping
  const regime       = analysis?.regime || 'NEUTRAL';
  const bias         = analysis?.bias || 'NEUTRAL';
  const biasStrength = analysis?.bias_strength || 0;
  const pcr          = analysis?.market_context?.pcr || 0;
  const callWall     = analysis?.key_levels?.call_wall || 0;
  const putWall      = analysis?.key_levels?.put_wall || 0;
  const ivAtm        = analysis?.volatility_state?.iv_atm || 0;
  const netGex        = analysis?.gamma_analysis?.net_gex || 0;
  const summary       = analysis?.summary || '';
  const sentiment     = analysis?.sentiment_overlay;
  const intel         = analysis?.chart_intelligence;
  const latency       = analysis?.computation_ms || 0;
  const confidence    = analysis?.confidence || 0;

  const getColor = (val: string) => {
    const v = (val ?? '').toUpperCase();
    if (v.includes('POSITIVE') || v.includes('BULL') || v.includes('LONG') || v.includes('UP'))
      return { color: '#4ade80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' };
    if (v.includes('NEGATIVE') || v.includes('BEAR') || v.includes('SHORT') || v.includes('DOWN'))
      return { color: '#f87171', bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.2)' };
    return { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', border: 'rgba(96,165,250,0.2)' };
  };

  const status = getColor(regime);

  if (!hasData) {
    return (
      <div className="p-8 space-y-6 opacity-40">
        <div className="flex items-center gap-4">
          <SkeletonPulse className="w-12 h-12 rounded-xl" />
          <div className="space-y-2">
            <SkeletonPulse className="w-48 h-6" />
            <SkeletonPulse className="w-32 h-4" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <SkeletonPulse className="h-24 rounded-xl" />
          <SkeletonPulse className="h-24 rounded-xl" />
          <SkeletonPulse className="h-24 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 flex flex-col gap-6 relative overflow-hidden">
      {/* Background Decorative Pulsar */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
        <div className="flex items-center gap-5">
          <div className="relative group">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 border border-white/10 flex items-center justify-center backdrop-blur-xl shadow-2xl transition-all duration-500 group-hover:scale-105">
              <Brain className="w-7 h-7 text-blue-400" />
            </div>
            <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-emerald-500 rounded-full border-2 border-[#0a0a0b] shadow-[0_0_10px_#10b981]" />
          </div>
          <div>
            <h2 className="text-2xl font-black text-white tracking-widest uppercase">Intelligence Command</h2>
            <div className="flex items-center gap-3 mt-1 opacity-70">
              <div className="flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-blue-400 animate-pulse" />
                <span className="text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest">Master Orchestrator Active</span>
              </div>
              <div className="w-1 h-1 rounded-full bg-slate-700" />
              <div className="text-[9px] font-black font-mono text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded border border-blue-400/20">SUPRA_v5.2</div>
              {latency > 0 && (
                <>
                  <div className="w-1 h-1 rounded-full bg-slate-700" />
                  <div className="text-[9px] font-black font-mono text-indigo-400">⚡ {latency.toFixed(1)}ms</div>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-white/[0.03] p-1.5 rounded-2xl border border-white/5 backdrop-blur-md">
           <div 
             className="px-5 py-2 rounded-xl text-[11px] font-black font-mono tracking-widest border transition-all duration-500 uppercase"
             style={{ color: status.color, backgroundColor: status.bg, borderColor: status.border, boxShadow: `0 0 20px ${status.bg}` }}
           >
             {regime}
           </div>
        </div>
      </div>

      {/* Grid Layer: Structural Integrity */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
        {[
          { label: 'Risk Topology', main: regime, sub: `${bias} BIAS`, icon: Activity, color: status.color },
          { label: 'Conviction', main: `${(confidence * 100).toFixed(0)}%`, sub: 'NEURAL SCORE', icon: Zap, color: '#facc15' },
          { label: 'Market Bias', main: bias, sub: `${(biasStrength * 100).toFixed(1)}% STR`, icon: Target, color: '#60a5fa' },
          { label: 'Sentiment', main: sentiment?.sentiment || 'NEUTRAL', sub: sentiment?.status || 'STABLE', icon: Shield, color: getColor(sentiment?.sentiment).color }
        ].map((card, i) => (
          <div key={i} className="group p-4 rounded-2xl bg-white/[0.01] border border-white/5 hover:bg-white/[0.03] transition-all duration-500 hover:border-white/10">
            <div className="flex items-center gap-2 mb-3">
              <card.icon className="w-3.5 h-3.5 text-slate-500 group-hover:text-white transition-colors" />
              <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-[0.2em]">{card.label}</span>
            </div>
            <div className="text-lg font-black font-mono tracking-tight text-white mb-1 uppercase leading-none" style={{ color: card.color }}>{card.main}</div>
            <div className="text-[8px] font-bold font-mono text-slate-500 tracking-widest uppercase">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Synthesis & Pattern Node */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 relative z-10">
        {/* Dynamic Summary */}
        <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/5 border-dashed relative group">
          <div className="flex items-center gap-3 mb-3 opacity-70">
            <Info className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-[9px] font-black font-mono text-slate-400 uppercase tracking-widest">Neural Synthesis</span>
          </div>
          <p className="text-[13px] font-medium leading-relaxed text-slate-300 italic font-sans min-h-[40px]">
            "{summary || "Operational data parsing in progress. Structural integrity stable."}"
          </p>
          <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/10 rounded-tl-lg" />
          <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/10 rounded-br-lg" />
        </div>

        {/* Pattern Recognition Node */}
        <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/5 relative group">
          <div className="flex items-center gap-3 mb-3 opacity-70">
            <Eye className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-[9px] font-black font-mono text-slate-400 uppercase tracking-widest">Deep Pattern Recon</span>
          </div>
          {intel?.pattern_detected ? (
            <div className="space-y-1.5 text-slate-300">
               <div className="text-[11px] font-black font-mono text-indigo-400">{intel.pattern_detected}</div>
               <div className="text-[10px] opacity-70 line-clamp-2 leading-snug">{intel.analysis_summary}</div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-slate-500 mt-2">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-700 animate-pulse" />
              <span className="text-[10px] font-bold font-mono tracking-tight uppercase">Scanning Structural Formations...</span>
            </div>
          )}
          <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-white/10 rounded-tr-lg" />
          <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-white/10 rounded-bl-lg" />
        </div>
      </div>

      {/* Advanced Metrics Footer */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 py-4 border-t border-white/5 relative z-10">
        {[
          { l: 'CALL WALL', v: callWall.toLocaleString(), c: '#f87171' },
          { l: 'PUT WALL', v: putWall.toLocaleString(), c: '#4ade80' },
          { l: 'NET GEX', v: (netGex/1e6).toFixed(1) + 'M', c: netGex > 0 ? '#4ade80' : '#f87171' },
          { l: 'IV_ATM', v: (ivAtm * 100).toFixed(1) + '%', c: '#60a5fa' }
        ].map((m, i) => (
          <div key={i} className="flex flex-col gap-1">
            <span className="text-[8px] font-black font-mono text-slate-600 uppercase tracking-widest">{m.l}</span>
            <span className="text-[13px] font-black font-mono text-white tabular-nums tracking-tight" style={{ color: m.c }}>{m.v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default memo(AICommandCenter);
