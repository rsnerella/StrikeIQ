/**
 * WebSocket Zustand Store - READ ONLY
 * 
 * This store reads WebSocket state from the singleton service.
 * All components must read from this store.
 */

import { create } from "zustand"
import { uiLog } from "@/utils/uiLogger"
import { useMarketContextStore } from "@/stores/marketContextStore"

interface WSStore {
  connected: boolean
  marketOpen: boolean | null
  marketStatus: "OPEN" | "PREOPEN" | "CLOSED" | "UNKNOWN"
  lastMessage: any | null
  error: string | null
  spot: number
  spotPrice: number
  liveSpot: number
  currentSpot: number
  atmStrike: number
  lastUpdate: number
  marketData: any
  optionChainSnapshot: any
  liveData: any
  wsLiveData: any
  analytics: any
  liveMarketData: any
  aiIntelligence: any
  dataQuality: any
  aiReady: boolean
  advancedStrategies: any
  signalScore: any
  chartAnalysis: any
  aiPrediction: any
  candles: any[]
  _lastChainUpdate: number
  _THROTTLE_MS: number
  handleMessage: (message: any) => void
  handleAnalytics: (analyticsPayload: any) => void
  setConnected: (v: boolean) => void
  setMarketOpen: (v: boolean | null) => void
  setMarketStatus: (v: "OPEN" | "PREOPEN" | "CLOSED" | "UNKNOWN") => void
  setLastMessage: (msg: any) => void
  setMarketData: (data: any) => void
  setError: (error: string | null) => void
}

export const useWSStore = create<WSStore>((set, get) => ({

  connected: false,
  marketOpen: null,
  marketStatus: "UNKNOWN",
  lastMessage: null,
  error: null,
  spot: 0,
  spotPrice: 0,
  liveSpot: 0,
  currentSpot: 0,
  atmStrike: 0,
  marketData: null,
  optionChainSnapshot: null,
  liveData: null,
  wsLiveData: null,
  analytics: null,
  liveMarketData: null,
  aiIntelligence: null,
  dataQuality: null,
  aiReady: false,
  advancedStrategies: null,
  signalScore: null,
  chartAnalysis: null,
  aiPrediction: null,
  candles: [],
  lastUpdate: 0,
  _lastChainUpdate: 0,
  _THROTTLE_MS: 50,

  handleMessage: (message: any) => {
    if (!message) return

    // STEP 3: DEBUG LOG
    console.log("WS MESSAGE PROCESSED", message);

    // Institutional Market Update (Elite Engine)
    if (message.type === "market_update") {
      const marketStore = useMarketContextStore.getState()
      const selectedSymbol = marketStore?.symbol || 'NIFTY'
      
      if (message.symbol !== selectedSymbol) return

      set({
        spot: message.spotPrice,
        spotPrice: message.spotPrice,
        liveSpot: message.liveSpot,
        currentSpot: message.currentSpot,
        atmStrike: message.atmStrike,
        aiIntelligence: message.aiIntelligence,
        dataQuality: message.dataQuality,
        aiReady: message.aiReady,
        lastUpdate: Date.now(),
        error: null
      })
      return
    }

    // Market status update
    if (message.type === "market_status" && message.market_open !== undefined) {
      set({
        marketOpen: message.market_open,
        marketStatus: message.status || (message.market_open ? "OPEN" : "CLOSED"),
        error: null
      })
      return
    }

    // AI Prediction
    if (message.type === "ai_prediction") {
      set({ aiPrediction: message, error: null })
      return
    }

    // INDEX TICK — backend broadcasts this for NIFTY/BANKNIFTY spot price
    if (message.type === "index_tick" && message.data) {
      const tick = message.data
      
      // DEBUG: Log index tick details
      console.log("INDEX TICK RECEIVED", {
        messageSymbol: message.symbol,
        tickSymbol: tick.symbol,
        ltp: tick.ltp
      })
      
      // PATCH 2: Filter WebSocket index ticks by selected symbol
      const marketStore = useMarketContextStore.getState()
      const selectedSymbol = marketStore?.symbol || 'NIFTY'
      
      // Use message.symbol instead of tick.symbol for filtering
      if (message.symbol !== selectedSymbol) {
        console.log("INDEX TICK FILTERED", {
          messageSymbol: message.symbol,
          selectedSymbol
        })
        return
      }
      
      set({
        spot: tick.ltp ?? 0,
        spotPrice: tick.ltp ?? 0,
        liveSpot: tick.ltp ?? 0,
        currentSpot: tick.ltp ?? 0,
        lastUpdate: Date.now(),
        liveData: { ...tick, symbol: message.symbol, spot_price: tick.ltp },
        wsLiveData: { ...tick, symbol: message.symbol, spot_price: tick.ltp },
        error: null
      })
      return
    }

    // OPTION TICK — individual option price updates
    if (message.type === "option_tick" && message.data) {
      const tick = message.data
      
      // PERFORMANCE: Filter by selected symbol to prevent unnecessary updates
      const marketStore = useMarketContextStore.getState()
      const selectedSymbol = marketStore?.symbol || 'NIFTY'
      
      if (message.symbol !== selectedSymbol) {
        console.log("OPTION TICK FILTERED", {
          messageSymbol: message.symbol,
          selectedSymbol
        })
        return
      }
      
      // DEBUG: Log option tick details
      console.log("OPTION TICK RECEIVED", {
        symbol: message.symbol,
        strike: tick.strike,
        right: tick.right,
        ltp: tick.ltp,
        oi: tick.oi
      })
      
      // Update option chain with individual tick data
      const currentData = get().marketData || {}
      
      // PERFORMANCE: Avoid expensive spread on large objects
      // Only update the specific strike that changed
      const strikeKey = tick.strike
      const optionType = tick.right === 'CE' ? 'CE' : 'PE'
      
      // Check if data actually changed to avoid unnecessary updates
      const currentOption = currentData[strikeKey]?.[optionType]
      if (currentOption && 
          currentOption.ltp === tick.ltp && 
          currentOption.oi === (tick.oi || 0) && 
          currentOption.volume === (tick.volume || 0)) {
        // No change, skip update
        return
      }
      
      // Create new object with only the updated strike
      const updatedData = {
        ...currentData,
        [strikeKey]: {
          ...currentData[strikeKey],
          [optionType]: {
            strike: tick.strike,
            right: tick.right,
            ltp: tick.ltp,
            oi: tick.oi || 0,
            volume: tick.volume || 0
          }
        }
      }
      
      set({
        marketData: updatedData,
        lastUpdate: Date.now(),
        error: null
      })
      return
    }

    // OPTION CHAIN UPDATE — backend broadcasts this every 500ms from option_chain_builder
    if (message.type === "option_chain_update" && message.data) {
      const now = Date.now()
      const store = get()

      // PERFORMANCE: Filter by selected symbol to prevent unnecessary updates
      const marketStore = useMarketContextStore.getState()
      const selectedSymbol = marketStore?.symbol || 'NIFTY'
      
      if (message.symbol !== selectedSymbol) {
        console.log("OPTION CHAIN UPDATE FILTERED", {
          messageSymbol: message.symbol,
          selectedSymbol
        })
        return
      }

      // DEBUG: Log option chain update details
      console.log("OPTION CHAIN UPDATE RECEIVED", {
        symbol: message.symbol,
        spot: message.spot,
        strikesCount: message.strikesCount,
        timestamp: message.timestamp
      })

      if (now - store._lastChainUpdate < store._THROTTLE_MS) {
        console.log("OPTION CHAIN UPDATE THROTTLED")
        return
      }

      // Update market context if symbol changed
      const marketContextStore = useMarketContextStore.getState()
      if (message.symbol !== marketContextStore.symbol) {
        marketContextStore.setSymbol(message.symbol)
        console.log("SYMBOL CONTEXT UPDATED", message.symbol)
      }
      if (message.expiry && message.expiry !== marketContextStore.expiry) {
        marketContextStore.setExpiry(message.expiry)
        console.log("EXPIRY CONTEXT UPDATED", message.expiry)
      }

      set({
        spot: message.spot ?? 0,
        marketData: message.data,
        optionChainSnapshot: message.data,
        lastUpdate: now,
        _lastChainUpdate: now,
        error: null
      })
      return
    }

    // HEATMAP UPDATE — backend broadcasts this every 3s from oi_heatmap_engine
    if (message.type === "heatmap_update") {
      // heatmap data is forwarded via optionChainSnapshot for OIHeatmap component
      const data = message.data
      if (data) {
        set({ marketData: { ...get().marketData, heatmap: data }, error: null })
      }
      return
    }

    // Market tick (legacy format)
    if (message.type === "market_tick" && message.data) {
      const tick = message.data
      set({
        spot: tick.ltp ?? 0,
        lastUpdate: Date.now(),
        liveData: tick,
        wsLiveData: tick,
        error: null
      })
      return
    }

    // Market data with spot price (legacy format)
    if (message.type === "market_data" && message.spot !== undefined) {
      set({
        spot: message.spot,
        lastUpdate: Date.now(),
        marketData: message,
        liveData: message,
        wsLiveData: message,
        error: null
      })
      return
    }

    // Market data with direct ltp (fallback)
    if (message.type === "market_data" && message.ltp !== undefined) {
      set({
        spot: message.ltp,
        lastUpdate: Date.now(),
        liveData: message,
        wsLiveData: message,
        error: null
      })
      return
    }

    // STEP 1: HANDLE TICK MESSAGE
    if (message.type === "tick") {
      // ADD SAFETY
      if (!message.ltp) {
        console.warn("Tick missing LTP", message)
        return
      }
      
      set({
        liveData: {
          spot_price: message.ltp,
          timestamp: Date.now()
        }
      })
      return
    }

    // STEP 2: HANDLE SNAPSHOT MESSAGE
    if (message.type === "snapshot") {
      set({
        optionChainSnapshot: message.data
      })
      return
    }

    // Chain update (legacy format)
    if (message.type === "chain_update" && message.data) {
      const now = Date.now()
      const store = get()

      if (now - store._lastChainUpdate < store._THROTTLE_MS) {
        return
      }

      const data = message.data
      set({
        spot: data.spot ?? 0,
        marketData: data,
        optionChainSnapshot: data,
        lastUpdate: now,
        _lastChainUpdate: now,
        error: null
      })
      return
    }

    // ANALYTICS UPDATE — from analytics_broadcaster
    if (message.type === "analytics_update") {
      get().handleAnalytics(message);
      return
    }

    // INTELLIGENCE UPDATE — from LiveStructuralEngine
    if (message.type === "intelligence_update" && message.intelligence) {
      set({
        analytics: { ...get().analytics, intelligence: message.intelligence },
        lastUpdate: Date.now(),
        error: null
      })
      return
    }

    // METRICS UPDATE — fallback from LiveStructuralEngine when AI pipeline fails
    if (message.type === "metrics_update") {
      set({
        spot: message.spot ?? get().spot,
        lastUpdate: Date.now(),
        error: null
      })
      return
    }

    // AI SIGNAL — from LiveStructuralEngine signal generator
    if (message.type === "ai_signal") {
      set({
        analytics: { ...get().analytics, ai_signals: message.signals },
        lastUpdate: Date.now(),
        error: null
      })
      return
    }

    // Raw option chain
    if (message.calls && message.puts) {
      const now = Date.now()
      const store = get()

      if (now - store._lastChainUpdate < store._THROTTLE_MS) {
        return
      }

      set({
        spot: message.spot ?? 0,
        marketData: message,
        optionChainSnapshot: message,
        lastUpdate: now,
        _lastChainUpdate: now,
        error: null
      })
      return
    }

    // ADVANCED STRATEGIES — Step 14 (SMC, ICT, CRT, MSNR)
    if (message.type === "advanced_strategies") {
      // ADVANCED STRATEGIES — Step 14: only update if symbol or content changed
      const prevAdv = get().advancedStrategies
      if (
        !prevAdv ||
        prevAdv.symbol !== message.symbol ||
        prevAdv.timestamp !== message.timestamp
      ) {
        set({
          advancedStrategies: message,
          analytics: { ...get().analytics, advanced_strategies: message },
          lastUpdate: Date.now(),
          error: null
        })
      }
      return
    }

    // SIGNAL SCORE — Step 15: only update if score meaningfully changed
    if (message.type === "signal_score") {
      const prevScore = get().signalScore
      const scoreDelta = Math.abs((prevScore?.score ?? -1) - (message.score ?? 0))
      if (
        !prevScore ||
        prevScore.symbol !== message.symbol ||
        scoreDelta >= 0.5 ||
        prevScore.bias !== message.bias
      ) {
        set({
          signalScore: message,
          analytics: { ...get().analytics, signal_score: message },
          lastUpdate: Date.now(),
          error: null
        })
      }
      return
    }

    // CHART ANALYSIS — from chart_signal_engine
    if (message.type === "chart_analysis") {
      const prev = get().chartAnalysis
      // Dedup: only update if timestamp or signal changed
      if (!prev || prev.timestamp !== message.timestamp || prev.signal !== message.signal) {
        set({
          chartAnalysis: message,
          lastUpdate: Date.now(),
          error: null
        })
      }
      return
    }

    // CANDLE DATA — from candle_builder
    if (message.type === "candle_data") {
      set({
        candles: message.candles || [],
        lastUpdate: Date.now(),
        error: null
      })
      return
    }

    // Silently ignore known server ack/control messages
    const silenced = ['subscribed', 'unsubscribed', 'pong', 'ping', 'ack']
    if (silenced.includes(message.type)) return

    // Unknown — log in dev only, do not pollute error state
    if (process.env.NODE_ENV === "development") {
      console.warn("⚠️ WS UNKNOWN MESSAGE TYPE:", message.type)
    }
  },

  handleAnalytics: (payload) => {
    if (!payload) return

    // PATCH 1: Prevent symbol mismatch from analytics
    const marketStore = useMarketContextStore.getState()
    const selectedSymbol = marketStore?.symbol || 'NIFTY'
    
    if (payload.symbol && payload.symbol !== selectedSymbol) {
      return
    }

    // P5: skip set if analytics timestamp hasn't changed (prevents render on identical payload)
    const prev = get().analytics
    if (prev?.timestamp && prev.timestamp === payload.timestamp) return

    if (process.env.NODE_ENV === "development") {
      console.log("Analytics stored in Zustand")
    }

    // FIX 7: Update liveMarketData structure for frontend widgets
    const renderableData = payload.analytics 
      ? { ...payload.analytics, symbol: payload.symbol, _timestamp: payload.timestamp } 
      : { ...payload };
    
    set({
      analytics: renderableData,
      // FIX 7: Update liveMarketData with complete structure
      liveMarketData: {
        snapshot: renderableData.snapshot,
        analytics: renderableData.analytics,
        option_chain: renderableData.option_chain,
        candles: renderableData.candles,
        ai_signals: renderableData.ai_signals,
        timestamp: payload.timestamp
      },
      // Phase 8: Extract spot and chain from bundle for full sync
      spot: renderableData.snapshot?.spot || get().spot,
      optionChainSnapshot: renderableData.option_chain || get().optionChainSnapshot,
      lastUpdate: Date.now(),
      connected: true,
      error: null
    })
  },

  setConnected: (v) => {
    uiLog("STORE UPDATE", {
      store: "wsStore",
      action: "setConnected",
      connected: v
    })
    set({ connected: v })
  },
  setMarketOpen: (v) => {
    uiLog("STORE UPDATE", {
      store: "wsStore",
      action: "setMarketOpen",
      marketOpen: v
    })
    set({
      marketOpen: v,
      marketStatus: v === true ? "OPEN" : v === false ? "CLOSED" : "UNKNOWN"
    })
  },
  setMarketStatus: (v) => {
    uiLog("STORE UPDATE", {
      store: "wsStore",
      action: "setMarketStatus",
      marketStatus: v
    })
    set({
      marketStatus: v,
      marketOpen: v === "OPEN"
    })
  },
  setLastMessage: (msg) => {
    uiLog("STORE UPDATE", {
      store: "wsStore",
      action: "setLastMessage",
      messageType: msg?.type
    })
    set({ lastMessage: msg })
  },
  setMarketData: (data) => {
    uiLog("STORE UPDATE", {
      store: "wsStore",
      action: "setMarketData",
      spot: data?.spot,
      symbol: data?.symbol
    })
    set({ marketData: data })
  },
  setError: (error) => {
    uiLog("STORE UPDATE", {
      store: "wsStore",
      action: "setError",
      error
    })
    set({ error })
  }
}))
