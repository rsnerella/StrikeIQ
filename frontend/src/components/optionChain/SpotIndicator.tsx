"use client";

import React, { useMemo } from 'react';

interface SpotIndicatorProps {
  spotPrice: number;
  strikes: number[];
  rowHeight: number; // Height of each row in pixels
}

const SpotIndicator: React.FC<SpotIndicatorProps> = ({ spotPrice, strikes, rowHeight }) => {
  const result = useMemo(() => {
    if (!spotPrice || strikes.length < 2) return null;

    let lowerIdx = -1;
    for (let i = 0; i < strikes.length; i++) {
        if (strikes[i] <= spotPrice) {
            lowerIdx = i;
        } else {
            break;
        }
    }

    if (lowerIdx === -1) return null;
    if (lowerIdx === strikes.length - 1) return null;

    const lowerStrike = strikes[lowerIdx];
    const upperStrike = strikes[lowerIdx + 1];
    const interval = upperStrike - lowerStrike;
    const ratio = (spotPrice - lowerStrike) / interval;

    const top = (lowerIdx * rowHeight) + (rowHeight / 2) + (ratio * rowHeight);

    return { top, ratio, lowerStrike, upperStrike };
  }, [spotPrice, strikes, rowHeight]);

  if (!result) return null;

  return (
    <>
      {/* ── Spot Area Highlight (Pure Glow, No Line) ──────────────── */}
      <div 
        className="absolute left-0 right-0 z-10 pointer-events-none transition-all duration-300 ease-out flex items-center justify-center"
        style={{ 
          top: `${result.top - 30}px`,
          height: '60px',
          background: 'radial-gradient(ellipse at center, rgba(0, 229, 255, 0.12) 0%, transparent 75%)'
        }}
      >
        {/* Core Intensity Spot (Subtle center focus) */}
        <div className="w-full h-[20px] bg-gradient-to-r from-transparent via-cyan-400/[0.08] to-transparent" />
      </div>

      {/* ── Moving Spot Price Tag ─────────────────────────────────── */}
      <div 
        className="absolute left-0 right-0 z-40 pointer-events-none transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1)"
        style={{ top: `${result.top}px` }}
      >
        {/* Transparent "SPOT" Price Tag */}
        <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-[1px]">
          <div className="flex items-center">
            {/* Minimal Pulse marker */}
            <div className="w-1 h-1 rounded-full mr-2 bg-cyan-400/60 animate-pulse" />
            
            <div className="relative flex items-center bg-[#00E5FF]/20 border border-cyan-500/15 px-2 py-0.5 rounded-l-md backdrop-blur-md">
              <span className="text-[9px] font-black font-mono text-cyan-200/40 uppercase tracking-tighter mr-1.5 font-sans">SPOT</span>
              <span className="text-[12px] font-black font-mono text-white tabular-nums tracking-tighter">
                {spotPrice.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
              </span>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </>
  );
};

export default React.memo(SpotIndicator);
