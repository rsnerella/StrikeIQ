/**
 * useLiveMarketData - READ ONLY hook for live market data.
 * 
 * This hook READS ONLY from wsStore and optionChainStore.
 * It does NOT create WebSocket connections.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useWSStore } from '../core/ws/wsStore';
import { useOptionChainStore } from '../core/ws/optionChainStore';
import { useShallow } from 'zustand/shallow';
import throttle from "lodash/throttle"
import { uiLog } from "@/utils/uiLogger"

export interface LiveMarketData {
  symbol: string
  spot: number
  timestamp: string
  change?: number
  change_percent?: number
  analytics_enabled?: boolean
  available_expiries?: string[]
  optionChain?: {
    symbol: string
    spot: number
    expiry: string
    calls: any[]
    puts: any[]
  } | null
  analytics?: any
  chartAnalysis?: any
  intelligence?: any
}

export function useLiveMarketData(symbol: string, expiry: string | null) {
  const [data, setData] = useState<LiveMarketData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<"loading" | "snapshot" | "live" | "error">("snapshot")

  // Render loop detection
  const renderCountRef = useRef(0)
  renderCountRef.current++

  if (renderCountRef.current > 20) {
    console.warn("⚠️ EXCESSIVE RENDER DETECTED in useLiveMarketData", {
      renderCount: renderCountRef.current,
      symbol,
      expiry
    })
  }

  // READ ONLY from stores with grouped selectors to prevent unnecessary re-renders
  const { spot, lastUpdate, connected, analytics } = useWSStore(
    useShallow(state => ({
      spot: state.spot,
      lastUpdate: state.lastUpdate,
      connected: state.connected,
      analytics: state.analytics,
      chartAnalysis: state.chartAnalysis
    }))
  )
  const { optionChainData, optionChainLastUpdate } = useOptionChainStore()

  // Spot fallback logic
  const effectiveSpot =
    optionChainData?.spot ||
    spot ||
    0

  // Throttled update function - memoized to prevent re-renders
  const throttledSetData = useMemo(() => {
    return throttle(setData, 300)
  }, [])

  useEffect(() => {
    uiLog("COMPONENT MOUNTED", "useLiveMarketData")
    return () => {
      uiLog("COMPONENT UNMOUNTED", "useLiveMarketData")
    }
  }, [])

  useEffect(() => {
    // Transform store data → UI data
    const safeAnalytics = analytics || {}

    // PATCH 1: Prevent symbol mismatch from analytics
    if (analytics?.symbol !== symbol) {
      return
    }

    // PATCH 4: Add defensive null guard
    if (!analytics) return

    if (process.env.NODE_ENV === "development") {
      console.log("🔗 ANALYTICS FROM STORE:", safeAnalytics)
    }

    const transformed: LiveMarketData = {
      symbol,
      spot: effectiveSpot,
      timestamp: new Date(lastUpdate || optionChainLastUpdate).toISOString(),
      analytics_enabled: optionChainData?.analytics_enabled,
      available_expiries: [],
      optionChain: optionChainData
        ? {
          symbol: optionChainData.symbol || symbol,
          spot: optionChainData.spot || effectiveSpot,
          expiry: optionChainData.expiry || expiry || "",
          calls: optionChainData.calls || [],
          puts: optionChainData.puts || []
        }
        : null,
      analytics: safeAnalytics,
      chartAnalysis: useWSStore.getState().chartAnalysis,
      intelligence: {
        // Map analytics to intelligence object for UI components
        bias: {
          ...safeAnalytics?.bias,
          label: safeAnalytics?.bias?.divergence_type === 'bullish' ? 'BULLISH' :
            safeAnalytics?.bias?.divergence_type === 'bearish' ? 'BEARISH' : 'NEUTRAL',
          score: safeAnalytics?.bias?.bias_strength || 0
        },
        pcr: safeAnalytics?.bias?.pcr_value ?? safeAnalytics?.pcr ?? 1.0,
        probability: safeAnalytics?.expected_move,
        volatility_regime: safeAnalytics?.structural?.volatility_regime ?? "UNKNOWN",
        breach_probability: safeAnalytics?.structural?.breach_probability ?? 0,
        expected_move: safeAnalytics?.structural?.expected_move ?? 0,
        gamma_regime: safeAnalytics?.structural?.gamma_regime ?? "neutral",
        support_level: safeAnalytics?.structural?.support_level ?? 0,
        resistance_level: safeAnalytics?.structural?.resistance_level ?? 0,
        intent_score: safeAnalytics?.structural?.intent_score ?? 0,
        oi_velocity: safeAnalytics?.structural?.oi_velocity ?? 0,
        total_oi: safeAnalytics?.structural?.total_oi ?? 0,
        regime: {
          market_regime: 'NORMAL',
          volatility_regime: safeAnalytics?.structural?.volatility_regime ?? "UNKNOWN",
          trend_regime: safeAnalytics?.bias?.divergence_type === 'bullish' ? 'UPTREND' :
            (safeAnalytics?.bias?.divergence_type === 'bearish' ? 'DOWNTREND' : 'SIDEWAYS'),
          confidence: 85.0
        },
        gamma: {
          net_gamma: safeAnalytics?.structural?.net_gamma ?? 0,
          gamma_flip: safeAnalytics?.structural?.gamma_flip_level ?? 0,
          dealer_gamma: safeAnalytics?.structural?.gamma_regime ?? "NEUTRAL",
          gamma_exposure: safeAnalytics?.structural?.net_gamma ?? 0
        },
        trade_suggestion: safeAnalytics?.trade_suggestion || safeAnalytics?.trade_setup,
        // Keep existing optionChain intelligence if available
        ...optionChainData?.intelligence
      }
    }

    if (process.env.NODE_ENV === "development") {
      console.log("🧠 INTELLIGENCE MAPPING:", transformed.intelligence)
    }

    throttledSetData(transformed)
  }, [spot, optionChainData, lastUpdate, optionChainLastUpdate, analytics, symbol, expiry])

  useEffect(() => {
    // Handle connection status
    if (!connected && !data) {
      setLoading(false)
      setMode("snapshot")
    } else if (connected && data) {
      setMode("live")
      setLoading(false)
    }
  }, [connected])

  // Cleanup throttle on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      throttledSetData.cancel()
    }
  }, [throttledSetData])

  return {
    data,
    loading,
    error,
    mode,
    connected,
    symbol,
    lastUpdate: data?.timestamp || new Date().toISOString(),
    availableExpiries: []
  }
}
