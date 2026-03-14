import { useWSStore } from "@/core/ws/wsStore"

export function useDashboardData() {

  // FIX 8: Read from liveMarketData structure instead of individual store keys
  const liveMarketData = useWSStore((s) => s.liveMarketData)
  const spot = useWSStore((s) => s.spot) // Fallback for spot
  const connected = useWSStore((s) => s.connected)

  // Extract data from liveMarketData
  const snapshot = liveMarketData?.snapshot || {}
  const analytics = liveMarketData?.analytics || {}
  const optionChain = liveMarketData?.option_chain || {}
  const candles = liveMarketData?.candles || []
  const aiSignals = liveMarketData?.ai_signals || {}

  // Extract specific metrics
  const spotPrice = snapshot.spot || spot
  const pcr = analytics.pcr || 0
  const totalCallOI = snapshot.total_call_oi || 0
  const totalPutOI = snapshot.total_put_oi || 0

  // Extract option chain strikes and convert to calls/puts arrays
  const strikes = optionChain.strikes || []
  
  // Convert strikes structure to calls and puts arrays for OIHeatmap compatibility
  const calls = (strikes || [])
    .filter((strike: any) => strike.CE && strike.CE.oi > 0)
    .map((strike: any) => ({
      strike: strike.strike,
      ltp: strike.CE.ltp || 0,
      oi: strike.CE.oi || 0,
      volume: strike.CE.volume || 0,
      iv: strike.CE.iv || 0,
      change: strike.CE.change || 0
    }))
  
  const puts = (strikes || [])
    .filter((strike: any) => strike.PE && strike.PE.oi > 0)
    .map((strike: any) => ({
      strike: strike.strike,
      ltp: strike.PE.ltp || 0,
      oi: strike.PE.oi || 0,
      volume: strike.PE.volume || 0,
      iv: strike.PE.iv || 0,
      change: strike.PE.change || 0
    }))

  return {
    spot: spotPrice,
    pcr,
    totalCallOI,
    totalPutOI,
    strikes,
    calls,
    puts,
    snapshot,
    analytics,
    optionChain,
    candles,
    aiSignals,
    connected,
    liveMarketData
  }
}
