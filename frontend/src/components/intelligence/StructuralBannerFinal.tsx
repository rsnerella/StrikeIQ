import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, Target, AlertTriangle } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';

interface StructuralBannerProps {
  regime: string;
  confidence: number;
  stability: number;
  acceleration: number;
}

const StructuralBanner: React.FC<StructuralBannerProps> = ({
  regime,
  confidence,
  stability,
  acceleration
}) => {
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentRegime, setCurrentRegime] = useState(regime);
  
  // Connect to global store for status indicators
  const connected = useWSStore(s => s.connected);
  const aiReady = useWSStore(s => s.aiReady);
  const symbol = useWSStore(s => s.symbol) || 'NIFTY';

  useEffect(() => {
    if (currentRegime !== regime) {
      setIsAnimating(true);
      setCurrentRegime(regime);
      setTimeout(() => setIsAnimating(false), 1000);
    }
  }, [regime, currentRegime]);

  const getRegimeConfig = (regimeType: string) => {
    switch (regimeType?.toLowerCase()) {
      case 'range':
        return {
          bg: 'bg-emerald-500/10 via-emerald-600/5 to-transparent',
          border: 'border-emerald-500/20',
          text: 'text-emerald-400',
          glow: 'shadow-emerald-500/5',
          icon: <Activity className="w-5 h-5 text-emerald-400" />
        };
      case 'trend':
        return {
          bg: 'bg-rose-500/10 via-rose-600/5 to-transparent',
          border: 'border-rose-500/20',
          text: 'text-rose-400',
          glow: 'shadow-rose-500/5',
          icon: <TrendingUp className="w-5 h-5 text-rose-400" />
        };
      case 'breakout':
        return {
          bg: 'bg-amber-500/10 via-amber-600/5 to-transparent',
          border: 'border-amber-500/20',
          text: 'text-amber-400',
          glow: 'shadow-amber-500/5',
          icon: <Target className="w-5 h-5 text-amber-400" />
        };
      case 'pin_risk':
        return {
          bg: 'bg-sky-500/10 via-sky-600/5 to-transparent',
          border: 'border-sky-500/20',
          text: 'text-sky-400',
          glow: 'shadow-sky-500/5',
          icon: <AlertTriangle className="w-5 h-5 text-sky-400" />
        };
      default:
        return {
          bg: 'bg-slate-500/10 via-slate-600/5 to-transparent',
          border: 'border-slate-500/20',
          text: 'text-slate-400',
          glow: 'shadow-slate-500/5',
          icon: <Activity className="w-5 h-5 text-slate-400" />
        };
    }
  };

  const getAccelerationColor = (value: number) => {
    if (value > 20) return 'text-emerald-400';
    if (value < -20) return 'text-rose-400';
    return 'text-slate-400';
  };

  const getStabilityColor = (value: number) => {
    if (value >= 80) return 'text-emerald-400';
    if (value >= 60) return 'text-amber-400';
    return 'text-rose-400';
  };

  const regimeColor = getRegimeConfig(currentRegime);

  return (
    <div className={`w-full p-[1px] rounded-2xl bg-white/5 ${isAnimating ? 'animate-pulse' : ''} shadow-lg border border-white/10`}>
        <div className={`w-full flex flex-col md:flex-row items-center justify-between p-5 rounded-[15px] backdrop-blur-3xl overflow-hidden relative ${regimeColor.bg}`}>
            {/* Left Cluster: Market ID and Connectivity */}
            <div className="flex items-center gap-6 relative z-10">
                <div className="flex flex-col">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-white/[0.03] border border-white/10">
                            {regimeColor.icon}
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-widest">Market Integrity</span>
                            <div className="flex items-center gap-2">
                                <h2 className="text-2xl font-black font-mono tracking-tight text-white uppercase">{currentRegime?.replace('_', ' ')}</h2>
                                <div className="px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-[9px] font-bold text-slate-400 uppercase tracking-widest">
                                    {symbol}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="h-10 w-[1px] bg-white/10 md:block hidden" />

                <div className="md:flex hidden items-center gap-6">
                    <div className="flex flex-col">
                        <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-widest mb-1">Stream</span>
                        <div className="flex items-center gap-2">
                            <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500'} animate-pulse`} />
                            <span className="text-xs font-bold font-mono text-white/80 uppercase">{connected ? "Live" : "OFF"}</span>
                        </div>
                    </div>
                    
                    <div className="flex flex-col">
                        <span className="text-[9px] font-black font-mono text-slate-500 uppercase tracking-widest mb-1">Neural</span>
                        <div className="flex items-center gap-2">
                            <div className={`w-1.5 h-1.5 rounded-full ${aiReady ? 'bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.5)]' : 'bg-amber-500'} animate-pulse`} />
                            <span className="text-xs font-bold font-mono text-white/80 uppercase">{aiReady ? "Ready" : "Warming"}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Cluster: Metrics */}
            <div className="flex items-center gap-10 relative z-10 md:mt-0 mt-4 justify-between w-full md:w-auto">
                <div className="flex flex-col items-center">
                    <span className="text-xl font-black font-mono text-white">{Math.round(confidence)}%</span>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Confidence</span>
                </div>
                
                <div className="h-8 w-[1px] bg-white/10" />

                <div className="flex flex-col items-center">
                    <span className={`text-xl font-black font-mono ${getStabilityColor(stability)}`}>{Math.round(stability)}%</span>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Stability</span>
                </div>

                <div className="h-8 w-[1px] bg-white/10" />

                <div className="flex flex-col items-center">
                    <span className={`text-xl font-black font-mono ${getAccelerationColor(acceleration)}`}>
                        {acceleration > 0 ? '+' : ''}{Math.round(acceleration)}
                    </span>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Velocity</span>
                </div>
            </div>
        </div>
    </div>
  );
};

export default StructuralBanner;
