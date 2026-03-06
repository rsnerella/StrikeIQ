import React, { memo } from 'react';
import { Brain, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

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
  const interpretation = intelligence?.interpretation ?? {
    narrative: null,
    risk_context: null,
    positioning_context: null,
    contradiction_flags: [],
    confidence_tone: 'cautious',
    interpreted_at: undefined,
    fallback: true
  };

  const getConfidenceIcon = (tone: string) => {
    switch (tone) {
      case 'high':
        return <CheckCircle className="w-4 h-4 text-success-400" />;
      case 'medium':
        return <Brain className="w-4 h-4 text-warning-400" />;
      case 'cautious':
      default:
        return <AlertTriangle className="w-4 h-4 text-danger-400" />;
    }
  };

  const getConfidenceColor = (tone: string) => {
    switch (tone) {
      case 'high':
        return 'text-success-400 bg-success-500/20 border-success-500/30';
      case 'medium':
        return 'text-warning-400 bg-warning-500/20 border-warning-500/30';
      case 'cautious':
      default:
        return 'text-danger-400 bg-danger-500/20 border-danger-500/30';
    }
  };

  return (
    <div className="trading-panel">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Brain className="w-5 h-5 text-[#4F8CFF]" />
          <h3 className="text-lg font-semibold text-white">AI Interpretation</h3>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium ${getConfidenceColor(interpretation.confidence_tone)}`}>
          {getConfidenceIcon(interpretation.confidence_tone)}
          <span className="capitalize">{interpretation.confidence_tone}</span>
        </div>
      </div>

      <div className="space-y-6">
        {/* Narrative */}
        {(interpretation.narrative || interpretation.fallback) && (
          <div>
            <h4 className="text-sm font-medium text-white mb-2">Market Narrative</h4>
            <p className="text-sm text-gray-400 leading-relaxed font-medium">
              {interpretation.narrative || interpretation.fallback ? 'Market analysis in progress...' : 'N/A'}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Risk Context */}
          <div className="bg-white/5 rounded-xl p-4 border border-white/5">
            <h4 className="text-[10px] uppercase tracking-widest font-bold text-gray-500 mb-2">Risk Context</h4>
            <p className="text-sm text-white font-semibold">
              {interpretation.risk_context || 'N/A'}
            </p>
          </div>

          {/* Positioning Context */}
          <div className="bg-white/5 rounded-xl p-4 border border-white/5">
            <h4 className="text-[10px] uppercase tracking-widest font-bold text-gray-500 mb-2">Positioning</h4>
            <p className="text-sm text-white font-semibold">
              {interpretation.positioning_context || 'N/A'}
            </p>
          </div>
        </div>

        {/* Contradiction Flags */}
        <div className="bg-red-500/5 rounded-xl p-4 border border-red-500/10">
          <h4 className="text-xs font-bold text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-3 h-3" />
            Structural Anomalies
          </h4>
          <div className="space-y-2">
            {(interpretation.contradiction_flags && interpretation.contradiction_flags.length > 0) 
              ? interpretation.contradiction_flags.map((flag, index) => (
                  <div key={index} className="flex items-center gap-2 text-xs text-red-300">
                    <div className="w-1 h-1 bg-red-400 rounded-full" />
                    <span>{flag}</span>
                  </div>
                ))
              : <div className="text-xs text-gray-500">No structural anomalies detected</div>
            }
          </div>
        </div>

        <div className="text-[10px] text-gray-600 flex justify-between items-center pt-2">
          <span>Engine v2.1.0-Live</span>
          <span>Last Sync: {interpretation.interpreted_at ? new Date(interpretation.interpreted_at).toLocaleTimeString() : 'Current'}</span>
        </div>
      </div>
    </div>
  );
};

export default memo(AIInterpretationPanel);
