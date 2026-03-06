import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { uiLog } from '../utils/uiLogger';
import { getTraceId } from '../utils/traceManager';

// Type definitions for market data
interface IndexData {
  symbol: string;
  ltp: number;
  change: number;
  change_percent: number;
}

interface OptionData {
  strike: number;
  call_oi: number;
  call_ltp: number;
  call_volume: number;
  put_oi: number;
  put_ltp: number;
  put_volume: number;
}

interface OptionChain {
  symbol: string;
  spot: number;
  atm_strike: number;
  expiry: string;
  strikes: OptionData[];
}

interface HeatmapData {
  strike: number;
  call_oi_intensity: number;
  put_oi_intensity: number;
  distance_from_atm: number;
  call_oi: number;
  put_oi: number;
  total_oi: number;
}

interface Heatmap {
  symbol: string;
  spot: number;
  atm_strike: number;
  pcr: number;
  total_call_oi: number;
  total_put_oi: number;
  heatmap: HeatmapData[];
}

interface Analytics {
  pcr?: number;
  expected_move?: {
    move_1sd: number;
    move_2sd: number;
    breakout_detected: boolean;
    breakout_direction: string;
    implied_volatility: number;
  };
  market_bias?: {
    bias_strength: number;
    divergence_detected: boolean;
    divergence_type: string;
    price_vs_vwap: number;
  };
  structural?: {
    gamma_regime: string;
    intent_score: number;
    support_level: number;
    resistance_level: number;
  };
}

interface MarketStore {
  // Connection state
  connected: boolean;
  marketOpen: boolean | null;
  lastUpdate: number;
  currentSymbol: string;
  
  // Index data
  index: IndexData | null;
  spot: number | null;
  
  // Option chain
  optionChain: OptionChain | null;
  
  // Heatmap data
  heatmap: Heatmap | null;
  
  // Analytics
  analytics: Analytics | null;
  aiSignals: any[];
  
  // Actions
  setConnected: (connected: boolean) => void;
  setMarketOpen: (open: boolean) => void;
  setCurrentSymbol: (symbol: string) => void;
  setSpot: (spot: number) => void;
  updateIndex: (data: IndexData & { timestamp: number }) => void;
  updateOptionChain: (data: OptionChain & { timestamp: number }) => void;
  updateHeatmap: (data: Heatmap & { timestamp: number }) => void;
  updateAnalytics: (data: Analytics & { timestamp: number }) => void;
  setAISignals: (signals: any[]) => void;
  updateMarketData: (data: Partial<MarketStore> & { connected?: boolean; lastUpdate?: number; marketOpen?: boolean }) => void;
  clearData: () => void;
}

// Create the unified market store
export const useMarketStore = create<MarketStore>()(
  subscribeWithSelector((set, get) => ({
    // Connection state
    connected: false,
    marketOpen: null,
    lastUpdate: 0,
    currentSymbol: 'NIFTY',
    
    // Data
    index: null,
    spot: null,
    optionChain: null,
    heatmap: null,
    analytics: null,
    aiSignals: [],
    
    // Actions with logging
    setConnected: (connected) => {
      console.log("WS TRACE → STATE SOURCE", { store: "marketStore", field: "connected", value: connected });
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "connected", value: connected });
      set({ connected });
    },
    
    setMarketOpen: (open) => {
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "marketOpen", value: open });
      set({ marketOpen: open });
    },
    
    setCurrentSymbol: (symbol) => {
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "currentSymbol", value: symbol });
      set({ currentSymbol: symbol });
    },
    
    setSpot: (spot) => {
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "spot", value: spot });
      set({ spot });
    },
    
    updateIndex: (data) => {
      const { timestamp, ...indexData } = data;
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "index", value: indexData });
      
      set((state) => ({
        index: indexData,
        spot: indexData.ltp,
        lastUpdate: timestamp,
        connected: true
      }));
    },
    
    updateOptionChain: (data) => {
      const { timestamp, ...chainData } = data;
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "optionChain", size: chainData.strikes?.length || 0 });
      
      set((state) => ({
        optionChain: chainData,
        lastUpdate: timestamp,
        connected: true
      }));
    },
    
    updateHeatmap: (data) => {
      const { timestamp, ...heatmapData } = data;
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "heatmap", size: heatmapData.heatmap?.length || 0 });
      
      set((state) => ({
        heatmap: heatmapData,
        lastUpdate: timestamp,
        connected: true
      }));
    },
    
    updateAnalytics: (data) => {
      const { timestamp, ...analyticsData } = data;
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "analytics", keys: Object.keys(analyticsData) });
      
      set((state) => ({
        analytics: analyticsData,
        lastUpdate: timestamp,
        connected: true
      }));
    },
    
    setAISignals: (signals) => {
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "aiSignals", count: signals.length });
      set({ aiSignals: signals });
    },
    
    updateMarketData: (update) => {
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "marketData", update });
      
      set((state) => ({
        ...state,
        ...update
      }));
    },
    
    clearData: () => {
      const traceId = getTraceId();
      uiLog("STORE UPDATE", { traceId, store: "marketStore", field: "clearData" });
      
      set({
        index: null,
        optionChain: null,
        heatmap: null,
        analytics: null,
        aiSignals: [],
        connected: false,
        lastUpdate: 0
      });
    }
  }))
);

// Selectors for optimized component access
export const useIndexData = () => useMarketStore((state) => state.index);
export const useOptionChain = () => useMarketStore((state) => state.optionChain);
export const useHeatmap = () => useMarketStore((state) => state.heatmap);
export const useAnalytics = () => useMarketStore((state) => state.analytics);
export const useConnectionStatus = () => useMarketStore((state) => ({
  connected: state.connected,
  lastUpdate: state.lastUpdate
}));

// Computed selectors
export const useMarketStatus = () => useMarketStore((state) => {
  const index = state.index;
  const marketOpen = state.marketOpen;
  
  return {
    marketOpen: marketOpen !== null ? marketOpen : false,
    symbol: index?.symbol || state.currentSymbol
  };
});

export const useATMStrike = () => useMarketStore((state) => {
  const optionChain = state.optionChain;
  const index = state.index;
  
  if (!optionChain || !index) {
    return null;
  }
  
  return optionChain.atm_strike;
});

export const usePCR = () => useMarketStore((state) => {
  const heatmap = state.heatmap;
  const analytics = state.analytics;
  
  // Prefer heatmap PCR, fallback to analytics
  return heatmap?.pcr || analytics?.pcr || 0;
});

export const useExpectedMove = () => useMarketStore((state) => {
  const analytics = state.analytics;
  return analytics?.expected_move || null;
});

export const useMarketBias = () => useMarketStore((state) => {
  const analytics = state.analytics;
  return analytics?.market_bias || null;
});

// Export types for external use
export type {
  IndexData,
  OptionData,
  OptionChain,
  HeatmapData,
  Heatmap,
  Analytics,
  MarketStore
};
