"use client";

import React, { useEffect, memo } from 'react';
import { useLiveMarketData } from '../hooks/useLiveMarketData';
import { useExpirySelector } from '../hooks/useExpirySelector';
import { useMarketContextStore } from '../stores/marketContextStore';
import SymbolSelector from './SymbolSelector';
import dynamic from 'next/dynamic';
const LoadingPlaceholder = () => (
  <div className="flex flex-col gap-4 p-4 opacity-70">
    <div className="h-4 bg-slate-800 animate-pulse rounded w-1/4"></div>
    <div className="h-20 bg-slate-800 animate-pulse rounded"></div>
  </div>
);

// ── Lazy load heavy panels (Task 10) ──────────────────────────────────────────
const OIHeatmap = dynamic(() => import('./optionChain/OIHeatmap'), { ssr: false, loading: () => <LoadingPlaceholder /> });
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
import { StrikeIQPriceChart } from './charts/StrikeIQPriceChart';

// ── Memoized heavy panels (Task 10) ─────────────────────────────────────────────
const MemoizedOIHeatmap = memo(OIHeatmap);
const MemoizedAIPanel = memo(AIInterpretationPanel);
const MemoizedAlerts = memo(AlertPanelFinal);
const MemoizedStrategyPlan = memo(StrategyPlanPanel);

// ── Types ─────────────────────────────────────────────────────────────────────
interface DashboardProps { initialSymbol?: string; }

// ── Global dashboard CSS ──────────────────────────────────────────────────────
const DASHBOARD_CSS = `
  /* ── Panel card base ──────────────────────────────────────────── */
  .trading-panel {
    background: rgba(6, 9, 18, 0.9);
    border-radius: 20px;
    border: 1px solid rgba(0, 229, 255, 0.15);
    padding: 24px;
    box-shadow: 
      0 12px 20px -5px rgba(0, 0, 0, 0.4), 
      0 8px 10px -6px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 0 rgba(255, 255, 255, 0.05);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(20px);
  }

  .trading-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.4), transparent);
    opacity: 0;
    transition: opacity 0.4s ease;
  }

  .trading-panel:hover {
    background: rgba(15, 23, 42, 0.75);
    border-color: rgba(56, 189, 248, 0.4);
    box-shadow: 
      0 25px 30px -10px rgba(0, 0, 0, 0.5), 
      0 15px 20px -10px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 0 rgba(255, 255, 255, 0.15);
    transform: translateY(-3px);
  }

  .trading-panel:hover::before { opacity: 1; }
  
  .trading-panel.no-pad { padding: 0; }

  /* ── Panel section label ─────────────────────────────────────── */
  .panel-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.6);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 8px;
    display: block;
  }

  /* ── 12-col responsive grid ──────────────────────────────────── */
  .dash-grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 20px;
  }

  .col-12 { grid-column: span 12; }
  .col-8  { grid-column: span 8;  }
  .col-6  { grid-column: span 6;  }
  .col-4  { grid-column: span 4;  }
  .col-3  { grid-column: span 3;  }

  @media (max-width: 1279px) and (min-width: 768px) {
    .dash-grid { gap: 16px; }
    .col-3  { grid-column: span 6;  }
    .col-4  { grid-column: span 6;  }
    .col-8  { grid-column: span 12; }
  }

  @media (max-width: 767px) {
    .dash-grid { gap: 14px; }
    .col-3  { grid-column: span 6;  }
    .col-4  { grid-column: span 12; }
    .col-6  { grid-column: span 12; }
    .col-8  { grid-column: span 12; }
  }

  @media (max-width: 479px) {
    .dash-grid { gap: 12px; }
    .col-3  { grid-column: span 12; }
  }

  .dash-grid > div > .trading-panel.h-full { height: 100%; }

  /* ── Section divider ─────────────────────────────────────────── */
  .section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.1), transparent);
    margin: 4px 0;
  }

  /* ── Metric row ──────────────────────────────────────────────── */
  .metric-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  }
  
  .metric-row:last-child {
    border-bottom: none;
  }

  .metric-label {
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: #94a3b8;
  }

  .metric-value {
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #f8fafc;
  }

  /* ── Stat mini-card ──────────────────────────────────────────── */
  .stat-mini {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 14px;
    padding: 12px 16px;
    transition: all 0.3s ease;
  }

  .stat-mini:hover {
    background: rgba(30, 41, 59, 0.5);
    border-color: rgba(56, 189, 248, 0.3);
    transform: scale(1.02);
  }
`;

// ── Main Dashboard ────────────────────────────────────────────────────────────
function DashboardComponent({ initialSymbol = 'NIFTY' }: DashboardProps) {
  // Optional safety: ensure client-side only
  if (typeof window === 'undefined') return null;
  
  try {
    const setCurrentSymbol = useMarketContextStore(state => state.setSymbol);
    const currentSymbol = useMarketContextStore(state => state.symbol);

    useEffect(() => {
      if (currentSymbol === 'NIFTY' && initialSymbol !== 'NIFTY') {
        setCurrentSymbol(initialSymbol);
      }
    }, [initialSymbol, currentSymbol]);

    const {
      selectedExpiry,
    } = useExpirySelector();

    // Unified Store Hook - Law 7
    const liveMarketData = useLiveMarketData(currentSymbol, selectedExpiry);

    // Full component guard for analytics data
    if (!liveMarketData) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <div className="text-gray-400">Loading...</div>
          </div>
        </div>
      );
    }

    return (
    <div className="min-h-screen bg-[#020408] text-slate-200 font-sans selection:bg-sky-500/30 overflow-x-hidden mesh-background">
      <style>{DASHBOARD_CSS}</style>

      {/* ── Visual Grid Overlay ─────────────────────────────────────── */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          backgroundImage: 'linear-gradient(rgba(56, 189, 248, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.03) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative z-10 w-full max-w-[1920px] mx-auto px-3 sm:px-5 lg:px-8 py-4 sm:py-6">
        <div className="dash-grid">

          {/* ROW 1 — Ticker Strip (full width) */}
          <div className="col-12">
            <TickerStrip symbol={currentSymbol} />
          </div>

          {/* ROW 2 — Symbol Selector (full width) */}
          <div className="col-12" style={{ position: 'relative', zIndex: 100 }}>
            <div className="trading-panel scanline-overlay" style={{ overflow: 'visible' }}>
              <SymbolSelector />
            </div>
          </div>

          {/* ROW 3 — Four Stat Cards (full width, internally 4-col) */}
          <div className="col-12">
            <StatCardsRow />
          </div>

          {/* ROW 4 — Alert Panel (compact, full width) */}
          <div className="col-12">
            <div className="trading-panel" style={{ padding: '10px 16px' }}>
              <MemoizedAlerts />
            </div>
          </div>

          {/* ROW 5 — Market Bias (4 cols) | Expected Move Range (8 cols) */}
          <div className="col-4">
            <BiasPanel />
          </div>
          <div className="col-8">
            <ExpectedMovePanel />
          </div>

          {/* ROW 6 — Smart Money | Liquidity | Gamma Exposure | Institutional Flow (3 cols each) */}
          <div className="col-3 flex flex-col items-stretch">
            <SmartMoneyPanel />
          </div>
          <div className="col-3 flex flex-col items-stretch">
            <LiquidityPanel />
          </div>
          <div className="col-3 flex flex-col items-stretch">
            <GammaExposurePanel />
          </div>
          <div className="col-3 flex flex-col items-stretch">
            <InstitutionalFlowPanel />
          </div>

          {/* ROW 7 — Signal Matrix | Trade Setup | Chart Intelligence | Strategy Plan (3 cols each) */}
          <div className="col-3 flex flex-col items-stretch h-full">
            <SignalMatrixPanel />
          </div>
          <div className="col-3 flex flex-col items-stretch h-full">
            <TradeSetupPanel />
          </div>
          <div className="col-3 flex flex-col items-stretch h-full">
            <ChartIntelligencePanel />
          </div>
          <div className="col-3 flex flex-col items-stretch h-full">
            <MemoizedStrategyPlan />
          </div>

          {/* ROW 8 — Volatility Regime (full width) */}
          <div className="col-6">
            <VolatilityRegimePanel />
          </div>
          {/* ROW 9 — AI Interpretation Panel (full width) */}
          <div className="col-6">
            <div className="trading-panel">
              <MemoizedAIPanel />
            </div>
          </div>

          {/* ROW 10 — StrikeIQ Unified Chart (full width) */}
          <div className="col-12">
            <div className="trading-panel">
              <StrikeIQPriceChart data={liveMarketData.data} />
            </div>
          </div>

          {/* ROW 11 — OI Heatmap (full width, horizontal scroll) */}
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

          {/* ROW 12 — Advanced Intelligence: 4 panels × 3 cols */}
          <div className="col-3">
            <TrapDetectionPanel />
          </div>
          <div className="col-3">
            <GammaSqueezePanel />
          </div>
          <div className="col-3">
            <LiquidityVacuumPanel />
          </div>
          <div className="col-3">
            <ExpiryMagnetPanel />
          </div>


          {/* ROW 14 — AI Command Center (full width) */}
          <div className="col-12">
            <div className="trading-panel">
              <AICommandCenter />
            </div>
          </div>

        </div>
      </div>
    </div>
    );
  } catch (err) {
    console.error("Dashboard crash:", err);
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-500 text-xl font-bold mb-4">Dashboard crashed</div>
          <div className="text-gray-300">Check console for details</div>
        </div>
      </div>
    );
  }
}

const Dashboard = memo(DashboardComponent);

export default Dashboard;
