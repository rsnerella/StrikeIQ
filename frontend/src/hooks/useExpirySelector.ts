/**
 * useExpirySelector - PRODUCTION STABILITY PATCH v2
 * - Normalizes API response (handles both flat array and { expiries: [] } shapes)
 * - Auto-selects nearest future expiry on load
 * - Prevents duplicate fetches with ref guard
 */

import { useState, useEffect, useRef } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import { useOptionChainStore } from '@/core/ws/optionChainStore';

export const useExpirySelector = () => {
  const [expiryList, setExpiryList] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string | null>(null);
  const [loadingExpiries, setLoadingExpiries] = useState(false);
  const [expiryError, setExpiryError] = useState<string | null>(null);

  const currentSymbol = useMarketStore(state => state.currentSymbol);
  const { optionChainConnected } = useOptionChainStore();

  const lastFetchedSymbolRef = useRef<string | null>(null);

  useEffect(() => {

    async function loadExpiries() {

      if (lastFetchedSymbolRef.current === currentSymbol) return;

      setLoadingExpiries(true);
      setExpiryError(null);

      try {
        const res = await fetch(`/api/v1/market/expiries?symbol=${currentSymbol}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const raw = await res.json();

        // Normalize: handle { expiries: [] }, { data: [] }, or flat []
        let list: string[] = [];
        if (Array.isArray(raw)) {
          list = raw;
        } else if (Array.isArray(raw?.expiries)) {
          list = raw.expiries;
        } else if (Array.isArray(raw?.data)) {
          list = raw.data;
        }

        setExpiryList(list);

        // Auto-select nearest future expiry
        if (list.length > 0 && !selectedExpiry) {
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const nearest = list
            .map(e => ({ str: e, date: new Date(e) }))
            .filter(({ date }) => date >= today)
            .sort((a, b) => a.date.getTime() - b.date.getTime())[0];

          setSelectedExpiry(nearest?.str || list[0]);
        }

        lastFetchedSymbolRef.current = currentSymbol;

      } catch (err: any) {
        console.warn('Expiry fetch failed:', err?.message);
        setExpiryError(err?.message || 'Failed to load expiries');
      } finally {
        setLoadingExpiries(false);
      }
    }

    loadExpiries();

  }, [currentSymbol]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExpiryChange = (expiry: string) => {
    setSelectedExpiry(expiry);
    localStorage.setItem('selectedExpiry', expiry);
  };

  return {
    expiryList,
    selectedExpiry,
    loadingExpiries,
    expiryError,
    handleExpiryChange,
    optionChainConnected,
    currentSymbol
  };
};
