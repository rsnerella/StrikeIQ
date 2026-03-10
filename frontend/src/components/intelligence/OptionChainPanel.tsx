import React, { memo } from 'react';
import { BarChart3, TrendingUp, TrendingDown, Target, Shield } from 'lucide-react';
import { OptionChainData } from '../../types/dashboard';

interface OptionChainPanelProps {
  optionChainData: OptionChainData;
}

const OptionChainPanel: React.FC<OptionChainPanelProps> = ({ optionChainData }) => {
  // Runtime guard for undefined data
  if (!optionChainData) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 h-full flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-2 border-gray-700 border-t-gray-500 rounded-full animate-spin mb-4" />
        <p className="text-gray-500 font-mono text-xs tracking-wider">Loading Option Chain...</p>
      </div>
    );
  }

  // Extract calls and puts from normalized optionChain structure
  const calls = optionChainData?.calls ?? [];
  const puts = optionChainData?.puts ?? [];
  
  // PERFORMANCE: Limit visible strikes to prevent rendering performance issues
  // Show only 20 strikes around ATM (10 above, 10 below)
  const totalStrikes = Math.max(calls.length, puts.length);
  const maxVisibleStrikes = 20;
  let visibleCalls = calls;
  let visiblePuts = puts;
  
  if (totalStrikes > maxVisibleStrikes) {
    // Find ATM strike (middle of the array)
    const atmIndex = Math.floor(totalStrikes / 2);
    const startIndex = Math.max(0, atmIndex - 10);
    const endIndex = Math.min(totalStrikes, atmIndex + 10);
    
    visibleCalls = calls.slice(startIndex, endIndex);
    visiblePuts = puts.slice(startIndex, endIndex);
    
    console.log(`PERFORMANCE: Limited strikes from ${totalStrikes} to ${visibleCalls.length} visible`);
  }
  
  console.log("Calls length:", visibleCalls.length);
  console.log("Puts length:", visiblePuts.length);
  console.log("VISIBLE STRIKES", visibleCalls.length + visiblePuts.length);
  console.log("FIRST CALL OBJECT:", visibleCalls[0]);
  console.log("FIRST PUT OBJECT:", visiblePuts[0]);

  // Handle missing data with skeleton (Phase 4)
  if (!optionChainData || (visibleCalls.length === 0 && visiblePuts.length === 0)) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 h-full flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-2 border-gray-700 border-t-gray-500 rounded-full animate-spin mb-4" />
        <p className="text-gray-500 font-mono text-xs tracking-wider">Aggregating Option Chain Intel...</p>
      </div>
    );
  }

  const getPCRColor = (signal: string) => {
    switch (signal?.toLowerCase()) {
      case 'bullish': return 'text-[#00FF9F] bg-[#00FF9F]/10 border-[#00FF9F]/30';
      case 'bearish': return 'text-[#FF4D4F] bg-[#FF4D4F]/10 border-[#FF4D4F]/30';
      default: return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  };

  const getConcentrationBarColor = (concentration: number) => {
    if (concentration >= 80) return 'bg-[#FF4D4F]';
    if (concentration >= 60) return 'bg-[#FFC857]';
    return 'bg-[#4F8CFF]';
  };

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 transition-all">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <BarChart3 className="w-5 h-5 mr-3 text-[#4F8CFF]" />
          Option Chain
        </h3>
      </div>

      {/* DEBUG: Temporary JSON dump */}
      <div className="mb-4 p-4 bg-black/50 rounded border border-gray-800">
        <h4 className="text-xs font-bold text-gray-500 mb-2">DEBUG - First Call Object:</h4>
        <pre className="text-xs text-gray-300 overflow-auto max-h-32">
          {JSON.stringify(visibleCalls[0], null, 2)}
        </pre>
      </div>

      {/* PCR Summary */}
      {optionChainData.pcr_summary && (
        <div className="mb-6">
          <div className={`rounded-xl p-4 border ${getPCRColor(optionChainData.pcr_summary.signal)}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider">Put-Call Ratio</span>
              <div className="flex items-center space-x-2">
                {optionChainData.pcr_summary.signal === 'bullish' && <TrendingUp className="w-4 h-4" />}
                {optionChainData.pcr_summary.signal === 'bearish' && <TrendingDown className="w-4 h-4" />}
                <span className="text-xs font-black uppercase tracking-wider">
                  {optionChainData.pcr_summary.signal}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">PCR Value</div>
                <div className="text-xl font-black">{optionChainData.pcr_summary.put_call_ratio.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Context</div>
                <div className="text-xs text-gray-400 font-medium">{optionChainData.pcr_summary.interpretation}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Key Levels */}
      {optionChainData.key_levels && (
        <div className="mb-6">
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Support & Resistance</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-black/20 rounded-xl p-4 border border-gray-800">
              <div className="flex items-center space-x-2 mb-3">
                <Target className="w-4 h-4 text-[#FF4D4F]" />
                <span className="text-[10px] font-bold text-[#FF4D4F] uppercase tracking-wider">Resistance</span>
              </div>
              <div className="space-y-2">
                {optionChainData.key_levels.resistance.map((level) => (
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
                {optionChainData.key_levels.support.map((level) => (
                  <div key={`support-${level}`} className="flex items-center justify-between text-xs font-mono font-bold">
                    <span className="text-gray-300">{level}</span>
                    <span className="text-[#00FF9F]">S</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Strikes */}
      {optionChainData.top_strikes && optionChainData.top_strikes.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">OI Concentration</h4>
          <div className="space-y-2">
            {optionChainData.top_strikes.slice(0, 3).map((strike) => (
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
                    <div className="text-[10px] font-bold text-[#FF4D4F]">{(strike.call_oi / 1000).toFixed(1)}k</div>
                  </div>
                  <div className="bg-gray-800/50 py-2 rounded border border-gray-800">
                    <div className="text-[8px] text-gray-500 uppercase font-bold">Puts</div>
                    <div className="text-[10px] font-bold text-[#00FF9F]">{(strike.put_oi / 1000).toFixed(1)}k</div>
                  </div>
                  <div className="bg-gray-800/50 py-2 rounded border border-gray-800">
                    <div className="text-[8px] text-gray-500 uppercase font-bold">Total</div>
                    <div className="text-[10px] font-bold text-[#4F8CFF]">{(strike.total_oi / 1000).toFixed(1)}k</div>
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
      )}
    </div>
  );
};

export default memo(OptionChainPanel);
