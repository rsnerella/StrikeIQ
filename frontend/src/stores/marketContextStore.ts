import { create } from 'zustand';

interface MarketContextState {
  symbol: string;
  expiry: string | null;
  timeframe: string;
  setSymbol: (symbol: string) => void;
  setExpiry: (expiry: string | null) => void;
  setTimeframe: (timeframe: string) => void;
}

import { persist } from 'zustand/middleware';

export const useMarketContextStore = create<MarketContextState>()(
  persist(
    (set) => ({
      symbol: "NIFTY",
      expiry: null,
      timeframe: "1m",
      setSymbol: (symbol) => set({ symbol }),
      setExpiry: (expiry) => set({ expiry }),
      setTimeframe: (timeframe) => set({ timeframe }),
    }),
    {
      name: 'strikeiq-market-context',
    }
  )
);
