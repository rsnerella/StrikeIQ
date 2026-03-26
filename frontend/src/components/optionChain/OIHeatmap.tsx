"use client";

import React, { memo, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useShallow } from "zustand/shallow";
import { Calendar, Info } from 'lucide-react';
import { useWSStore } from '../../core/ws/wsStore';
import { useOptionChainStore } from '../../core/ws/optionChainStore';
import { useExpirySelector } from '../../hooks/useExpirySelector';
import { SectionLabel } from '../dashboard/StatCards';
import { PremiumDropdown } from '../ui/PremiumDropdown';
import SpotIndicator from './SpotIndicator';

interface OIData {
  strike: number;
  oi: number;
  change: number;
  ltp: number;
  volume: number;
  iv: number;
  put_oi: number;
  put_change: number;
  put_ltp: number;
  put_volume: number;
  put_iv: number;
}

interface OIHeatmapProps {
  symbol: string;
}

const OIHeatmap: React.FC<OIHeatmapProps> = ({ symbol }) => {
  const {
    expiryList,
    selectedExpiry,
    loadingExpiries,
    handleExpiryChange,
  } = useExpirySelector();

  const [oiData, setOiData] = useState<OIData[]>([]);
  const [spotPrice, setSpotPrice] = useState<number | null>(null);
  
  // Row height management for the spot indicator
  const [rowHeight, setRowHeight] = useState<number>(42); // Default estimate
  const rowMeasurementRef = useRef<HTMLDivElement>(null);

  const { 
    heatmapStoreCalls, 
    heatmapStorePuts, 
    heatmapStoreSpot, 
    heatmapStoreConnected, 
    heatmapStoreAtm 
  } = useWSStore(
    useShallow(state => ({
      heatmapStoreCalls: state.calls,
      heatmapStorePuts: state.puts,
      heatmapStoreSpot: state.spot,
      heatmapStoreConnected: state.connected,
      heatmapStoreAtm: state.atmStrike
    }))
  );
  
  const actualLiveData = useMemo(() => {
    const callsArray = Object.entries(heatmapStoreCalls || {}).map(([strike, data]) => ({
      strike: parseInt(strike),
      ...data
    }));
    
    const putsArray = Object.entries(heatmapStorePuts || {}).map(([strike, data]) => ({
      strike: parseInt(strike),
      ...data
    }));
    
    return { 
      callsData: callsArray, 
      putsData: putsArray, 
      spot_price: heatmapStoreSpot,
      atm_strike: heatmapStoreAtm
    };
  }, [heatmapStoreCalls, heatmapStorePuts, heatmapStoreSpot, heatmapStoreAtm]);

  const tableRef = useRef<HTMLDivElement>(null);
  const atmRowRef = useRef<HTMLDivElement>(null);
  const componentRef = useRef<HTMLDivElement>(null); // For visibility detection
  const hasScrolledRef = useRef<boolean>(false);
  const scrollLockedRef = useRef<boolean>(false); // To prevent infinite scroll fighting

  // Measure row height on mount/update
  useEffect(() => {
    if (rowMeasurementRef.current) {
      setRowHeight(rowMeasurementRef.current.offsetHeight);
    }
  }, [oiData]);

  // ── MAGNETIC CENTERING LOGIC ──────────────────────────────
  const centerATM = useCallback((behavior: ScrollBehavior = 'smooth') => {
    if (atmRowRef.current && tableRef.current) {
        const container = tableRef.current;
        const row = atmRowRef.current;
        const scrollPosition = row.offsetTop - (container.offsetHeight / 2) + (row.offsetHeight / 2);
        container.scrollTo({ top: scrollPosition, behavior });
    }
  }, []);

  // Center on visibility (IntersectionObserver)
  useEffect(() => {
    if (!componentRef.current) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
            // Magnetic snap when user visits the component
            centerATM('smooth');
        }
      });
    }, { threshold: 0.2 }); // Trigger when 20% of component is visible

    observer.observe(componentRef.current);
    return () => observer.disconnect();
  }, [centerATM]);

  // Handle initial auto-scroll to ATM on data load
  useEffect(() => {
    if (oiData.length > 0 && !hasScrolledRef.current) {
        centerATM('auto');
        hasScrolledRef.current = true;
    }
  }, [oiData, centerATM]);

  // Reset scroll lock on symbol change
  useEffect(() => {
    hasScrolledRef.current = false;
  }, [symbol]);

  // Process live data from WebSocket
  useEffect(() => {
    if (actualLiveData && actualLiveData.callsData && Array.isArray(actualLiveData.callsData)) {
      setSpotPrice(actualLiveData.spot_price);

      const strikeMap: { [key: number]: any } = {};

      actualLiveData.callsData.forEach((call: any) => {
        if (call.strike) {
          strikeMap[call.strike] = {
            call_oi: call.oi || 0,
            put_oi: 0,
            call_ltp: call.ltp || 0,
            put_ltp: 0,
            call_volume: call.volume || 0,
            put_volume: 0,
            call_change: call.oi_change || 0,
            put_change: 0
          };
        }
      });

      actualLiveData.putsData.forEach((put: any) => {
        if (put.strike) {
          if (strikeMap[put.strike]) {
            strikeMap[put.strike].put_oi = put.oi || 0;
            strikeMap[put.strike].put_ltp = put.ltp || 0;
            strikeMap[put.strike].put_volume = put.volume || 0;
            strikeMap[put.strike].put_change = put.oi_change || 0;
          } else {
            strikeMap[put.strike] = {
              call_oi: 0,
              put_oi: put.oi || 0,
              call_ltp: 0,
              put_ltp: put.ltp || 0,
              call_volume: 0,
              put_volume: put.volume || 0,
              call_change: 0,
              put_change: put.oi_change || 0
            };
          }
        }
      });

      const transformedData = Object.entries(strikeMap).map(([strike, data]) => ({
        strike: parseInt(strike),
        oi: data.call_oi,
        change: data.call_change,
        ltp: data.call_ltp,
        volume: data.call_volume,
        iv: 0,
        put_oi: data.put_oi,
        put_change: data.put_change,
        put_ltp: data.put_ltp,
        put_volume: data.put_volume,
        put_iv: 0,
      }));

      transformedData.sort((a, b) => a.strike - b.strike);

      // Show roughly 50 strikes centered around ATM
      const atm = actualLiveData.atm_strike || spotPrice || 0;
      const filteredData = transformedData.filter(row => {
        const diff = Math.abs(row.strike - atm);
        return diff <= 1250; // Wider range if needed, user mentioned 50+
      });

      setOiData(filteredData);
    }
  }, [actualLiveData, spotPrice]);

  const maxCallOI = Math.max(...(oiData || []).map(r => r.oi), 1);
  const maxPutOI = Math.max(...(oiData || []).map(r => r.put_oi), 1);
  
  const strikeList = useMemo(() => (oiData || []).map(d => d.strike), [oiData]);

  return (
    <div ref={componentRef} className="w-full relative">
      {/* Header section matches Premium styling */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 px-1">
        <div className="flex flex-col gap-1">
          <SectionLabel>Option Chain Architecture</SectionLabel>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Live Heatmap Visualization</span>
            <div className={`w-1.5 h-1.5 rounded-full ${heatmapStoreConnected ? 'bg-[#00E5FF] animate-pulse shadow-[0_0_8px_#00E5FF]' : 'bg-slate-700'}`} />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <PremiumDropdown
            value={selectedExpiry || ''}
            onChange={handleExpiryChange}
            options={expiryList}
            loading={loadingExpiries}
            placeholder="Expiry"
            minWidth={156}
            icon={<Calendar size={12} />}
          />
          
          <div className="hidden sm:flex items-center gap-4 px-4 py-2 bg-white/[0.02] border border-white/5 rounded-xl">
             <div className="flex items-center gap-1.5 cursor-help group/info">
               <Info size={10} className="text-slate-600 group-hover/info:text-cyan-400" />
               <span className="text-[9px] font-bold font-mono text-slate-500 uppercase">Interactive Hub</span>
             </div>
          </div>
        </div>
      </div>

      {/* Main Heatmap Container */}
      <div className="relative rounded-2xl overflow-hidden border border-[rgba(0,229,255,0.15)] bg-[rgba(6,9,18,0.9)] backdrop-blur-[20px] shadow-2xl">
        
        {/* Sticky Headers */}
        <div className="sticky top-0 z-50 bg-[#090e1a]/95 backdrop-blur-xl border-b border-white/10">
          <div className="grid grid-cols-7 py-3">
            <div className="col-span-3 text-center border-r border-white/5">
              <span className="text-[10px] font-bold font-mono tracking-[0.3em] text-[#FF3131] uppercase">Call Dynamics</span>
            </div>
            <div className="col-span-1 text-center">
              <span className="text-[10px] font-bold font-mono tracking-[0.3em] text-cyan-400 uppercase">ATM</span>
            </div>
            <div className="col-span-3 text-center border-l border-white/5">
              <span className="text-[10px] font-bold font-mono tracking-[0.3em] text-[#00FF9D] uppercase">Put Dynamics</span>
            </div>
          </div>

          <div className="grid grid-cols-7 py-2.5 border-t border-white/[0.03] bg-white/[0.01]">
            <div className="text-right pr-6 text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">OI Units</div>
            <div className="text-center text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Chg</div>
            <div className="text-center text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest border-r border-white/5">LTP</div>
            <div className="text-center text-[9px] font-bold font-mono text-cyan-400 uppercase tracking-widest">Strike</div>
            <div className="text-center text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest border-l border-white/5">LTP</div>
            <div className="text-center text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Chg</div>
            <div className="text-left pl-6 text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">OI Units</div>
          </div>
        </div>

        {/* Scrollable Rows Container */}
        <div 
          ref={tableRef} 
          className="overflow-y-auto custom-scrollbar relative" 
          style={{ maxHeight: '420px' }}
        >
          <div className="flex flex-col relative w-full h-full min-h-full">
            
            {/* Real-time Spot Indicator Overlay */}
            {spotPrice && oiData.length > 0 && (
                <SpotIndicator 
                    spotPrice={spotPrice} 
                    strikes={strikeList} 
                    rowHeight={rowHeight}
                />
            )}

            {(oiData || []).map((row, index) => {
              const checkSpot = actualLiveData?.atm_strike || spotPrice || 0;
              const isATM = Math.abs(row.strike - checkSpot) <= 1;
              const callIntensity = row.oi / maxCallOI;
              const putIntensity = row.put_oi / maxPutOI;

              // ── PROXIMITY CALCULATIONS ──────────────────────────
              const spotDist = spotPrice ? Math.abs(row.strike - spotPrice) : 999;
              const strikeInterval = 50; 
              const proximityEffect = spotPrice ? Math.max(0, 1 - (spotDist / (strikeInterval * 1.5))) : 0;
              const isMagnetic = spotDist < 5;

              return (
                <div 
                  key={row.strike} 
                  ref={isATM ? atmRowRef : (index === 0 ? rowMeasurementRef : null)} 
                  className={`grid grid-cols-7 py-2.5 border-b border-white/[0.02] transition-all duration-500 relative group/row ${
                    isATM ? 'bg-cyan-500/[0.05] border-y border-cyan-500/20 z-20' : 'hover:bg-white/[0.02]'
                  }`}
                  style={{
                    backgroundColor: proximityEffect > 0 ? `rgba(0, 229, 255, ${proximityEffect * 0.04})` : undefined
                  }}
                >
                  {/* Intensity Gradient Bars (Premium Neon Style) */}
                  <div className="absolute right-[57.14%] top-[2px] bottom-[2px] pointer-events-none transition-all duration-700" style={{ width: `${callIntensity * 40}%` }}>
                    <div className="h-full bg-gradient-to-l from-[#FF3131]/25 to-transparent border-r border-[#FF3131]/50 shadow-[-4px_0_12px_rgba(255,49,49,0.2)]" />
                  </div>
                  
                  <div className="absolute left-[57.14%] top-[2px] bottom-[2px] pointer-events-none transition-all duration-700" style={{ width: `${putIntensity * 40}%` }}>
                    <div className="h-full bg-gradient-to-r from-[#00FF9D]/25 to-transparent border-l border-[#00FF9D]/50 shadow-[4px_0_12px_rgba(0,255,157,0.2)]" />
                  </div>

                  {/* Row Values */}
                  <div className="text-right pr-6 text-[12px] font-bold font-mono tabular-nums text-rose-100/90 relative z-10 transition-colors group-hover/row:text-white">
                    {row.oi > 0 ? row.oi.toLocaleString() : '—'}
                  </div>
                  <div className={`text-center text-[11px] font-mono tabular-nums transition-colors ${row.change > 0 ? 'text-[#00FF9D]' : (row.change < 0 ? 'text-[#FF3131]/60' : 'text-slate-600')}`}>
                    {row.change !== 0 ? (row.change > 0 ? `+${row.change}` : row.change) : '—'}
                  </div>
                  <div className={`text-center text-[11px] font-bold font-mono text-slate-400 tabular-nums border-r border-white/5 transition-colors ${proximityEffect > 0.6 ? 'text-white' : ''}`}>
                    {row.ltp > 0 ? row.ltp.toFixed(1) : '—'}
                  </div>
                  
                  {/* Global Strike Index (Institutional Sync) */}
                  <div className={`text-center text-[13px] font-black font-mono tabular-nums tracking-tighter transition-all duration-500 relative z-30 ${
                    isATM ? 'text-cyan-400 scale-110' : 
                    (proximityEffect > 0.4 ? 'text-cyan-200' : 'text-slate-300 group-hover/row:text-white')
                  }`}>
                    {row.strike}
                    {isMagnetic && (
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full border border-cyan-500/30 animate-ping pointer-events-none" />
                    )}
                  </div>
                  
                  <div className={`text-center text-[11px] font-bold font-mono text-slate-400 tabular-nums border-l border-white/5 transition-colors ${proximityEffect > 0.6 ? 'text-white' : ''}`}>
                    {row.put_ltp > 0 ? row.put_ltp.toFixed(1) : '—'}
                  </div>
                  <div className={`text-center text-[11px] font-mono tabular-nums transition-colors ${row.put_change > 0 ? 'text-[#00FF9D]' : (row.put_change < 0 ? 'text-[#FF3131]/60' : 'text-slate-600')}`}>
                    {row.put_change !== 0 ? (row.put_change > 0 ? `+${row.put_change}` : row.put_change) : '—'}
                  </div>
                  
                  <div className="text-left pl-6 text-[12px] font-bold font-mono tabular-nums text-emerald-100/90 relative z-10 transition-colors group-hover/row:text-white">
                    {row.put_oi > 0 ? row.put_oi.toLocaleString() : '—'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer / Legend */}
      <div className="mt-6 flex items-center justify-between px-2">
        <div className="flex gap-8">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-[#FF3131]/20 border border-[#FF3131]/40 shadow-[0_0_8px_rgba(255,49,49,0.1)]" />
            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Writer Trap (CE)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-[#00FF9D]/20 border border-[#00FF9D]/40 shadow-[0_0_8px_rgba(0,255,157,0.1)]" />
            <span className="text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest">Writer Support (PE)</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-slate-700">
           <span className="text-[9px] font-black font-mono uppercase tracking-[0.25em]">StrikeIQ Core v5.1</span>
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar { width: 5px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(0,229,255,0.2); }
      `}</style>
    </div>
  );
};

export default memo(OIHeatmap);
