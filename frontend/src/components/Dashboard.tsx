"use client";

import React, { useEffect, memo } from 'react';
import { AlertTriangle, Minus } from 'lucide-react';
import { useLiveMarketData } from '../hooks/useLiveMarketData';
import { useExpirySelector } from '../hooks/useExpirySelector';
import { useMarketContextStore } from '../stores/marketContextStore';
import { useModeGuard, useEffectiveSpot } from './SafeModeGuard';
import SymbolSelector from './SymbolSelector';
import dynamic from 'next/dynamic';
const LoadingPlaceholder = () => (
  <div className="animate-pulse flex flex-col gap-4 p-4 grayscale opacity-50">
    <div className="h-4 bg-slate-700 rounded w-1/4"></div>
    <div className="h-20 bg-slate-700 rounded"></div>
  </div>
);

// ── Lazy load heavy panels (Task 10) ──────────────────────────────────────────
const OIHeatmap = dynamic(() => import('./OIHeatmap'), { ssr: false, loading: () => <LoadingPlaceholder /> });
const AIInterpretationPanel = dynamic(() => import('./AIInterpretationPanel'), { ssr: false, loading: () => <LoadingPlaceholder /> });
const AlertPanelFinal = dynamic(() => import('./intelligence/AlertPanelFinal'), { ssr: false, loading: () => <LoadingPlaceholder /> });
const AICommandCenter = dynamic(() => import('./AICommandCenter'), { ssr: false, loading: () => <LoadingPlaceholder /> });
const StrategyPlanPanel = dynamic(() => import('./intelligence/StrategyPlanPanel'), { ssr: false, loading: () => <LoadingPlaceholder /> });

// ── Dashboard sub-components ─────────────────────────────────────────────────
import { LoadingBlock, SnapshotReadyBlock, ErrorBlock } from './dashboard/DashboardBlocks';
import { TickerStrip } from './dashboard/TickerStrip';
import { StatCardsRow } from './dashboard/StatCards';
import { GammaExposurePanel } from './dashboard/GammaExposurePanel';
import { InstitutionalFlowPanel } from './dashboard/InstitutionalFlowPanel';
import { SignalMatrixPanel } from './dashboard/SignalMatrixPanel';
import { TradeSetupPanel } from './dashboard/TradeSetupPanel';
import { ChartIntelligencePanel } from './dashboard/ChartIntelligencePanel';
import { VolatilityRegimePanel } from './dashboard/VolatilityRegimePanel';
import { TrapDetectionPanel } from './dashboard/TrapDetectionPanel';
import { GammaSqueezePanel } from './dashboard/GammaSqueezePanel';
import { LiquidityVacuumPanel } from './dashboard/LiquidityVacuumPanel';
import { ExpiryMagnetPanel } from './dashboard/ExpiryMagnetPanel';
import { BiasPanel, ExpectedMovePanel } from './dashboard/BiasAndMove';
import { SmartMoneyPanel, LiquidityPanel } from './dashboard/SmartMoneyAndLiquidity';
import { CARD } from './dashboard/DashboardTypes';
import type { LiveMarketData } from '../hooks/useLiveMarketData';

// ── Memoized heavy panels (Task 10) ─────────────────────────────────────────────
const MemoizedOIHeatmap = memo(OIHeatmap);
const MemoizedAIPanel = memo(AIInterpretationPanel);
const MemoizedAlerts = memo(AlertPanelFinal);
const MemoizedAICommandCenter = memo(AICommandCenter);
const MemoizedStrategyPlan = memo(StrategyPlanPanel);

// ── Types ─────────────────────────────────────────────────────────────────────
interface DashboardProps { initialSymbol?: string; }

// ── Global dashboard CSS ──────────────────────────────────────────────────────
const DASHBOARD_CSS = `
  /* ── Panel card base ──────────────────────────────────────────── */
  .trading-panel {
    background: rgba(6,9,18,0.72);
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.07);
    padding: 20px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25), 0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(24px);
  }
  .trading-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(0,229,255,0.30) 50%, transparent 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }
  .trading-panel::after {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: radial-gradient(ellipse at top left, rgba(0,229,255,0.03), transparent 60%);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }
  .trading-panel:hover {
    border-color: rgba(0,229,255,0.20);
    box-shadow: 0 2px 6px rgba(0,0,0,0.30), 0 12px 40px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,229,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06);
  }
  .trading-panel:hover::before { opacity: 1; }
  .trading-panel:hover::after  { opacity: 1; }
  .trading-panel.no-pad { padding: 0; }

  /* ── Panel section label ─────────────────────────────────────── */
  .panel-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(148,163,184,0.55);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 4px;
  }

  /* ── 12-col responsive grid ──────────────────────────────────── */
  .dash-grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 18px;
  }

  /* Desktop: exact col spans */
  .col-12 { grid-column: span 12; }
  .col-8  { grid-column: span 8;  }
  .col-6  { grid-column: span 6;  }
  .col-4  { grid-column: span 4;  }
  .col-3  { grid-column: span 3;  }

  /* Tablet (768–1279px): 2 columns for most panels */
  @media (max-width: 1279px) and (min-width: 768px) {
    .dash-grid { gap: 14px; }
    .col-3  { grid-column: span 6;  }
    .col-4  { grid-column: span 6;  }
    .col-8  { grid-column: span 12; }
  }

  /* Mobile (<768px): full width for most, 2-col for small panels */
  @media (max-width: 767px) {
    .dash-grid { gap: 12px; }
    .col-3  { grid-column: span 6;  }
    .col-4  { grid-column: span 12; }
    .col-6  { grid-column: span 12; }
    .col-8  { grid-column: span 12; }
  }

  /* Extra-small (<480px): all full width */
  @media (max-width: 479px) {
    .col-3  { grid-column: span 12; }
  }

  /* h-full support inside grid cells */
  .dash-grid > div > .trading-panel.h-full { height: 100%; }

  /* ── Section divider ─────────────────────────────────────────── */
  .section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,229,255,0.12), rgba(99,102,241,0.10), transparent);
    margin: 2px 0;
    border-radius: 1px;
  }

  /* ── Metric row ──────────────────────────────────────────────── */
  .metric-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 0;
  }
  .metric-label {
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(148,163,184,0.55);
  }
  .metric-value {
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #fff;
    font-variant-numeric: tabular-nums;
  }

  /* ── Stat mini-card ──────────────────────────────────────────── */
  .stat-mini {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 10px 12px;
    transition: background 0.2s ease, border-color 0.2s ease;
  }
  .stat-mini:hover {
    background: rgba(255,255,255,0.042);
    border-color: rgba(255,255,255,0.11);
  }
`;



// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard({ initialSymbol = 'NIFTY' }: DashboardProps) {
  const setCurrentSymbol = useMarketContextStore(state => state.setSymbol);
  const currentSymbol = useMarketContextStore(state => state.symbol);

  useEffect(() => {
    if (currentSymbol === 'NIFTY' && initialSymbol !== 'NIFTY') {
      setCurrentSymbol(initialSymbol);
    }
  }, [initialSymbol, setCurrentSymbol, currentSymbol]);

  const {
    expiryList,
    selectedExpiry,
    loadingExpiries,
    expiryError,
    handleExpiryChange,
    optionChainConnected
  } = useExpirySelector();

  const { data, error, loading, mode } = useLiveMarketData(currentSymbol, selectedExpiry);

  const isLiveMode = useModeGuard(mode, 'LIVE');
  const isSnapshotMode = useModeGuard(mode, 'SNAPSHOT');
  const effectiveSpot = useEffectiveSpot(data, mode);
  const isAnalyticsEnabled = (data as any)?.analytics_enabled !== false;

  // Inject global CSS once
  React.useEffect(() => {
    const id = 'dashboard-global-css';
    if (!document.getElementById(id)) {
      const el = document.createElement('style');
      el.id = id;
      el.textContent = DASHBOARD_CSS;
      document.head.appendChild(el);
    }
    return () => { document.getElementById(id)?.remove(); };
  }, []);

  // Snapshot-mode body class
  React.useEffect(() => {
    document.body.classList.toggle('snapshot-mode', mode !== 'live');
  }, [mode]);

  const safeError = typeof error === 'string' ? error : null;
  const modeLabel = mode === 'live' ? 'LIVE' : mode === 'snapshot' ? 'SNAPSHOT' : mode === 'error' ? 'HALTED' : 'OFFLINE';
  const modeColor = mode === 'live' ? '#4ade80' : mode === 'snapshot' ? '#60a5fa' : '#f87171';

  // ── State guards ─────────────────────────────────────────────────────────────
  if (loading) return mode === 'snapshot' ? <SnapshotReadyBlock /> : <LoadingBlock />;
  if (safeError) return <ErrorBlock message={safeError} />;

  // ── Main render ──────────────────────────────────────────────────────────────
  return (
    <div className="w-full">
      {/* Subtle grid overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          backgroundImage: 'linear-gradient(rgba(0,229,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,1) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          opacity: 0.016,
        }}
      />

      <div className="relative z-10 w-full max-w-[1920px] mx-auto px-3 sm:px-5 lg:px-8 py-4 sm:py-6">
        <div className="dash-grid">

          {/* ROW 1 — Symbol Selector (full width) */}
          <div className="col-12" style={{ position: 'relative', zIndex: 100 }}>
            <div className="trading-panel" style={{ overflow: 'visible' }}>
              <SymbolSelector />
            </div>
          </div>

          {/* ROW 2 — Ticker Strip (full width) */}
          <div className="col-12">
            <TickerStrip
              symbol={currentSymbol}
              data={data}
              effectiveSpot={effectiveSpot}
              mode={mode}
              modeLabel={modeLabel}
              modeColor={modeColor}
            />
          </div>

          {/* ROW 3 — Four Stat Cards (full width, internally 4-col) */}
          <div className="col-12">
            <StatCardsRow data={data} isAnalyticsEnabled={isAnalyticsEnabled} />
          </div>

          {/* ROW 4 — Alert Panel (compact, full width) */}
          <div className="col-12">
            <div className="trading-panel" style={{ padding: '10px 16px' }}>
              <MemoizedAlerts alerts={(data as any)?.alerts || []} />
            </div>
          </div>

          {/* ROW 5 — Market Bias (4 cols) | Expected Move Range (8 cols) */}
          <div className="col-4">
            <BiasPanel data={data} />
          </div>
          <div className="col-8">
            <ExpectedMovePanel data={data} isSnapshotMode={isSnapshotMode} />
          </div>

          {/* ROW 6 — Smart Money | Liquidity | Gamma Exposure | Institutional Flow (3 cols each) */}
          <div className="col-3">
            <SmartMoneyPanel data={data} isSnapshotMode={isSnapshotMode} />
          </div>
          <div className="col-3">
            <LiquidityPanel data={data} />
          </div>
          <div className="col-3">
            <GammaExposurePanel data={data} />
          </div>
          <div className="col-3">
            <InstitutionalFlowPanel data={data} />
          </div>

          {/* ROW 7 — Signal Matrix (4 cols) | Trade Setup (4 cols) | Chart Intelligence (4 cols) */}
          <div className="col-4">
            <SignalMatrixPanel data={data} />
          </div>
          <div className="col-4">
            <TradeSetupPanel data={data} />
          </div>
          <div className="col-4">
            <ChartIntelligencePanel data={data} />
          </div>

          {/* ROW 8 — Volatility Regime (full width) */}
          <div className="col-12">
            <VolatilityRegimePanel data={data} />
          </div>

          {/* ROW 9 — OI Heatmap (full width, horizontal scroll) */}
          <div className="col-12">
            <div className="trading-panel" style={{ padding: 0 }}>
              <div id="oi-heatmap" className="rounded-2xl overflow-x-auto" style={CARD}>
                <div className="h-[1px] w-full" style={{ background: 'linear-gradient(90deg, transparent, rgba(245,158,11,0.40), transparent)' }} />
                <div className="p-4 sm:p-5 min-w-[640px]">
                  <MemoizedOIHeatmap symbol={currentSymbol} />
                </div>
              </div>
            </div>
          </div>

          {/* ROW 10 — Advanced Intelligence: 4 panels × 3 cols */}
          <div className="col-3">
            <TrapDetectionPanel data={data} />
          </div>
          <div className="col-3">
            <GammaSqueezePanel data={data} />
          </div>
          <div className="col-3">
            <LiquidityVacuumPanel data={data} />
          </div>
          <div className="col-3">
            <ExpiryMagnetPanel data={data} />
          </div>

          {/* ROW 11 — Strategy Plan (Full Width) */}
          <div className="col-12">
            <div className="trading-panel">
              <MemoizedStrategyPlan symbol={currentSymbol} />
            </div>
          </div>

          {/* ROW 12 — AI Interpretation Panel (full width) */}
          <div className="col-12">
            <div className="trading-panel">
              <div id="section-ai" className="scroll-mt-20" />
              <MemoizedAIPanel intelligence={data?.intelligence ?? null} />
            </div>
          </div>

          {/* ROW 13 — AI Command Center (full width) */}
          <div className="col-12">
            <div className="trading-panel">
              <MemoizedAICommandCenter />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
