/**
 * useExpirySelector - PRODUCTION STABILITY PATCH v2
 * - Normalizes API response (handles both flat array and { expiries: [] } shapes)
 * - Auto-selects nearest future expiry on load
 * - Prevents duplicate fetches with ref guard
 */

import { useState, useEffect, useRef } from 'react';
import { useMarketContextStore } from '@/stores/marketContextStore';
import { useOptionChainStore } from '@/core/ws/optionChainStore';
import { resubscribeMarketWS } from '@/services/wsService';
import api from '@/api/client';
import { API_URL } from '@/api/client';

export const useExpirySelector = () => {
  const [expiryList, setExpiryList] = useState<string[]>([]);
  const [loadingExpiries, setLoadingExpiries] = useState(false);
  const [expiryError, setExpiryError] = useState<string | null>(null);

  const currentSymbol = useMarketContextStore(state => state.symbol);
  const selectedExpiry = useMarketContextStore(state => state.expiry);
  const setExpiry = useMarketContextStore(state => state.setExpiry);

  const { optionChainConnected } = useOptionChainStore();

  const lastFetchedSymbolRef = useRef<string | null>(null);

  useEffect(() => {

    async function loadExpiries() {

      if (lastFetchedSymbolRef.current === currentSymbol) return;

      setLoadingExpiries(true);
      setExpiryError(null);

      try {
        const response = await api.get(`/api/v1/market/expiries?symbol=${currentSymbol}`);
        const raw = response.data;
        if (!raw) {
          console.warn('Backend not available - no data received');
          setExpiryError('Backend offline - expiry data unavailable');
          return;
        }

        // Normalize: handle { expiries: [] }, { data: [] }, or flat []
        let list: string[] = [];
        if (Array.isArray(raw)) {
          list = raw;
        } else if (Array.isArray(raw?.expiries)) {
          list = raw.expiries;
        } else if (Array.isArray(raw?.data)) {
          list = raw.data;
        }

        setExpiryList(prev => {
          if (JSON.stringify(prev) === JSON.stringify(list)) return prev;
          return list;
        });

        // Auto-select nearest future expiry
        if (list.length > 0) {
          const stored = localStorage.getItem('selectedExpiry');
          const today = new Date();
          today.setHours(0, 0, 0, 0);

          let newExpiry = list[0];
          
          if (stored && list.includes(stored)) {
            newExpiry = stored;
          } else {
            const nearest = list
              .map(e => ({ str: e, date: new Date(e) }))
              .filter(({ date }) => date >= today)
              .sort((a, b) => a.date.getTime() - b.date.getTime())[0];
            newExpiry = nearest?.str || list[0];
          }

          if (selectedExpiry !== newExpiry) {
            setExpiry(newExpiry);
            localStorage.setItem('selectedExpiry', newExpiry);
            resubscribeMarketWS(currentSymbol, newExpiry);
          }
        }

        lastFetchedSymbolRef.current = currentSymbol;

      } catch (err: any) {
        console.warn('Expiry fetch failed:', err?.message);
        
        // Handle backend offline scenario specifically
        if (err?.message?.includes('Backend not available')) {
          setExpiryError('Backend offline - expiry data unavailable');
        } else {
          setExpiryError(err?.message || 'Failed to load expiries');
        }
      } finally {
        setLoadingExpiries(false);
      }
    }

    loadExpiries();

  }, [currentSymbol]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExpiryChange = (expiry: string) => {
    setExpiry(expiry);
    localStorage.setItem('selectedExpiry', expiry);
    resubscribeMarketWS(currentSymbol, expiry);
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
