import React, { memo } from 'react';
import { TrendingUp, TrendingDown, Target, Shield, Activity, BarChart3, Info, AlertTriangle, Zap } from 'lucide-react';

interface InstitutionalBiasProps {
  intelligence?: {
    bias: {
      score: number;
      label: string;
      strength: number;
      direction: string;
      confidence: number;
      signal: string;
    };
    volatility: {
      current: string;
      percentile: number;
      trend: string;
      risk: string;
      environment: string;
    };
    liquidity: {
      total_oi: number;
      oi_change_24h: number;
      concentration: number;
      depth_score: number;
      flow_direction: string;
    };
  };
  spotPrice?: number;
  marketStatus?: string;
  marketChange?: number;
  marketChangePercent?: number;
}

export default memo(function InstitutionalBias({ intelligence, spotPrice, marketStatus, marketChange, marketChangePercent }: InstitutionalBiasProps) {
  if (!intelligence || !intelligence.bias) {
    return (
      <div className="bg-[#111827] rounded-xl p-5 border border-[#1F2937] h-full flex flex-col items-center justify-center space-y-4">
        <div className="w-12 h-12 border-2 border-gray-700 border-t-gray-500 rounded-full animate-spin" />
        <div className="text-center">
          <h2 className="text-xl font-bold text-white mb-2">Bias Matrix Loading...</h2>
          <p className="text-gray-500 font-mono text-xs tracking-wider">Synchronizing institutional flows</p>
        </div>
      </div>
    );
  }

  const { bias, volatility, liquidity } = intelligence;

  const biasLabel = (bias.label || "NEUTRAL").toUpperCase();
  const biasColor = biasLabel.includes("BULL") ? "text-[#00FF9F]" : biasLabel.includes("BEAR") ? "text-[#FF4D4F]" : "text-[#FFC857]";

  const getBiasIcon = () => {
    if (biasLabel.includes("BULL")) {
      return <TrendingUp className="w-6 h-6 text-[#00FF9F]" />;
    } else if (biasLabel.includes("BEAR")) {
      return <TrendingDown className="w-6 h-6 text-[#FF4D4F]" />;
    } else {
      return <Target className="w-6 h-6 text-[#FFC857]" />;
    }
  };

  return (
    <div className="bg-[#111827] rounded-xl p-8 border border-[#1F2937] h-full relative overflow-hidden group">
      {/* Content */}
      <div className="relative z-10">
        {/* Header - Simplified */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gray-800 rounded-xl border border-gray-700">
              <Shield className="w-6 h-6 text-[#4F8CFF]" />
            </div>
            <div>
              <div className="text-sm text-gray-400 uppercase tracking-widest font-medium mb-1">Bias Engine</div>
              <div className="flex items-center space-x-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${marketStatus === 'OPEN' ? 'bg-[#00FF9F]/20 text-[#00FF9F]' : 'bg-gray-500/20 text-gray-400'
                  }`}>
                  {marketStatus || 'UNKNOWN'}
                </span>
                <span className="text-xs text-gray-500 font-mono">Real-time Analysis</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* Spot Price */}
            <div className="text-right">
              <div className="text-2xl font-black text-white">
                ₹{spotPrice?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="flex items-center justify-end space-x-2">
                {marketChange && (
                  <span className={`text-xs font-bold font-mono ${marketChange >= 0 ? 'text-[#00FF9F]' : 'text-[#FF4D4F]'}`}>
                    {marketChange >= 0 ? '+' : ''}{marketChange.toFixed(2)}
                  </span>
                )}
                {marketChangePercent && (
                  <span className={`text-xs font-bold font-mono px-1.5 py-0.5 rounded ${marketChangePercent >= 0 ? 'bg-[#00FF9F]/10 text-[#00FF9F]' : 'bg-[#FF4D4F]/10 text-[#FF4D4F]'}`}>
                    ({marketChangePercent.toFixed(2)}%)
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Global Bias Meter */}
        <div className="bg-black/20 border border-gray-800 rounded-xl p-6 mb-8 transition-all">
          <div className="flex items-center justify-between mb-6">
            <span className="text-xs text-gray-400 uppercase tracking-widest font-bold">Consensus Signal</span>
            <div className="flex items-center space-x-2 text-[#4F8CFF] bg-[#4F8CFF]/10 px-3 py-1 rounded-full text-xs font-bold border border-[#4F8CFF]/20">
              <Activity className="w-3 h-3" />
              <span>CONFIDENCE: {Math.round(bias.confidence)}%</span>
            </div>
          </div>

          <div className="flex items-center space-x-6">
            <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
              {getBiasIcon()}
            </div>
            <div className="flex-1">
              <div className="flex items-end justify-between mb-2">
                <span className={`text-3xl font-black uppercase tracking-tight ${biasColor}`}>
                  {biasLabel}
                </span>
                <span className="text-sm font-mono text-gray-500">STRENGTH: {bias.strength.toFixed(1)}x</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden border border-gray-700 p-[1px]">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${biasLabel.includes("BULL") ? "bg-[#00FF9F]" :
                    biasLabel.includes("BEAR") ? "bg-[#FF4D4F]" :
                      "bg-[#4F8CFF]"
                    }`}
                  style={{ width: `${bias.strength * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Tactical Modules */}
        <div className="grid grid-cols-2 gap-4">
          {/* Volatility Status */}
          <div className="bg-black/20 border border-gray-800 rounded-xl p-5 hover:border-[#4F8CFF]/30 transition-all">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-analytics-500/10 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-analytics-400" />
              </div>
              <span className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Volatility</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-bold text-white mb-0.5 capitalize">{volatility.current}</div>
                <div className="text-[10px] text-gray-500">Regime Status</div>
              </div>
              <div className={`text-xs font-mono font-bold px-2 py-1 rounded ${volatility.risk === 'high' ? 'text-[#FF4D4F] bg-[#FF4D4F]/10' : 'text-[#00FF9F] bg-[#00FF9F]/10'
                }`}>
                RISK: {volatility.risk.toUpperCase()}
              </div>
            </div>
          </div>

          {/* Flow Direction */}
          <div className="bg-black/20 border border-gray-800 rounded-xl p-5 hover:border-[#4F8CFF]/30 transition-all">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-orange-500/10 rounded-lg">
                <Zap className="w-4 h-4 text-orange-400" />
              </div>
              <span className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Flow Dynamics</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-bold text-white mb-0.5 capitalize">{liquidity.flow_direction}</div>
                <div className="text-[10px] text-gray-500">Smart Capital</div>
              </div>
              <div className="flex items-center space-x-1">
                <div className={`w-1.5 h-1.5 rounded-full animate-ping ${liquidity.flow_direction === 'inflow' ? 'bg-[#00FF9F]' : 'bg-[#FF4D4F]'
                  }`} />
                <span className="text-[10px] text-gray-400 font-mono">ACTIVE</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});
