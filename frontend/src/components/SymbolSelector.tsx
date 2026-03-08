"use client";
import React from 'react';
import { useMarketStore } from '@/stores/marketStore';
import { useExpirySelector } from '@/hooks/useExpirySelector';
import { PremiumDropdown } from '@/components/ui/PremiumDropdown';
import { BarChart2, Calendar } from 'lucide-react';

const SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY"];

export default function SymbolSelector() {
  const currentSymbol = useMarketStore(state => state.currentSymbol);
  const setCurrentSymbol = useMarketStore(state => state.setCurrentSymbol);

  const {
    expiryList,
    selectedExpiry,
    loadingExpiries,
    handleExpiryChange,
  } = useExpirySelector();

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between',
      width: '100%',
      gap: 16,
    }}>

      {/* ── Left: Symbol toggle ───────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>

        {/* Label */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 2 }}>
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
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: 4,
          borderRadius: 12,
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          {SYMBOLS.map(s => {
            const active = s === currentSymbol;
            return (
              <button
                key={s}
                onClick={() => setCurrentSymbol(s)}
                style={{
                  padding: '5px 16px',
                  borderRadius: 8,
                  fontSize: 11,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  cursor: 'pointer',
                  transition: 'all 0.18s ease',
                  background: active ? 'rgba(0,229,255,0.12)' : 'transparent',
                  color: active ? '#00E5FF' : 'rgba(148,163,184,0.60)',
                  border: active ? '1px solid rgba(0,229,255,0.28)' : '1px solid transparent',
                  boxShadow: active ? '0 0 12px rgba(0,229,255,0.14), inset 0 1px 0 rgba(255,255,255,0.06)' : 'none',
                }}
              >
                {s}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Right: Expiry dropdown ────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
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
          minWidth={148}
        />
      </div>

    </div>
  );
}
