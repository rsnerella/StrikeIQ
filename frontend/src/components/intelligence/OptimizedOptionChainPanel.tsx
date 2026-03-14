import React, { memo, useMemo, useCallback } from 'react';
import { BarChart3, TrendingUp, TrendingDown, Target, Shield } from 'lucide-react';
import { OptionChainData } from '../../types/dashboard';

interface OptimizedOptionChainPanelProps {
  optionChainData: OptionChainData;
}

// Memoized sub-components to prevent re-renders
const PCRSummary = memo(({ pcr_summary }: { pcr_summary: any }) => {
  const getPCRColor = useCallback((signal: string) => {
    switch (signal?.toLowerCase()) {
      case 'bullish': return 'text-[#00FF9F] bg-[#00FF9F]/10 border-[#00FF9F]/30';
      case 'bearish': return 'text-[#FF4D4F] bg-[#FF4D4F]/10 border-[#FF4D4F]/30';
      default: return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  }, []);

  if (!pcr_summary) return null;

  return (
    <div className="mb-6">
      <div className={`rounded-xl p-4 border ${getPCRColor(pcr_summary.signal)}`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold uppercase tracking-wider">Put-Call Ratio</span>
          <div className="flex items-center space-x-2">
            {pcr_summary.signal === 'bullish' && <TrendingUp className="w-4 h-4" />}
            {pcr_summary.signal === 'bearish' && <TrendingDown className="w-4 h-4" />}
            <span className="text-xs font-black uppercase tracking-wider">
              {pcr_summary.signal}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">PCR Value</div>
            <div className="text-xl font-black">
            {typeof pcr_summary.put_call_ratio === 'number' && pcr_summary.put_call_ratio > 0
                ? pcr_summary.put_call_ratio.toFixed(2)
                : <span className="text-gray-600">—</span>
            }
          </div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Context</div>
            <div className="text-xs text-gray-400 font-medium">{pcr_summary.interpretation}</div>
          </div>
        </div>
      </div>
    </div>
  );
});

PCRSummary.displayName = 'PCRSummary';

const KeyLevels = memo(({ key_levels }: { key_levels: any }) => {
  if (!key_levels) return null;

  return (
    <div className="mb-6">
      <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Support & Resistance</h4>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-black/20 rounded-xl p-4 border border-gray-800">
          <div className="flex items-center space-x-2 mb-3">
            <Target className="w-4 h-4 text-[#FF4D4F]" />
            <span className="text-[10px] font-bold text-[#FF4D4F] uppercase tracking-wider">Resistance</span>
          </div>
          <div className="space-y-2">
            {key_levels.resistance.map((level: string) => (
              <div key={`resistance-${level}`} className="flex items-center justify-between text-xs font-mono font-bold">
                <span className="text-gray-300">{level}</span>
                <span className="text-[#FF4D4F]">R</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-black/20 rounded-xl p-4 border border-gray-800">
          <div className="flex items-center space-x-2 mb-3">
            <Shield className="w-4 h-4 text-[#00FF9F]" />
            <span className="text-[10px] font-bold text-[#00FF9F] uppercase tracking-wider">Support</span>
          </div>
          <div className="space-y-2">
            {key_levels.support.map((level: string) => (
              <div key={`support-${level}`} className="flex items-center justify-between text-xs font-mono font-bold">
                <span className="text-gray-300">{level}</span>
                <span className="text-[#00FF9F]">S</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
});

KeyLevels.displayName = 'KeyLevels';

const TopStrikes = memo(({ top_strikes }: { top_strikes: any[] }) => {
  const getConcentrationBarColor = useCallback((concentration: number) => {
    if (concentration >= 80) return 'bg-[#FF4D4F]';
    if (concentration >= 60) return 'bg-[#FFC857]';
    return 'bg-[#4F8CFF]';
  }, []);

  if (!top_strikes || top_strikes.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">OI Concentration</h4>
      <div className="space-y-2">
        {top_strikes.slice(0, 3).map((strike) => (
          <div key={`strike-${strike.strike}`} className="bg-black/20 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-bold text-white font-mono">{strike.strike}</div>
              <div className="text-[10px] text-gray-500 font-mono font-bold">
                {strike.oi_concentration.toFixed(1)}% Weight
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-gray-800/50 py-2 rounded border border-gray-800">
                <div className="text-[8px] text-gray-500 uppercase font-bold">Calls</div>
                <div className="text-[10px] font-bold text-[#FF4D4F]">
              {strike.call_oi > 0 ? (strike.call_oi / 1000).toFixed(1) + 'k' : '—'}
            </div>
              </div>
              <div className="bg-gray-800/50 py-2 rounded border border-gray-800">
                <div className="text-[8px] text-gray-500 uppercase font-bold">Puts</div>
                <div className="text-[10px] font-bold text-[#00FF9F]">
                {strike.put_oi > 0 ? (strike.put_oi / 1000).toFixed(1) + 'k' : '—'}
              </div>
              </div>
              <div className="bg-gray-800/50 py-2 rounded border border-gray-800">
                <div className="text-[8px] text-gray-500 uppercase font-bold">Total</div>
                <div className="text-[10px] font-bold text-[#4F8CFF]">
                {strike.total_oi > 0 ? (strike.total_oi / 1000).toFixed(1) + 'k' : '—'}
              </div>
              </div>
            </div>

            <div className="mt-3">
              <div className="w-full bg-black/30 rounded-full h-1 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getConcentrationBarColor(strike.oi_concentration)}`}
                  style={{ width: `${strike.oi_concentration}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

TopStrikes.displayName = 'TopStrikes';

const OptimizedOptionChainPanel: React.FC<OptimizedOptionChainPanelProps> = memo(({ optionChainData }) => {
  // Memoized data extraction to prevent re-computation
  const { calls, puts, hasData } = useMemo(() => {
    const calls = optionChainData?.calls ?? [];
    const puts = optionChainData?.puts ?? [];
    const hasData = calls.length > 0 || puts.length > 0;
    
    return { calls, puts, hasData };
  }, [optionChainData]);

  // Memoized derived values
  const derivedValues = useMemo(() => {
    // Calculate derived strike values
    const totalOI = [...calls, ...puts].reduce((sum, item) => sum + (item.open_interest || 0), 0);
    const avgStrike = [...calls, ...puts].reduce((sum, item) => sum + (item.strike || 0), 0) / Math.max([...calls, ...puts].length, 1);
    
    return {
      totalOI,
      avgStrike,
      totalStrikes: calls.length + puts.length
    };
  }, [calls, puts]);

  // Early return for missing data
  if (!hasData) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 h-full flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-2 border-gray-700 border-t-gray-500 rounded-full animate-spin mb-4" />
        <p className="text-gray-500 font-mono text-xs tracking-wider">Aggregating Option Chain Intel...</p>
      </div>
    );
  }

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 transition-all">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <BarChart3 className="w-5 h-5 mr-3 text-[#4F8CFF]" />
          Option Chain
        </h3>
        <div className="text-xs text-gray-400">
          {derivedValues.totalStrikes} strikes • {derivedValues.totalOI.toLocaleString()} total OI
        </div>
      </div>

      {/* Memoized sub-components */}
      <PCRSummary pcr_summary={optionChainData?.pcr_summary} />
      <KeyLevels key_levels={optionChainData?.key_levels} />
      <TopStrikes top_strikes={optionChainData?.top_strikes || []} />
    </div>
  );
});

OptimizedOptionChainPanel.displayName = 'OptimizedOptionChainPanel';

export default OptimizedOptionChainPanel;
