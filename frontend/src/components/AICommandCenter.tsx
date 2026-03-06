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

  const getRegimeColor = (regime: string) => {
    switch (regime?.toLowerCase()) {
      case 'bullish':
      case 'uptrend':
      case 'high_vol':
        return 'text-[#00FF9F] bg-[#00FF9F]/10 border-[#00FF9F]/30';
      case 'bearish':
      case 'downtrend':
      case 'low_vol':
        return 'text-[#FF4D4F] bg-[#FF4D4F]/10 border-[#FF4D4F]/30';
      default:
        return 'text-[#4F8CFF] bg-[#4F8CFF]/10 border-[#4F8CFF]/30';
    }
  };

  const getSignalIcon = (signal: string) => {
    switch (signal?.toUpperCase()) {
      case 'BULLISH':
        return <TrendingUp className="w-4 h-4" />;
      case 'BEARISH':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Target className="w-4 h-4" />;
    }
  };

  return (
    <div className="trading-panel space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="w-6 h-6 text-[#4F8CFF]" />
          <h2 className="text-xl font-bold text-white">AI Command Center</h2>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium ${getRegimeColor(safeIntelligence?.regime?.market_regime)}`}>
          {getSignalIcon(safeIntelligence?.regime?.market_regime)}
          <span className="capitalize">{safeIntelligence?.regime?.market_regime || 'NEUTRAL'}</span>
        </div>
      </div>

      {/* Market Regime Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Market Regime</span>
          </div>
          <div className="text-lg font-bold text-white capitalize">
            {intelligence?.regime?.market_regime || 'NEUTRAL'}
          </div>
          <div className="text-xs text-gray-400">
            Confidence: {intelligence?.regime?.confidence?.toFixed(1) || '0.0'}%
          </div>
        </div>

        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Volatility Regime</span>
          </div>
          <div className="text-lg font-bold text-white capitalize">
            {intelligence?.regime?.volatility_regime || 'NORMAL'}
          </div>
          <div className="text-xs text-gray-400">
            Expected move: ±{intelligence?.probability?.expected_move?.toFixed(2) || '0.00'}
          </div>
        </div>

        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Trend Regime</span>
          </div>
          <div className="text-lg font-bold text-white capitalize">
            {intelligence?.regime?.trend_regime || 'SIDEWAYS'}
          </div>
          <div className="text-xs text-gray-400">
            Bias strength: {(biasData.strength * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Smart Money & Gamma Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-3">
            <Eye className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Smart Money Bias</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Signal:</span>
              <span className={`text-sm font-medium capitalize ${biasData.label?.toUpperCase() === 'BULLISH' ? 'text-[#00FF9F]' : biasData.label?.toUpperCase() === 'BEARISH' ? 'text-[#FF4D4F]' : 'text-[#4F8CFF]'}`}>
                {biasData.label || 'NEUTRAL'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Confidence:</span>
              <span className="text-sm font-medium text-white">
                {biasData.confidence?.toFixed(1) || '0.0'}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Direction:</span>
              <span className="text-sm font-medium capitalize text-white">
                {biasData.direction || 'NONE'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Dealer Gamma</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Net Gamma:</span>
              <span className={`text-sm font-medium ${intelligence?.gamma?.net_gamma > 0 ? 'text-[#00FF9F]' : 'text-[#FF4D4F]'}`}>
                {intelligence?.gamma?.net_gamma?.toFixed(2) || '0.00'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Regime:</span>
              <span className="text-sm font-medium capitalize text-white">
                {intelligence?.gamma?.dealer_gamma || 'NEUTRAL'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Flip Level:</span>
              <span className="text-sm font-medium text-white">
                {intelligence?.gamma?.gamma_flip?.toLocaleString('en-IN') || 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Signals Section */}
      <div className="bg-black/30 rounded-lg p-4 border border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-[#4F8CFF]" />
          <span className="text-sm font-medium text-gray-300">Risk Signals</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className={`text-center p-3 rounded-lg border ${intelligence?.signals?.stoploss_hunt ? 'bg-[#FF4D4F]/10 border-[#FF4D4F]/30' : 'bg-black/50 border-white/10'}`}>
            <AlertTriangle className={`w-5 h-5 mx-auto mb-1 ${intelligence?.signals?.stoploss_hunt ? 'text-[#FF4D4F]' : 'text-gray-500'}`} />
            <div className="text-xs font-medium text-white">Stoploss Hunt</div>
            <div className={`text-xs ${intelligence?.signals?.stoploss_hunt ? 'text-[#FF4D4F]' : 'text-gray-500'}`}>
              {intelligence?.signals?.stoploss_hunt ? 'ACTIVE' : 'CLEAR'}
            </div>
          </div>

          <div className={`text-center p-3 rounded-lg border ${intelligence?.signals?.trap_detection ? 'bg-[#FFC857]/10 border-[#FFC857]/30' : 'bg-black/50 border-white/10'}`}>
            <Target className={`w-5 h-5 mx-auto mb-1 ${intelligence?.signals?.trap_detection ? 'text-[#FFC857]' : 'text-gray-500'}`} />
            <div className="text-xs font-medium text-white">Trap Detection</div>
            <div className={`text-xs ${intelligence?.signals?.trap_detection ? 'text-[#FFC857]' : 'text-gray-500'}`}>
              {intelligence?.signals?.trap_detection ? 'DETECTED' : 'CLEAR'}
            </div>
          </div>

          <div className={`text-center p-3 rounded-lg border ${intelligence?.signals?.liquidity_event ? 'bg-[#4F8CFF]/10 border-[#4F8CFF]/30' : 'bg-black/50 border-white/10'}`}>
            <Activity className={`w-5 h-5 mx-auto mb-1 ${intelligence?.signals?.liquidity_event ? 'text-[#4F8CFF]' : 'text-gray-500'}`} />
            <div className="text-xs font-medium text-white">Liquidity Event</div>
            <div className={`text-xs ${intelligence?.signals?.liquidity_event ? 'text-[#4F8CFF]' : 'text-gray-500'}`}>
              {intelligence?.signals?.liquidity_event ? 'ACTIVE' : 'NORMAL'}
            </div>
          </div>

          <div className={`text-center p-3 rounded-lg border ${intelligence?.signals?.gamma_squeeze ? 'bg-[#00FF9F]/10 border-[#00FF9F]/30' : 'bg-black/50 border-white/10'}`}>
            <Zap className={`w-5 h-5 mx-auto mb-1 ${intelligence?.signals?.gamma_squeeze ? 'text-[#00FF9F]' : 'text-gray-500'}`} />
            <div className="text-xs font-medium text-white">Gamma Squeeze</div>
            <div className={`text-xs ${intelligence?.signals?.gamma_squeeze ? 'text-[#00FF9F]' : 'text-gray-500'}`}>
              {intelligence?.signals?.gamma_squeeze ? 'SQUEEZE' : 'NORMAL'}
            </div>
          </div>
        </div>
      </div>

      {/* Expected Move & Probability Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Expected Move Range</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">1SD Range:</span>
              <span className="text-sm font-medium text-white">
                {intelligence?.probability?.lower_1sd?.toLocaleString('en-IN')} - {intelligence?.probability?.upper_1sd?.toLocaleString('en-IN')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">2SD Range:</span>
              <span className="text-sm font-medium text-white">
                {intelligence?.probability?.lower_2sd?.toLocaleString('en-IN')} - {intelligence?.probability?.upper_2sd?.toLocaleString('en-IN')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Volatility State:</span>
              <span className={`text-sm font-medium capitalize ${
                intelligence?.probability?.volatility_state === 'overpriced' ? 'text-[#FF4D4F]' :
                intelligence?.probability?.volatility_state === 'underpriced' ? 'text-[#00FF9F]' :
                'text-[#4F8CFF]'
              }`}>
                {intelligence?.probability?.volatility_state || 'NEUTRAL'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">Probability Matrix</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Range Hold:</span>
              <span className="text-sm font-medium text-white">
                {intelligence?.probability?.range_hold_probability?.toFixed(1) || '0.0'}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Breach Risk:</span>
              <span className="text-sm font-medium text-white">
                {intelligence?.probability?.breach_probability?.toFixed(1) || '0.0'}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Expected Move:</span>
              <span className="text-sm font-medium text-white">
                ±{intelligence?.probability?.expected_move?.toFixed(2) || '0.00'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Trade Suggestion */}
      {intelligence?.trade_suggestion && (
        <div className="trade-signal-card" style={{
          background: 'rgba(0,150,255,0.06)',
          border: '1px solid rgba(0,150,255,0.25)',
          borderRadius: '12px',
          padding: '16px'
        }}>
          <div className="flex items-center gap-2 mb-3">
            <ArrowUpRight className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">AI Trade Suggestion</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <div className="text-xs text-gray-400 mb-1">Strategy</div>
              <div className="text-sm font-medium text-white capitalize">
                {intelligence.trade_suggestion.strategy}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Strike</div>
              <div className="text-sm font-medium text-white">
                {intelligence.trade_suggestion.option}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Entry</div>
              <div className="text-sm font-medium text-white">
                {intelligence.trade_suggestion.entry?.toLocaleString('en-IN')}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Target</div>
              <div className="text-sm font-medium text-white">
                {intelligence.trade_suggestion.target?.toLocaleString('en-IN')}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Stoploss</div>
              <div className="text-sm font-medium text-white">
                {intelligence.trade_suggestion.stoploss?.toLocaleString('en-IN')}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Confidence</div>
              <div className="text-sm font-medium text-white">
                {intelligence.trade_suggestion.confidence?.toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Risk/Reward</div>
              <div className="text-sm font-medium text-white">
                1:{intelligence.trade_suggestion.risk_reward?.toFixed(1)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Reasoning */}
      {intelligence?.reasoning && (
        <div className="bg-black/30 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-2 mb-3">
            <Info className="w-4 h-4 text-[#4F8CFF]" />
            <span className="text-sm font-medium text-gray-300">AI Reasoning</span>
          </div>
          <div className="text-sm text-gray-300 leading-relaxed">
            {intelligence.reasoning}
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(AICommandCenter);
