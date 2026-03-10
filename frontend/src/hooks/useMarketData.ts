/**
 * Hook to access live market data from WebSocket store
 * Provides persistent access to market_data without closing connection
 */

import { useWSStore } from '../core/ws/wsStore';
import { useShallow } from 'zustand/shallow';

export function useMarketData() {
  // PERFORMANCE: Use grouped selectors to prevent unnecessary re-renders
  const { marketData, connected, error } = useWSStore(
    useShallow(state => ({
      marketData: state.marketData,
      connected: state.connected,
      error: state.error
    }))
  );

  const calls = marketData?.calls ?? []
  const puts = marketData?.puts ?? []

  return {
    spot: marketData?.spot ?? 0,
    calls,
    puts,
    connected
  }
}
