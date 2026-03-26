import React from 'react';
import { Activity, TrendingUp, AlertTriangle, Clock } from 'lucide-react';

interface RegimeDynamics {
  regime: string;
  confidence: number;
  stability_score: number;
  acceleration_index: number;
  transition_probability: number;
  regime_duration_minutes: number;
  interpretation: {
    stability_level: string;
    acceleration_trend: string;
    transition_risk: string;
  };
  alerts: Array<{
    type: string;
    severity: string;
    message: string;
  }>;
}

interface RegimeDynamicsPanelProps {
  dynamics: RegimeDynamics;
}

const RegimeDynamicsPanel: React.FC<RegimeDynamicsPanelProps> = ({ dynamics }) => {
  const getStabilityColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'very_stable':
        return 'text-green-400 bg-green-500/20 border-green-500/40';
      case 'stable':
        return 'text-green-300 bg-green-400/20 border-green-400/40';
      case 'moderately_stable':
        return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/40';
      case 'unstable':
        return 'text-red-400 bg-red-500/20 border-red-500/40';
      default:
        return 'text-gray-400 bg-gray-500/20 border-gray-500/40';
    }
  };

  const getAccelerationColor = (trend: string) => {
    switch (trend?.toLowerCase()) {
      case 'strengthening_rapidly':
        return 'text-green-400 bg-green-500/20';
      case 'strengthening':
        return 'text-green-300 bg-green-400/20';
      case 'stable':
        return 'text-gray-400 bg-gray-500/20';
      case 'weakening':
        return 'text-orange-400 bg-orange-500/20';
      case 'weakening_rapidly':
        return 'text-red-400 bg-red-500/20';
      default:
        return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getTransitionRiskColor = (risk: string) => {
    switch (risk?.toLowerCase()) {
      case 'high_risk':
        return 'text-red-400';
      case 'moderate_risk':
        return 'text-yellow-400';
      case 'low_risk':
        return 'text-green-400';
      default:
        return 'text-gray-400';
    }
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  // Simple sparkline data (would come from historical data)
  const sparklineData = Array.from({ length: 20 }, (_, i) => 
    Math.sin(i * 0.3) * 20 + dynamics.stability_score
  );

  return (
    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white">Regime Dynamics</h3>
        
        {/* Current Regime Badge */}
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <div className="px-3 py-1 bg-blue-500/20 border border-blue-500/40 rounded-full">
            <span className="text-blue-400 font-medium text-sm">
              {dynamics.regime?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Stability Score */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-300">Stability Score</h4>
            <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getStabilityColor(dynamics.interpretation.stability_level)}`}>
              {dynamics.interpretation.stability_level?.replace('_', ' ') || 'Unknown'}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-2xl font-bold text-white">
              {Math.round(dynamics.stability_score)}
            </div>
            
            {/* Mini Sparkline */}
            <div className="flex items-end space-x-0.5 h-8">
              {(sparklineData || []).map((value, index) => (
                <div
                  key={index}
                  className="w-1 bg-blue-400/30"
                  style={{ height: `${(value / 100) * 32}px` }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Acceleration Index */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-300">Acceleration Index</h4>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${getAccelerationColor(dynamics.interpretation.acceleration_trend)}`}>
              {dynamics.interpretation.acceleration_trend?.replace('_', ' ') || 'Unknown'}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className={`text-2xl font-bold ${getAccelerationColor(dynamics.interpretation.acceleration_trend)}`}>
              {dynamics.acceleration_index > 0 ? '+' : ''}{Math.round(dynamics.acceleration_index)}
            </div>
            
            {/* Acceleration Bar */}
            <div className="flex-1">
              <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden relative">
                <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-600 transform -translate-x-1/2" />
                <div 
                  className={`h-full transition-all duration-500 ${
                    dynamics.acceleration_index > 0 ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  style={{ 
                    width: `${Math.abs(dynamics.acceleration_index)}%`,
                    marginLeft: dynamics.acceleration_index >= 0 ? '50%' : `${50 - Math.abs(dynamics.acceleration_index)}%`
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Transition Probability */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-300">Transition Probability</h4>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </div>
          
          <div className="flex items-center space-x-3">
            <div className={`text-xl font-bold ${getTransitionRiskColor(dynamics.interpretation.transition_risk)}`}>
              {Math.round(dynamics.transition_probability)}%
            </div>
            
            <div className={`px-2 py-1 rounded text-xs font-medium ${
              dynamics.transition_probability >= 70 ? 'bg-red-500/20 text-red-400' :
              dynamics.transition_probability >= 40 ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-green-500/20 text-green-400'
            }`}>
              {dynamics.interpretation.transition_risk?.replace('_', ' ') || 'Unknown'}
            </div>
          </div>
        </div>

        {/* Time in Regime */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-300">Time in Regime</h4>
            <Clock className="w-4 h-4 text-gray-400" />
          </div>
          
          <div className="text-xl font-bold text-white">
            {formatDuration(dynamics.regime_duration_minutes)}
          </div>
          
          <div className="text-xs text-gray-400 mt-1">
            Since regime change
          </div>
        </div>
      </div>

      {/* Regime Alerts */}
      {dynamics.alerts && dynamics.alerts.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center">
            <AlertTriangle className="w-4 h-4 mr-2 text-yellow-400" />
            Regime Alerts
          </h4>
          
          <div className="space-y-2">
            {dynamics.alerts.slice(0, 3).map((alert, index) => (
              <div key={index} className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full" />
                  <div className="text-sm text-yellow-400 flex-1">
                    {alert.message}
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

export default RegimeDynamicsPanel;
