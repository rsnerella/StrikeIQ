import React, { memo } from 'react';
import { TrendingUp, TrendingDown, Activity, DollarSign, Target, Shield } from 'lucide-react';
import { SmartMoneyData } from '../../types/dashboard';

interface SmartMoneyPanelProps {
  smartMoneyData: SmartMoneyData;
}

const SmartMoneyPanel: React.FC<SmartMoneyPanelProps> = ({ smartMoneyData }) => {
  const safeData = smartMoneyData ?? {
    net_smart_money_flow: 'NEUTRAL',
    call_writing_detected: false,
    call_writing_strength: 0,
    put_writing_detected: false,
    put_writing_strength: 0,
    long_buildup_detected: false,
    short_buildup_detected: false,
    institutional_activity_score: 0,
    key_observations: []
  };

  const getFlowColor = (flow: string) => {
    switch (flow?.toLowerCase()) {
      case 'bullish': return 'text-[#00FF9F] bg-[#00FF9F]/10 border-[#00FF9F]/30';
      case 'bearish': return 'text-[#FF4D4F] bg-[#FF4D4F]/10 border-[#FF4D4F]/30';
      default: return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  };

  const getFlowIcon = (flow: string) => {
    switch (flow?.toLowerCase()) {
      case 'bullish': return <TrendingUp className="w-5 h-5" />;
      case 'bearish': return <TrendingDown className="w-5 h-5" />;
      default: return <Activity className="w-5 h-5" />;
    }
  };

  const getStrengthBarColor = (strength: number) => {
    if (strength >= 80) return 'bg-[#FF4D4F]';
    if (strength >= 60) return 'bg-[#FFC857]';
    return 'bg-[#4F8CFF]';
  };

  return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white flex items-center">
            <DollarSign className="w-5 h-5 mr-3 text-[#00FF9F]" />
            Smart Money
          </h3>

          {/* Net Flow Badge */}
          <div className={`px-3 py-1 rounded-full border flex items-center space-x-2 ${getFlowColor(safeData.net_smart_money_flow)}`}>
            {getFlowIcon(safeData.net_smart_money_flow)}
            <span className="text-[10px] font-black uppercase tracking-wider">
              {safeData.net_smart_money_flow}
            </span>
          </div>
        </div>

      {/* Call Writing & Put Writing */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Call Writing */}
        <div className="w-full bg-gray-800/50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Call Writing</span>
            <Target className="w-4 h-4 text-red-400" />
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${safeData?.call_writing_detected ? 'bg-red-500' : 'bg-gray-600'}`}></div>
            <span className={`text-lg font-semibold ${safeData?.call_writing_detected ? 'text-red-400' : 'text-gray-500'}`}>
              {safeData?.call_writing_detected ? 'DETECTED' : 'NONE'}
            </span>
          </div>
          {safeData?.call_writing_detected && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>Strength</span>
                <span>{(safeData?.call_writing_strength ?? 0).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getStrengthBarColor(safeData?.call_writing_strength ?? 0)}`}
                  style={{ width: `${safeData?.call_writing_strength ?? 0}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Put Writing */}
        <div className="w-full bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Put Writing</span>
            <Shield className="w-4 h-4 text-[#00FF9F]" />
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${safeData?.put_writing_detected ? 'bg-[#00FF9F]' : 'bg-gray-700'}`}></div>
            <span className={`text-lg font-semibold ${safeData?.put_writing_detected ? 'text-[#00FF9F]' : 'text-gray-500'}`}>
              {safeData?.put_writing_detected ? 'DETECTED' : 'NONE'}
            </span>
          </div>
          {safeData?.put_writing_detected && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>Strength</span>
                <span>{(safeData?.put_writing_strength ?? 0).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getStrengthBarColor(safeData?.put_writing_strength ?? 0)}`}
                  style={{ width: `${safeData?.put_writing_strength ?? 0}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Long Buildup & Short Buildup */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Long Buildup */}
        <div className="w-full bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Long Buildup</span>
            <TrendingUp className="w-4 h-4 text-[#00FF9F]" />
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${safeData?.long_buildup_detected ? 'bg-[#00FF9F]' : 'bg-gray-700'}`}></div>
            <span className={`text-lg font-semibold ${safeData?.long_buildup_detected ? 'text-[#00FF9F]' : 'text-gray-500'}`}>
              {safeData?.long_buildup_detected ? 'ACTIVE' : 'NONE'}
            </span>
          </div>
        </div>

        {/* Short Buildup */}
        <div className="w-full bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Short Buildup</span>
            <TrendingDown className="w-4 h-4 text-[#FF4D4F]" />
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${safeData?.short_buildup_detected ? 'bg-[#FF4D4F]' : 'bg-gray-700'}`}></div>
            <span className={`text-lg font-semibold ${safeData?.short_buildup_detected ? 'text-[#FF4D4F]' : 'text-gray-500'}`}>
              {safeData?.short_buildup_detected ? 'ACTIVE' : 'NONE'}
            </span>
          </div>
        </div>
      </div>

      {/* Institutional Activity Score */}
      <div className="mb-6">
        <div className="bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Activity Score</span>
            <Activity className="w-4 h-4 text-[#4F8CFF]" />
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>Activity Level</span>
                <span>{(safeData?.institutional_activity_score ?? 0).toFixed(1)}/100</span>
              </div>
              <div className="w-full bg-gray-900 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getStrengthBarColor(safeData?.institutional_activity_score ?? 0)}`}
                  style={{ width: `${safeData?.institutional_activity_score ?? 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Observations */}
      {safeData?.key_observations && safeData.key_observations.length > 0 && (
        <div className="mt-auto">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Observations</h4>
          <div className="space-y-2">
            {safeData.key_observations.map((observation, index) => (
              <div key={index} className="bg-black/20 rounded-lg px-3 py-2 text-xs text-gray-400 border border-gray-800">
                {observation}
              </div>
            ))}
          </div>
        </div>
      )}
      </div>
  );
};

export { SmartMoneyPanel };
export default memo(SmartMoneyPanel);
