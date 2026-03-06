import React, { memo } from 'react';
import { TrendingUp, TrendingDown, Activity, DollarSign, Target, Shield } from 'lucide-react';
import { SmartMoneyData } from '../../types/dashboard';

interface SmartMoneyPanelProps {
  smartMoneyData: SmartMoneyData;
}

const SmartMoneyPanel: React.FC<SmartMoneyPanelProps> = ({ smartMoneyData }) => {
  // Always render the component, use fallback data when smartMoneyData is missing

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
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 h-full transition-all">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <DollarSign className="w-5 h-5 mr-3 text-[#00FF9F]" />
          Smart Money
        </h3>

        {/* Net Flow Badge */}
        <div className={`px-3 py-1 rounded-full border flex items-center space-x-2 ${getFlowColor(smartMoneyData.net_smart_money_flow)}`}>
          {getFlowIcon(smartMoneyData.net_smart_money_flow)}
          <span className="text-[10px] font-black uppercase tracking-wider">
            {smartMoneyData.net_smart_money_flow}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 mb-6">
        {/* Call Writing */}
        <div className="col-span-6">
          <div className="bg-gray-800/50 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Call Writing</span>
              <Target className="w-4 h-4 text-red-400" />
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${smartMoneyData?.call_writing_detected ? 'bg-red-500' : 'bg-gray-600'}`}></div>
              <span className={`text-lg font-semibold ${smartMoneyData?.call_writing_detected ? 'text-red-400' : 'text-gray-500'}`}>
                {smartMoneyData?.call_writing_detected ? 'DETECTED' : 'NONE'}
              </span>
            </div>
            {smartMoneyData?.call_writing_detected && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                  <span>Strength</span>
                  <span>{(smartMoneyData?.call_writing_strength ?? 0).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${getStrengthBarColor(smartMoneyData?.call_writing_strength ?? 0)}`}
                    style={{ width: `${smartMoneyData?.call_writing_strength ?? 0}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Put Writing */}
        <div className="col-span-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Put Writing</span>
              <Shield className="w-4 h-4 text-[#00FF9F]" />
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${smartMoneyData?.put_writing_detected ? 'bg-[#00FF9F]' : 'bg-gray-700'}`}></div>
              <span className={`text-lg font-semibold ${smartMoneyData?.put_writing_detected ? 'text-[#00FF9F]' : 'text-gray-500'}`}>
                {smartMoneyData?.put_writing_detected ? 'DETECTED' : 'NONE'}
              </span>
            </div>
            {smartMoneyData?.put_writing_detected && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                  <span>Strength</span>
                  <span>{(smartMoneyData?.put_writing_strength ?? 0).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${getStrengthBarColor(smartMoneyData?.put_writing_strength ?? 0)}`}
                    style={{ width: `${smartMoneyData?.put_writing_strength ?? 0}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Buildup Activity */}
      <div className="grid grid-cols-12 gap-4 mb-6">
        <div className="col-span-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Long Buildup</span>
              <TrendingUp className="w-4 h-4 text-[#00FF9F]" />
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${smartMoneyData?.long_buildup_detected ? 'bg-[#00FF9F]' : 'bg-gray-700'}`}></div>
              <span className={`text-lg font-semibold ${smartMoneyData?.long_buildup_detected ? 'text-[#00FF9F]' : 'text-gray-500'}`}>
                {smartMoneyData?.long_buildup_detected ? 'ACTIVE' : 'NONE'}
              </span>
            </div>
          </div>
        </div>

        <div className="col-span-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Short Buildup</span>
              <TrendingDown className="w-4 h-4 text-[#FF4D4F]" />
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${smartMoneyData?.short_buildup_detected ? 'bg-[#FF4D4F]' : 'bg-gray-700'}`}></div>
              <span className={`text-lg font-semibold ${smartMoneyData?.short_buildup_detected ? 'text-[#FF4D4F]' : 'text-gray-500'}`}>
                {smartMoneyData?.short_buildup_detected ? 'ACTIVE' : 'NONE'}
              </span>
            </div>
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
                <span>{(smartMoneyData?.institutional_activity_score ?? 0).toFixed(1)}/100</span>
              </div>
              <div className="w-full bg-gray-900 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getStrengthBarColor(smartMoneyData?.institutional_activity_score ?? 0)}`}
                  style={{ width: `${smartMoneyData?.institutional_activity_score ?? 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Observations */}
      {smartMoneyData?.key_observations && smartMoneyData.key_observations.length > 0 && (
        <div className="mt-auto">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Observations</h4>
          <div className="space-y-2">
            {smartMoneyData.key_observations.map((observation, index) => (
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

export default memo(SmartMoneyPanel);
