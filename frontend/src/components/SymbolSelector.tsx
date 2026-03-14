"use client";
import React from 'react';
import { useMarketContextStore } from '@/stores/marketContextStore';
import { useExpirySelector } from '@/hooks/useExpirySelector';
import { resubscribeMarketWS } from '@/services/wsService';
import { PremiumDropdown } from '@/components/ui/PremiumDropdown';
import { BarChart2, Calendar } from 'lucide-react';

const SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY"];

export default function SymbolSelector() {
  const currentSymbol = useMarketContextStore(state => state.symbol);
  const setCurrentSymbol = useMarketContextStore(state => state.setSymbol);
  
  const timeframe = useMarketContextStore(state => state.timeframe || '1m');
  const setTimeframe = useMarketContextStore(state => state.setTimeframe);
  
  const handleSymbolChange = (sym: string) => {
    setCurrentSymbol(sym);
    // Send subscription message to backend for the new symbol
    resubscribeMarketWS(sym, selectedExpiry);
  };

  const handleTimeframeChange = (tf: string) => {
    setTimeframe(tf);
    // Map timeframe UI labels to API parameters
    const timeframeMap: { [key: string]: string } = {
      '1m': '1minute',
      '5m': '5minute',
      '15m': '15minute',
      '1h': '60minute',
      '1d': 'day'
    };
    
    const apiTimeframe = timeframeMap[tf] || tf;
    console.log('TIMEFRAME CHANGED', { ui: tf, api: apiTimeframe });
    
    // Fetch candles for new timeframe (implement this based on your candle fetching logic)
    // fetchCandles(currentSymbol, apiTimeframe);
  };

  const {
    expiryList,
    selectedExpiry,
    loadingExpiries,
    handleExpiryChange,
  } = useExpirySelector();

  return (
    <div className="flex flex-wrap items-center gap-2">

      {/* ── Left: Symbol toggle ───────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-4">

        {/* Label */}
        <div className="flex items-center gap-1 sm:gap-2">
          <BarChart2 size={14} style={{ color: 'rgba(0,229,255,0.70)' }} />
          <span style={{
            fontSize: 10,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 700,
            letterSpacing: '0.20em',
            textTransform: 'uppercase',
            color: 'rgba(148,163,184,0.50)',
          }}>
            Index
          </span>
        </div>

        {/* Toggle pills */}
        <div className="flex items-center gap-1 sm:gap-2 p-1 sm:p-2 rounded-xl bg-white/4 border border-white/8">
          {SYMBOLS.map(s => {
            const active = s === currentSymbol;
            return (
              <button
                key={s}
                onClick={() => handleSymbolChange(s)}
                className="px-2 py-1 sm:px-4 sm:py-1.5 text-xs sm:text-sm rounded-lg font-bold font-mono tracking-wider cursor-pointer transition-all duration-180 ease-in-out"
                style={{
                  background: active ? 'rgba(0,229,255,0.12)' : 'transparent',
                  color: active ? '#00E5FF' : 'rgba(148,163,184,0.60)',
                  border: active ? '1px solid rgba(0,229,255,0.28)' : '1px solid transparent',
                  boxShadow: active ? '0 0 12px rgba(0,229,255,0.14), inset 0 1px 0 rgba(255,255,255,0.06)' : 'none',
                  letterSpacing: '0.08em',
                }}
              >
                {s}
              </button>
            );
          })}
        </div>

        {/* Timeframe toggle */}
        <div className="flex flex-wrap items-center gap-1 sm:gap-2 mt-2 sm:mt-0">
          {/* Label */}
          <div className="flex items-center gap-1 sm:gap-2">
            <span style={{
              fontSize: 10,
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 700,
              letterSpacing: '0.20em',
              textTransform: 'uppercase',
              color: 'rgba(148,163,184,0.50)',
            }}>
              TF
            </span>
          </div>
          <div className="flex items-center gap-0.5 sm:gap-1 p-0.5 sm:p-1 rounded-lg bg-white/4 border border-white/8">
            {['1m', '5m', '15m'].map(tf => {
              const active = tf === timeframe;
              return (
                <button
                  key={tf}
                  onClick={() => handleTimeframeChange(tf)}
                  className="px-2 py-1 sm:px-3 sm:py-1.5 text-xs sm:text-sm rounded-md font-bold font-mono cursor-pointer transition-all duration-180 ease-in-out"
                  style={{
                    background: active ? 'rgba(0,229,255,0.12)' : 'transparent',
                    color: active ? '#00E5FF' : 'rgba(148,163,184,0.60)',
                    border: active ? '1px solid rgba(0,229,255,0.28)' : '1px solid transparent',
                  }}
                >
                  {tf}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Right: Expiry dropdown ────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-2 sm:mt-0 w-full sm:w-auto">
        <div className="flex items-center gap-1 sm:gap-2">
          <Calendar size={12} style={{ color: 'rgba(148,163,184,0.45)' }} />
          <span style={{
            fontSize: 10,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 700,
            letterSpacing: '0.20em',
            textTransform: 'uppercase',
            color: 'rgba(148,163,184,0.45)',
          }}>
            Expiry
          </span>
        </div>

        <PremiumDropdown
          value={selectedExpiry || ''}
          onChange={handleExpiryChange}
          options={expiryList}
          placeholder="Select expiry"
          loading={loadingExpiries}
          minWidth={120}
        />
      </div>

    </div>
  );
}
