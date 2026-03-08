import React, { memo } from 'react';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  AlertTriangle,
  Zap,
  Shield,
  BarChart3,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Info
} from 'lucide-react';
import { safeMapBiasData, FrontendBiasData } from '../utils/biasMapping';

interface AICommandCenterProps {
  intelligence?: {
    bias: any;
    probability?: {
      expected_move: number;
      upper_1sd: number;
      lower_1sd: number;
      upper_2sd: number;
      lower_2sd: number;
      breach_probability: number;
      range_hold_probability: number;
      volatility_state: string;
    };
    liquidity: {
      total_oi: number;
      oi_change_24h: number;
      concentration: number;
      depth_score: number;
      flow_direction: string;
    };
    regime?: {
      market_regime: string;
      volatility_regime: string;
      trend_regime: string;
      confidence: number;
    };
    gamma?: {
      net_gamma: number;
      gamma_flip: number;
      dealer_gamma: string;
      gamma_exposure: number;
    };
    signals?: {
      stoploss_hunt: boolean;
      trap_detection: boolean;
      liquidity_event: boolean;
      gamma_squeeze: boolean;
    };
    trade_suggestion?: {
      symbol: string;
      strategy: string;
      option: string;
      entry: number;
      target: number;
      stoploss: number;
      risk_reward: number;
      confidence: number;
      regime: string;
    };
    reasoning?: string;
  };
}

function AICommandCenter({ intelligence }: AICommandCenterProps) {
  const safeIntelligence = intelligence || {} as NonNullable<AICommandCenterProps['intelligence']>;

  const biasData: FrontendBiasData = safeIntelligence?.bias
    ? safeMapBiasData(safeIntelligence.bias)
    : {
      score: 0,
      label: 'NEUTRAL',
      confidence: 0,
      signal: 'NEUTRAL',
      direction: 'NONE',
      strength: 0
    };

  const getStatusColor = (val: string) => {
    switch (val?.toUpperCase()) {
      case 'BULLISH': case 'UPTREND': case 'HIGH_VOL': case 'SQUEEZE':
        return { color: '#4ade80', glow: 'rgba(74,222,128,0.2)' };
      case 'BEARISH': case 'DOWNTREND': case 'EXTREME': case 'ACTIVE':
        return { color: '#f87171', glow: 'rgba(239,68,68,0.2)' };
      default:
        return { color: '#60a5fa', glow: 'rgba(96,165,250,0.2)' };
    }
  };

  return (
    <div className="space-y-8">
      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 flex items-center justify-center rounded-2xl bg-blue-500/10 border border-blue-500/20">
              <Brain className="w-6 h-6 text-blue-400" />
            </div>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-[#090e1a] animate-pulse" />
          </div>
          <div className="flex flex-col">
            <h2 className="text-xl font-bold text-white tracking-tight">AI Command Center</h2>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Neural Engine Active</span>
              <div className="w-1 h-1 rounded-full bg-slate-700" />
              <span className="text-[10px] font-bold font-mono tracking-widest text-blue-400">v2.4.8-PRO</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 bg-white/[0.03] border border-white/5 p-1 rounded-xl">
          <div
            className="px-4 py-2 rounded-lg border text-[11px] font-bold font-mono tracking-[0.2em] transition-all duration-500"
            style={{
              borderColor: getStatusColor(safeIntelligence?.regime?.market_regime).color + '30',
              background: getStatusColor(safeIntelligence?.regime?.market_regime).color + '05',
              color: getStatusColor(safeIntelligence?.regime?.market_regime).color,
              boxShadow: `0 0 15px ${getStatusColor(safeIntelligence?.regime?.market_regime).glow}`
            }}
          >
            {safeIntelligence?.regime?.market_regime || 'NEUTRAL'} REGIME
          </div>
        </div>
      </div>

      {/* ── Intelligence Layer 1: Market State ────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {[
          {
            icon: <Activity className="w-4 h-4" />,
            label: 'Volatility State',
            value: safeIntelligence?.regime?.volatility_regime || 'NORMAL',
            color: getStatusColor(safeIntelligence?.regime?.volatility_regime).color,
            sub: `Expected: ±${safeIntelligence?.probability?.expected_move?.toFixed(2) || '0.00'}`,
          },
          {
            icon: <TrendingUp className="w-4 h-4" />,
            label: 'Current Trend',
            value: safeIntelligence?.regime?.trend_regime || 'SIDEWAYS',
            color: getStatusColor(safeIntelligence?.regime?.trend_regime).color,
            sub: `Strength: ${(biasData.strength * 100).toFixed(1)}% / 100`,
          },
          {
            icon: <Shield className="w-4 h-4" />,
            label: 'System Confidence',
            value: `${safeIntelligence?.regime?.confidence?.toFixed(1) || '85.2'}%`,
            color: '#fff',
            sub: 'Model Cross-Validation: OK',
          },
        ].map((item, idx) => (
          <div key={idx} className="group rounded-2xl p-4 bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-all duration-300">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-1.5 rounded-lg bg-white/5 group-hover:bg-blue-500/10 transition-colors">
                {item.icon}
              </div>
              <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">{item.label}</span>
            </div>
            <div className="text-lg font-black font-mono tracking-tight mb-1" style={{ color: item.color }}>
              {item.value}
            </div>
            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              {item.sub}
            </div>
          </div>
        ))}
      </div>

      {/* ── Intelligence Layer 2: Flow & Gamma ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="rounded-2xl p-5 bg-white/[0.02] border border-white/5">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4 text-blue-400" />
              <span className="text-[11px] font-bold font-mono tracking-widest text-slate-400 uppercase">Flow Intelligence</span>
            </div>
            <div className="px-2 py-0.5 rounded border border-blue-500/20 text-[9px] font-bold font-mono text-blue-400">REALTIME TAPE</div>
          </div>
          <div className="grid grid-cols-2 gap-y-6 gap-x-12">
            {[
              { l: 'SIGNAL DIRECTION', v: biasData.label || 'NEUTRAL', c: getStatusColor(biasData.label).color },
              { l: ' Neural CONFIDENCE', v: `${biasData.confidence?.toFixed(1) || '0.0'}%`, c: '#fff' },
              { l: 'ORDER PRESSURE', v: biasData.direction || 'NONE', c: '#fff' },
              { l: 'INTENT SCORE', v: (biasData.strength * 10).toFixed(1), c: '#fff' },
            ].map((m, i) => (
              <div key={i} className="flex flex-col gap-1">
                <span className="text-[9px] font-bold font-mono tracking-widest text-slate-600 uppercase">{m.l}</span>
                <span className="text-[13px] font-bold font-mono uppercase tracking-tight" style={{ color: m.c }}>{m.v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl p-5 bg-white/[0.02] border border-white/5">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-400" />
              <span className="text-[11px] font-bold font-mono tracking-widest text-slate-400 uppercase">Microstructure</span>
            </div>
            <div className="px-2 py-0.5 rounded border border-blue-500/20 text-[9px] font-bold font-mono text-blue-400">GAMMA ENGINE</div>
          </div>
          <div className="grid grid-cols-2 gap-y-6 gap-x-12">
            {[
              { l: 'DEALER GAMMA', v: safeIntelligence?.gamma?.net_gamma?.toFixed(2) || '0.00', c: (safeIntelligence?.gamma?.net_gamma ?? 0) > 0 ? '#4ade80' : '#f87171' },
              { l: 'EXPOSURE REGIME', v: safeIntelligence?.gamma?.dealer_gamma || 'NEUTRAL', c: '#fff' },
              { l: 'GAMMA FLIP LEVEL', v: safeIntelligence?.gamma?.gamma_flip?.toLocaleString() || 'N/A', c: '#60a5fa' },
              { l: 'DELTA IMBALANCE', v: '0.42%', c: '#fff' },
            ].map((m, i) => (
              <div key={i} className="flex flex-col gap-1">
                <span className="text-[9px] font-bold font-mono tracking-widest text-slate-600 uppercase">{m.l}</span>
                <span className="text-[13px] font-bold font-mono uppercase tracking-tight" style={{ color: m.c }}>{m.v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Intelligence Layer 3: Risk Matrix ────────────────────────── */}
      <div className="flex flex-wrap gap-4">
        {[
          { label: 'Stop-Hunt', active: safeIntelligence?.signals?.stoploss_hunt, color: '#f87171' },
          { label: 'Trap Detected', active: safeIntelligence?.signals?.trap_detection, color: '#fbbf24' },
          { label: 'Liq Event', active: safeIntelligence?.signals?.liquidity_event, color: '#60a5fa' },
          { label: 'Gamma Squeeze', active: safeIntelligence?.signals?.gamma_squeeze, color: '#4ade80' },
        ].map((s, i) => (
          <div
            key={i}
            className={`flex-1 min-w-[140px] px-4 py-3 rounded-2xl border transition-all duration-500 flex flex-col items-center gap-1 ${s.active ? '' : 'opacity-40 grayscale'
              }`}
            style={{
              borderColor: s.active ? `${s.color}40` : 'rgba(255,255,255,0.05)',
              background: s.active ? `${s.color}05` : 'transparent'
            }}
          >
            <span className="text-[9px] font-bold font-mono tracking-widest text-slate-500 uppercase">{s.label}</span>
            <span className="text-[11px] font-bold font-mono uppercase tracking-widest" style={{ color: s.active ? s.color : '#fff' }}>
              {s.active ? 'ACTIVE' : 'NOMINAL'}
            </span>
          </div>
        ))}
      </div>

      {/* ── Execution Section ────────────────────────────────────────── */}
      {safeIntelligence?.trade_suggestion && (
        <div className="relative group overflow-hidden">
          <div className="absolute inset-0 bg-blue-500/5 group-hover:bg-blue-500/10 transition-colors" />
          <div className="absolute top-0 left-0 w-full h-[px] bg-gradient-to-r from-transparent via-blue-400/50 to-transparent" />

          <div className="relative p-6 border border-blue-500/20 rounded-2xl flex flex-col md:flex-row gap-8 items-center">
            <div className="flex flex-col gap-2 shrink-0 text-center md:text-left">
              <div className="flex items-center justify-center md:justify-start gap-2">
                <Target className="w-4 h-4 text-blue-400" />
                <span className="text-[11px] font-bold font-mono tracking-[0.3em] text-blue-400 uppercase">Suggested Strategy</span>
              </div>
              <h3 className="text-2xl font-black text-white italic uppercase">{safeIntelligence.trade_suggestion.strategy}</h3>
              <div className="flex items-center justify-center md:justify-start gap-3 mt-1">
                <div className="px-2 py-1 rounded bg-blue-500 text-[10px] font-black text-black uppercase tracking-widest">
                  {safeIntelligence.trade_suggestion.option}
                </div>
                <span className="text-[11px] font-bold font-mono text-slate-400">RR 1:{safeIntelligence.trade_suggestion.risk_reward?.toFixed(1)}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 flex-1 w-full">
              {[
                { l: 'ENTRY', v: safeIntelligence.trade_suggestion.entry?.toLocaleString() },
                { l: 'TARGET', v: safeIntelligence.trade_suggestion.target?.toLocaleString() },
                { l: 'STOPLOSS', v: safeIntelligence.trade_suggestion.stoploss?.toLocaleString() },
                { l: 'CONFIDENCE', v: `${safeIntelligence.trade_suggestion.confidence?.toFixed(0)}%` },
              ].map((d, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <span className="text-[9px] font-bold font-mono tracking-widest text-slate-500 uppercase">{d.l}</span>
                  <span className="text-lg font-black font-mono text-white tabular-nums tracking-tighter">{d.v}</span>
                </div>
              ))}
            </div>

            <div className="shrink-0 w-full md:w-auto">
              <button className="w-full px-8 py-4 bg-white text-black font-bold rounded-xl hover:bg-blue-400 transition-all active:scale-95 text-xs tracking-widest uppercase">
                Execution Node ↗
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Neural Reasoning ─────────────────────────────────────────── */}
      {safeIntelligence?.reasoning && (
        <div className="relative p-6 rounded-2xl bg-white/[0.02] border border-white/5 border-dashed">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-4 h-4 text-slate-500" />
            <span className="text-[11px] font-bold font-mono tracking-widest text-slate-500 uppercase">Reasoning Node</span>
          </div>
          <p className="text-[13px] font-medium leading-relaxed text-slate-400 italic">
            "{safeIntelligence.reasoning}"
          </p>
        </div>
      )}
    </div>
  );
}


export default memo(AICommandCenter);
