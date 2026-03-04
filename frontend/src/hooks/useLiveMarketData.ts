/**
 * useLiveMarketData - READ ONLY hook for live market data.
 * 
 * This hook READS ONLY from wsStore and optionChainStore.
 * It does NOT create WebSocket connections.
 */

import { useState, useEffect, useRef } from "react"
import { useWSStore } from "@/core/ws/wsStore"
import { useOptionChainStore } from "@/core/ws/optionChainStore"
import { throttle } from "@/utils/throttle"

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
  intelligence?: any
}

export function useLiveMarketData(symbol: string, expiry: string | null) {
  const [data, setData] = useState<LiveMarketData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<"loading" | "snapshot" | "live" | "error">("snapshot")

  // READ ONLY from stores
  const { spot, lastUpdate, connected } = useWSStore()
  const { optionChainData, optionChainLastUpdate } = useOptionChainStore()

  // Throttled update function
  const throttledSetData = useRef(
    throttle((transformedData: LiveMarketData) => {
      const safeSpot = Number(transformedData.spot) || 0
      console.log("📊 UI RENDER: spot=", safeSpot, "symbol=", transformedData.symbol)
      setData(transformedData)
      setMode("live")
      setLoading(false)
      setError(null)
    }, 100)
  ).current

  useEffect(() => {
    // Transform store data → UI data
    const transformed: LiveMarketData = {
      symbol,
      spot: spot || optionChainData?.spot || 0,
      timestamp: new Date(lastUpdate || optionChainLastUpdate).toISOString(),
      analytics_enabled: optionChainData?.analytics_enabled,
      available_expiries: [],
      optionChain: optionChainData
        ? {
          symbol: optionChainData.symbol || symbol,
          spot: optionChainData.spot || spot,
          expiry: optionChainData.expiry || expiry || "",
          calls: optionChainData.calls || [],
          puts: optionChainData.puts || []
        }
        : null,
      analytics: optionChainData?.analytics,
      intelligence: optionChainData?.intelligence
    }

    throttledSetData(transformed)
  }, [spot, optionChainData, lastUpdate, optionChainLastUpdate, symbol, expiry])

  useEffect(() => {
    // Handle connection status
    if (!connected && !data) {
      setLoading(false)
      setMode("snapshot")
    } else if (connected && data) {
      setMode("live")
      setLoading(false)
    }
  }, [connected, data])

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
