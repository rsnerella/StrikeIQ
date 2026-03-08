import React, { memo, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { BarChart3, TrendingUp, TrendingDown } from 'lucide-react';
import api from '../lib/api';
import { useWSStore } from '../core/ws/wsStore';
import { useOptionChainStore } from '../core/ws/optionChainStore';
import { useDashboardData } from '../hooks/useDashboardData';
import { useExpirySelector } from '../hooks/useExpirySelector';
import { CARD } from './dashboard/DashboardTypes';
import { SectionLabel } from './dashboard/StatCards';
import { PremiumDropdown } from './ui/PremiumDropdown';
import { Calendar } from 'lucide-react';

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

  // Use expiry selector hook
  const {
    expiryList,
    selectedExpiry,
    loadingExpiries,
    expiryError,
    handleExpiryChange,
    optionChainConnected
  } = useExpirySelector();

  // Use global store data
  const { calls, puts, connected } = useDashboardData();

  const [oiData, setOiData] = useState<OIData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [spotPrice, setSpotPrice] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Read from Zustand stores for fallback
  const { liveData: wsLiveData, optionChainSnapshot, spot } = useWSStore();
  const { optionChainData } = useOptionChainStore();

  // Use structured data from global store, fallback to option chain store, then legacy data
  const actualLiveData = calls.length > 0 || puts.length > 0
    ? { calls, puts, spot }
    : optionChainData || wsLiveData || optionChainSnapshot;

  // 🔥 PCR FALLBACK CALCULATION (FRONTEND-ONLY FIX)
  const calculatePCR = useCallback((data: any) => {
    if (!data || !data.calls || !data.puts) return 0;

    const totalCallOI = data.calls.reduce((sum: number, call: any) =>
      sum + (call.open_interest || call.oi || 0), 0);
    const totalPutOI = data.puts.reduce((sum: number, put: any) =>
      sum + (put.open_interest || put.oi || 0), 0);

    return totalCallOI > 0 ? totalPutOI / totalCallOI : 0;
  }, []);

  // Use backend PCR if valid, otherwise fallback to calculated PCR
  const pcr = useMemo(() => {
    return actualLiveData?.pcr && actualLiveData.pcr > 0
      ? actualLiveData.pcr
      : calculatePCR(actualLiveData);
  }, [actualLiveData?.pcr, calculatePCR]);

  // Remove render-time logging to prevent memory growth

  const tableRef = useRef<HTMLDivElement>(null);
  const atmRowRef = useRef<HTMLTableRowElement>(null);
  const hasScrolledRef = useRef<boolean>(false);

  // Remove render-time logging to prevent memory growth

  // Reset scroll flag when symbol changes
  useEffect(() => {
    hasScrolledRef.current = false;
  }, [symbol]);

  // Process live data from WebSocket (includes chain snapshot)
  useEffect(() => {
    if (actualLiveData && "calls" in actualLiveData && "puts" in actualLiveData && Array.isArray(actualLiveData.calls)) {
      // Process live data without render-time logging

      // Use spot price from live data (new field name)
      setSpotPrice(actualLiveData.spot_price);

      // Build unified strike map by merging calls and puts
      const strikeMap: { [key: number]: { call_oi: number; put_oi: number; call_ltp: number; put_ltp: number; call_volume: number; put_volume: number } } = {};

      // Process calls
      actualLiveData.calls.forEach((call: any) => {
        strikeMap[call.strike] = {
          call_oi: call.oi || 0,
          put_oi: 0,
          call_ltp: call.ltp || 0,
          put_ltp: 0,
          call_volume: call.volume || 0,
          put_volume: 0
        };
      });

      // Process puts and merge with existing strikes
      actualLiveData.puts.forEach((put: any) => {
        if (strikeMap[put.strike]) {
          // Merge with existing call data
          strikeMap[put.strike].put_oi = put.oi || 0;
          strikeMap[put.strike].put_ltp = put.ltp || 0;
          strikeMap[put.strike].put_volume = put.volume || 0;
        } else {
          // Add new put-only strike
          strikeMap[put.strike] = {
            call_oi: 0,
            put_oi: put.oi || 0,
            call_ltp: 0,
            put_ltp: put.ltp || 0,
            call_volume: 0,
            put_volume: put.volume || 0
          };
        }
      });

      // Convert strike map to array format for rendering
      const transformedData = Object.entries(strikeMap).map(([strike, data]) => ({
        strike: parseInt(strike),
        oi: data.call_oi,
        change: 0, // Not available in snapshot
        ltp: data.call_ltp,
        volume: data.call_volume,
        iv: 0, // Not available in snapshot
        put_oi: data.put_oi,
        put_change: 0,
        put_ltp: data.put_ltp,
        put_volume: data.put_volume,
        put_iv: 0,
      }));

      // Sort by strike for proper ordering
      transformedData.sort((a, b) => a.strike - b.strike);

      // Filter to ATM window (±500 strikes) - DO NOT filter by OI
      const filteredData = transformedData.filter(row => {
        const diff = Math.abs(row.strike - actualLiveData.atm_strike);
        return diff <= 500;   // keep ±500 window
      });

      // Process strike transformation without logging
      setOiData(filteredData);
      setLoading(false);
      setError(null);
    } else {
      // Handle invalid data silently
    }
  }, [actualLiveData]);

  // Remove render-time logging to prevent memory growth

  // Always render the UI, show loading/error states inline instead of blocking

  // Calculate max OI for intensity scaling
  const maxCallOI = Math.max(...oiData.map(r => r.oi), 1);
  const maxPutOI = Math.max(...oiData.map(r => r.put_oi), 1);

  return (
    <div className="w-full relative">
      {/* ── Dashboard Integration Header ─────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex flex-col gap-1">
          <SectionLabel>Option Intelligence Matrix</SectionLabel>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">Real-time OI Concentration</span>
            <div className={`w-1.5 h-1.5 rounded-full ${optionChainConnected ? 'bg-cyan-500 animate-pulse' : 'bg-slate-700'}`} />
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
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-red-500/50" />
              <span className="text-[9px] font-bold font-mono text-slate-500 uppercase">Calls</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-500/50" />
              <span className="text-[9px] font-bold font-mono text-slate-500 uppercase">Puts</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Spot Indicator ────────────────────────────────────────── */}
      {spotPrice && (
        <div className="group relative overflow-hidden mb-6 p-4 rounded-2xl bg-[#00E5FF]/[0.02] border border-[#00E5FF]/10 transition-all duration-500 hover:bg-[#00E5FF]/[0.04]">
          <div className="absolute top-0 left-0 w-1 h-full bg-[#00E5FF]" />
          <div className="flex items-center justify-between relative z-10">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold font-mono tracking-[0.2em] text-cyan-500/70 uppercase">Index Spot Reference</span>
              <span className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-widest mt-0.5">Live Feed Active</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] font-bold font-mono text-cyan-500/50">INR</span>
              <span
                className="text-3xl font-black tabular-nums tracking-tighter text-white"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              >
                {spotPrice.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── The Matrix ────────────────────────────────────────────── */}
      <div className="relative rounded-2xl overflow-hidden border border-white/5 bg-black/20 backdrop-blur-sm">

        {/* Matrix Header */}
        <div className="sticky top-0 z-30 bg-[#090e1a]/95 backdrop-blur-xl border-b border-white/10">
          <div className="grid grid-cols-7 py-3">
            <div className="col-span-3 text-center border-r border-white/5">
              <span className="text-[10px] font-bold font-mono tracking-[0.3em] text-red-500/80 uppercase">Call Dynamics</span>
            </div>
            <div className="col-span-1 text-center">
              <span className="text-[10px] font-bold font-mono tracking-[0.3em] text-cyan-400 uppercase">ATM</span>
            </div>
            <div className="col-span-3 text-center border-l border-white/5">
              <span className="text-[10px] font-bold font-mono tracking-[0.3em] text-green-500/80 uppercase">Put Dynamics</span>
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

        {/* Matrix Body */}
        <div
          ref={tableRef}
          className="overflow-y-auto custom-scrollbar"
          style={{ maxHeight: '520px' }}
        >
          <div className="flex flex-col">
            {oiData.map((row) => {
              const checkSpot = actualLiveData?.atm_strike || spotPrice || 0;
              const isATM = Math.abs(row.strike - checkSpot) <= 1;
              const callIntensity = row.oi / maxCallOI;
              const putIntensity = row.put_oi / maxPutOI;

              return (
                <div
                  key={row.strike}
                  ref={isATM ? atmRowRef : null}
                  className={`grid grid-cols-7 py-2.5 border-b border-white/[0.02] transition-colors duration-300 relative ${isATM ? 'bg-cyan-500/[0.06] border-y border-cyan-500/20 z-10' : 'hover:bg-white/[0.02]'
                    }`}
                >
                  {/* Call OI Intensity Bar */}
                  <div className="absolute right-[57.14%] top-0 bottom-0 pointer-events-none overflow-hidden transition-all duration-700" style={{ width: `${callIntensity * 42.8}%` }}>
                    <div className="absolute inset-0 bg-red-500/5 border-r border-red-500/20" />
                  </div>

                  {/* Call OI */}
                  <div className="text-right pr-6 text-[12px] font-bold font-mono tabular-nums text-red-100 relative z-10 transition-colors" style={{ opacity: callIntensity > 0.1 ? 1 : 0.4 }}>
                    {row.oi > 0 ? row.oi.toLocaleString() : '—'}
                  </div>

                  {/* Call Chg */}
                  <div className="text-center text-[11px] font-mono text-slate-600 tabular-nums">
                    {row.change !== 0 ? (row.change > 0 ? `+${row.change}` : row.change) : '—'}
                  </div>

                  {/* Call LTP */}
                  <div className="text-center text-[11px] font-bold font-mono text-slate-400 tabular-nums border-r border-white/5">
                    {row.ltp > 0 ? row.ltp.toFixed(1) : '—'}
                  </div>

                  {/* Strike */}
                  <div className={`text-center text-[13px] font-black font-mono tabular-nums tracking-tighter ${isATM ? 'text-cyan-400' : 'text-white'}`}>
                    {row.strike}
                  </div>

                  {/* Put LTP */}
                  <div className="text-center text-[11px] font-bold font-mono text-slate-400 tabular-nums border-l border-white/5">
                    {row.put_ltp > 0 ? row.put_ltp.toFixed(1) : '—'}
                  </div>

                  {/* Put Chg */}
                  <div className="text-center text-[11px] font-mono text-slate-600 tabular-nums">
                    {row.put_change !== 0 ? (row.put_change > 0 ? `+${row.put_change}` : row.put_change) : '—'}
                  </div>

                  {/* Put OI Intensity Bar */}
                  <div className="absolute left-[57.14%] top-0 bottom-0 pointer-events-none overflow-hidden transition-all duration-700" style={{ width: `${putIntensity * 42.8}%` }}>
                    <div className="absolute inset-0 bg-green-500/5 border-l border-green-500/20" />
                  </div>

                  {/* Put OI */}
                  <div className="text-left pl-6 text-[12px] font-bold font-mono tabular-nums text-green-100 relative z-10 transition-colors" style={{ opacity: putIntensity > 0.1 ? 1 : 0.4 }}>
                    {row.put_oi > 0 ? row.put_oi.toLocaleString() : '—'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Matrix Footer */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex gap-6">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500/20 border border-red-500/40" />
            <span className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-widest">Call Concentration</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500/20 border border-green-500/40" />
            <span className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-widest">Put Concentration</span>
          </div>
        </div>
        <span className="text-[9px] font-bold font-mono text-slate-700 uppercase tracking-[0.2em]">Quantum Option Matrix v4.2</span>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(0,229,255,0.2); }
      `}</style>
    </div>
  );
};


export default memo(OIHeatmap);
