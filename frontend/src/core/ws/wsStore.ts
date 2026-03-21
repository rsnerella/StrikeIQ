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
  atm: number
  symbol?: string
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
  
  // 🔥 ADD PERFORMANCE DATA
  performance: any
  analytics_full: any
  strategy_weights: any
  
  _lastChainUpdate: number
  _lastHeatmapUpdate: number
  _THROTTLE_MS: number
  
  // NEW: Separated AI analysis and trade setup fields
  aiAnalysis: any | null
  tradeSetup: any | null
  
  // Master Contract v5.0 Extended Fields
  pcr: number
  callWall: number
  putWall: number
  maxPain: number
  gexFlip: number
  netGex: number
  ivAtm: number
  ivPercentile: number
  calls: Record<string, any>
  puts: Record<string, any>
  optionChain: any
  regime: string
  bias: string
  biasStrength: number
  keyLevels: any
  gammaAnalysis: any
  volState: any
  technicals: any
  rsi: number
  summary: string
  tradePlan: any
  earlyWarnings: any[]
  newsAlerts: any[]
  paperTrading: any
  heatmapData: any
  oiHeatmap: any
  oi_heatmap: any
  
  handleMessage: (message: any) => void
  handleAnalytics: (analyticsPayload: any) => void
  setConnected: (v: boolean) => void
  setMarketOpen: (v: boolean | null) => void
  setMarketStatus: (v: "OPEN" | "PREOPEN" | "CLOSED" | "UNKNOWN") => void
  setLastMessage: (msg: any) => void
  setMarketData: (data: any) => void
  setError: (error: string | null) => void
  
  // NEW: Methods for separated fields
  setAIAnalysis: (analysis: any) => void
  setTradeSetup: (trade: any) => void
}

export const useWSStore = create<WSStore>((set, get) =>({

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
  atm: 0,
  marketData: null,
  optionChainSnapshot: null,
  liveData: null,
  wsLiveData: null,
  analytics: {},
  liveMarketData: null,
  aiIntelligence: null,
  dataQuality: null,
  aiReady: false,
  advancedStrategies: null,
  signalScore: null,
  chartAnalysis: null,
  aiPrediction: null,
  candles: [],
  
  // 🔥 ADD PERFORMANCE DATA DEFAULTS
  performance: null,
  analytics_full: null,
  strategy_weights: null,
  
  lastUpdate: 0,
  _lastChainUpdate: 0,
  _lastHeatmapUpdate: 0,
  _THROTTLE_MS: 50,

  // NEW: Separated AI analysis and trade setup fields
  aiAnalysis: null,
  tradeSetup: null,

  // Master Contract v5.0 Extended State
  pcr: 0,
  callWall: 0,
  putWall: 0,
  maxPain: 0,
  gexFlip: 0,
  netGex: 0,
  ivAtm: 0,
  ivPercentile: 0,
  calls: {},
  puts: {},
  optionChain: null,
  regime: 'RANGING',
  bias: 'NEUTRAL',
  biasStrength: 0,
  keyLevels: {},
  gammaAnalysis: {},
  volState: {},
  technicals: {},
  rsi: 0,
  summary: '',
  tradePlan: null,
  earlyWarnings: [],
  newsAlerts: [],
  paperTrading: null,
  heatmapData: null,
  oiHeatmap: null,
  oi_heatmap: null,

  handleMessage: (message: any) => {
    if (!message) return

    // STEP 4: VERIFY STORE ENTRY
    console.log("[STORE HANDLE ENTRY]", message.type)
    console.log("[ZUSTAND SET]", message.analytics)

    // STEP 5: RAW WS LOGGING
    if (message.type !== 'pong' && message.type !== 'ping') {
      console.log('RAW WS MESSAGE:', message.type, Object.keys(message));
    }
    
    // 🔥 TEMP DEBUG LOG (REMOVE AFTER 2-3 MINS)
    if (message.type === 'analytics_update' || message.type === 'market_update') {
      console.log('[WS DATA]', message);
    }

    const marketContextStore = useMarketContextStore.getState();
    const selectedSymbol = marketContextStore?.symbol || 'NIFTY';

    switch (message.type) {
      case 'market_update':
      case 'analytics_update': {
        const now = Date.now()
        if (now - get()._lastChainUpdate < get()._THROTTLE_MS) {
          return
        }
        const p = message;
        if (p.symbol && p.symbol !== selectedSymbol) return;

        // Extract spot from any alias
        const spotRaw = p.spot ?? p.spotPrice ?? p.liveSpot ?? p.currentSpot ?? 0;
        const spot = typeof spotRaw === 'number' && spotRaw > 0 ? spotRaw : 0;

        // Log every message so we can verify it's arriving
        if (process.env.NODE_ENV === 'development') {
          console.log(
            '[wsStore] market_update |',
            'spot=', spot,
            'pcr=', p.option_chain?.pcr,
            'calls=', Object.keys(p.option_chain?.calls || {}).length,
            'ai_ready=', p.ai_ready
          );
        }

        set((prev) => ({
          // SPOT — all aliases
          spot: spot > 0 ? spot : prev.spot,
          spotPrice:    spot > 0 ? spot : prev.spotPrice,
          liveSpot:     spot > 0 ? spot : prev.liveSpot,
          currentSpot:  spot > 0 ? spot : prev.currentSpot,

          // Core
          atm:          p.atm       ?? prev.atm,
          symbol:       p.symbol    ?? prev.symbol,
          lastUpdate:   p.timestamp ?? Date.now(),
          aiReady:      p.ai_ready  ?? p.aiReady ?? prev.aiReady,

          // Option chain fields
          pcr:          p.option_chain?.pcr           ?? prev.pcr,
          callWall:     p.option_chain?.call_wall      ?? prev.callWall,
          putWall:      p.option_chain?.put_wall       ?? prev.putWall,
          maxPain:      p.option_chain?.max_pain       ?? prev.maxPain,
          gexFlip:      p.option_chain?.gex_flip       ?? prev.gexFlip,
          netGex:       p.option_chain?.net_gex        ?? prev.netGex,
          ivAtm:        p.option_chain?.iv_atm         ?? prev.ivAtm,
          ivPercentile: p.option_chain?.iv_percentile  ?? prev.ivPercentile,
          calls: {
            ...(prev.calls || {}),
            ...(p.option_chain?.calls || {})
          },

          puts: {
            ...(prev.puts || {}),
            ...(p.option_chain?.puts || {})
          },
          optionChain:  p.option_chain                 ?? prev.optionChain,

          // AI analysis — accept both key names
          regime:        (p.market_analysis ?? p.aiIntelligence)?.regime          ?? prev.regime,
          bias:          (p.market_analysis ?? p.aiIntelligence)?.bias            ?? prev.bias,
          biasStrength:  (p.market_analysis ?? p.aiIntelligence)?.bias_strength   ?? prev.biasStrength,
          keyLevels:     (p.market_analysis ?? p.aiIntelligence)?.key_levels      ?? prev.keyLevels,
          gammaAnalysis: (p.market_analysis ?? p.aiIntelligence)?.gamma_analysis  ?? prev.gammaAnalysis,
          volState:      (p.market_analysis ?? p.aiIntelligence)?.volatility_state ?? prev.volState,
          technicals:    (p.market_analysis ?? p.aiIntelligence)?.technical_state  ?? prev.technicals,
          summary:       (p.market_analysis ?? p.aiIntelligence)?.summary          ?? prev.summary,

          // Plans and alerts
          tradePlan:     p.trade_plan     ?? prev.tradePlan,
          earlyWarnings: Array.isArray(p.early_warnings) ? p.early_warnings : prev.earlyWarnings ?? [],
          newsAlerts:    Array.isArray(p.news_alerts)    ? p.news_alerts    : prev.newsAlerts    ?? [],
          paperTrading:  p.paper_trading  ?? prev.paperTrading,

          // Data quality
          dataQuality: {
            hasSpot:    spot > 0,
            hasOi:      (p.option_chain?.call_wall ?? 0) > 0,
            hasGreeks:  (p.option_chain?.iv_atm    ?? 0) > 0,
            aiReady:    p.ai_ready ?? false,
            lastUpdate: Date.now(),
            source:     spot > 0 ? 'live' : 'rest_poller',
          },
          
          // 🔥 ADD PERFORMANCE DATA
          performance: p.performance ?? prev.performance ?? {
            total_trades: 0,
            wins: 0,
            losses: 0,
            win_rate: 0,
            total_pnl: 0
          },
          analytics_full: p.analytics_full ?? prev.analytics_full ?? {
            equity_curve: [],
            max_drawdown: 0,
            strategy_stats: {},
            current_equity: 0,
            peak_equity: 0
          },
          strategy_weights: p.strategy_weights ?? prev.strategy_weights ?? {
            "TREND": 1.0,
            "REVERSAL": 1.0,
            "WEAK_TREND": 0.5,
            "RANGE": 1.0,
            "NONE": 0.0
          },
          
          _lastChainUpdate: now
        }));
        break;
      }

      case 'analytics_update': {
        const a = message.analytics || {}
        const spot = a.spot || a.spotPrice || message.spot || 0

        console.log("[WS FINAL ANALYTICS INCOMING]", a)

        set((prev) => {
          console.log("[WS FINAL ANALYTICS AFTER MERGE]", {
            incoming: a,
            previous: prev.analytics,
            merged: {
              ...prev.analytics,
              ...a
            }
          })

          return {
            spotPrice:    spot > 0 ? spot : prev.spotPrice,
            liveSpot:     spot > 0 ? spot : prev.liveSpot,
            currentSpot:  spot > 0 ? spot : prev.currentSpot,
            lastUpdate:   message.timestamp || Date.now(),
            aiReady:      true,

            analytics: {
              ...prev.analytics,
              ...a,

              strategy:
                a.strategy !== undefined
                  ? a.strategy
                  : prev.analytics?.strategy ?? 'NO_TRADE',

              confidence:
                a.confidence !== undefined
                  ? a.confidence
                  : prev.analytics?.confidence ?? null,

              execution:
                a.execution !== undefined
                  ? a.execution
                  : prev.analytics?.execution ?? {},

              metadata: a.metadata
                ? {
                    ...prev.analytics?.metadata,
                    ...a.metadata
                  }
                : prev.analytics?.metadata ?? {}
            },

            // Map from analytics object
            regime:        a.regime         || a.market_regime   || prev.regime        || 'RANGING',
            bias:          a.bias           || a.market_bias     || prev.bias          || 'NEUTRAL',
            biasStrength:  a.bias_strength  || a.confidence      || prev.biasStrength  || 0,
            keyLevels:     a.key_levels     || a.levels          || prev.keyLevels     || {},
            volState:      a.volatility_state || a.volatility    || prev.volState      || {},
            technicals:    a.technical_state  || a.technicals    || prev.technicals    || {},
            summary:       a.summary        || prev.summary      || '',
            tradePlan:     a.trade_plan     || a.signal          || prev.tradePlan     || null,
            earlyWarnings: Array.isArray(a.early_warnings) ? a.early_warnings :
                           Array.isArray(a.warnings)       ? a.warnings       :
                           prev.earlyWarnings || [],
          }
        });
        break;
      }

      case 'option_chain_update': {
        if (message.symbol === selectedSymbol) {
          const now = Date.now()
          const lastChainUpdate = get()._lastChainUpdate || 0

          // Only update option chain every 500ms maximum
          if (now - lastChainUpdate < 500) break

          const p = message
          const spot = p.spot || 0

          // Log to verify data is arriving
          if (process.env.NODE_ENV === 'development') {
            const callCount = Object.keys(p.calls || {}).length
            console.log(
              '[wsStore] option_chain_update |',
              'calls=', callCount,
              'pcr=', p.pcr,
              'atm=', p.atm
            )
          }

          set((prev) => ({
            spotPrice:    spot > 0 ? spot : prev.spotPrice,
            liveSpot:     spot > 0 ? spot : prev.liveSpot,
            currentSpot:  spot > 0 ? spot : prev.currentSpot,
            atm:          p.atm    || prev.atm,
            lastUpdate:   p.timestamp || Date.now(),

            pcr:          p.pcr    || prev.pcr,
            calls:        p.calls  || prev.calls || {},
            puts:         p.puts   || prev.puts  || {},

            // Nested optionChain object
            optionChain: {
              ...(prev.optionChain || {}),
              calls:   p.calls || {},
              puts:    p.puts  || {},
              pcr:     p.pcr   ?? prev.optionChain?.pcr ?? 0,
              atm:     p.atm   ?? prev.optionChain?.atm ?? 0,
              spot:    (spot || prev.optionChain?.spot) ?? 0,
              strikes: p.strikesCount ?? 0,
            },

            // Also write to chainData in case any component uses it
            chainData: {
              calls: p.calls || {},
              puts:  p.puts  || {},
              pcr:   (p.pcr ?? 0),
              atm:   (p.atm ?? 0),
            },

            // Data quality
            dataQuality: {
              ...(prev.dataQuality || {}),
              hasOi:      (p.strikesCount || 0) > 0,
              lastUpdate: Date.now(),
            },

            _lastChainUpdate: now
          }));
        }
        break;
      }

      case 'market_status': {
        if (message.market_open !== undefined) {
          set({
            marketOpen: message.market_open,
            marketStatus: message.status || (message.market_open ? "OPEN" : "CLOSED"),
            error: null
          });
        }
        break;
      }

      case 'ai_prediction':
        set({ aiPrediction: message, error: null });
        break;

      case 'index_tick': {
        const tick = message.data;
        if (message.symbol === selectedSymbol && tick) {
          set({
            spot: tick.ltp ?? 0,
            spotPrice: tick.ltp ?? 0,
            liveSpot: tick.ltp ?? 0,
            currentSpot: tick.ltp ?? 0,
            lastUpdate: Date.now(),
            liveData: { ...tick, symbol: message.symbol, spot_price: tick.ltp },
            wsLiveData: { ...tick, symbol: message.symbol, spot_price: tick.ltp },
            error: null
          });
        }
        break;
      }

      case 'option_tick': {
        const tick = message.data;
        if (message.symbol === selectedSymbol && tick) {
          const currentData = get().marketData || {};
          const strikeKey = tick.strike;
          const optionType = tick.right === 'CE' ? 'CE' : 'PE';
          
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
          };
          
          set({
            marketData: updatedData,
            lastUpdate: Date.now(),
            error: null
          });
        }
        break;
      }

      case 'heatmap_update': {
        const now = Date.now()
        const lastHeatmap = get()._lastHeatmapUpdate || 0

        if (now - lastHeatmap < 1000) break  // max once per second

        const data = message.data;
        if (data) {
          // Write to multiple possible fields to ensure compatibility
          set({ 
            marketData: { ...get().marketData, heatmap: data }, 
            heatmapData: data,
            oiHeatmap: data,
            oi_heatmap: data,
            _lastHeatmapUpdate: now,
            error: null 
          });
        }
        break;
      }

      case 'market_tick':
      case 'market_data':
      case 'tick': {
        const spot = message.spot ?? message.ltp ?? message.data?.ltp ?? 0;
        if (spot > 0) {
          set({
            spot,
            spotPrice: spot,
            liveSpot: spot,
            currentSpot: spot,
            lastUpdate: Date.now(),
            error: null
          });
        }
        break;
      }

      case 'intelligence_update':
        if (message.intelligence) {
          set({
            analytics: { ...get().analytics, intelligence: message.intelligence },
            lastUpdate: Date.now(),
            error: null
          });
        }
        break;

      case 'metrics_update':
        set({
          spot: message.spot ?? get().spot,
          lastUpdate: Date.now(),
          error: null
        });
        break;

      case 'ai_signal':
        set({
          analytics: { ...get().analytics, ai_signals: message.signals },
          lastUpdate: Date.now(),
          error: null
        });
        break;

      case 'advanced_strategies':
        set({
          advancedStrategies: message,
          analytics: { ...get().analytics, advanced_strategies: message },
          lastUpdate: Date.now(),
          error: null
        });
        break;

      case 'signal_score':
        set({
          signalScore: message,
          analytics: { ...get().analytics, signal_score: message },
          lastUpdate: Date.now(),
          error: null
        });
        break;

      case 'chart_analysis':
        set({
          chartAnalysis: message,
          lastUpdate: Date.now(),
          error: null
        });
        break;

      case 'candle_data':
        set({
          candles: message.candles || [],
          lastUpdate: Date.now(),
          error: null
        });
        break;

      case 'subscribed':
        console.log('✅ Subscribed to', message.symbol);
        break;

      case 'strategy_update': {
        // NEW: Handle separated strategy update message
        console.log("WS STRATEGY UPDATE:", message)
        
        // STEP 5: VERIFY strategy_update CASE HIT
        console.log("[STORE HIT] strategy_update")
        
        const { analysis, trade } = message;
        
        if (analysis) {
          set((prev) => ({
            ...prev,
            aiAnalysis: analysis,
            
            // Write flat fields for component compatibility
            regime:        analysis.regime        ?? prev.regime,
            bias:          analysis.bias          ?? prev.bias,
            biasStrength:  analysis.confidence    ?? prev.biasStrength,
            summary:       analysis.reasoning?.[0] ?? prev.summary,
            netGex:        analysis.gamma_analysis?.net_gex ?? prev.netGex,
            rsi:           analysis.technical_state?.rsi ?? prev.technicals?.rsi ?? prev.rsi,
            
            // Key levels — write to BOTH flat and nested
            callWall:      analysis.key_levels?.call_wall ?? prev.callWall,
            putWall:       analysis.key_levels?.put_wall  ?? prev.putWall,
            gexFlip:       analysis.key_levels?.gex_flip  ?? prev.gexFlip,
            keyLevels:     analysis.key_levels             ?? prev.keyLevels,
            
            // Technical state
            technicals: {
              ...(prev.technicals || {}),
              rsi:           analysis.technical_state?.rsi         ?? prev.technicals?.rsi,
              momentum_15m: analysis.technical_state?.momentum_15m ?? prev.technicals?.momentum_15m,
            },
            
            // Volatility
            volState: {
              ...(prev.volState || {}),
              state:         analysis.volatility_analysis?.regime ?? prev.volState?.state,
              iv_atm:        analysis.volatility_analysis?.iv_atm ?? prev.volState?.iv_atm,
              iv_percentile: analysis.volatility_analysis?.iv_percentile ?? prev.volState?.iv_percentile,
            },
            
            // Gamma
            gammaAnalysis: {
              ...(prev.gammaAnalysis || {}),
              regime:  analysis.gamma_analysis?.regime ?? prev.gammaAnalysis?.regime,
              net_gex: analysis.gamma_analysis?.net_gex ?? prev.gammaAnalysis?.net_gex,
              flip_level: analysis.gamma_analysis?.flip_level ?? prev.gammaAnalysis?.flip_level,
            },
            
            lastUpdate: Date.now(),
            error: null
          }));
        }
        
        if (trade) {
          // STEP 3: ADD DEBUG
          console.log("[STRATEGY UPDATE RECEIVED]", message.trade)
          set({
            tradeSetup: trade,
            lastUpdate: Date.now(),
            error: null
          });
        }
        
        break;
      }

      default:
        // Silently skip control messages
        if (!['pong', 'ping', 'ack'].includes(message.type)) {
          if (process.env.NODE_ENV === "development") {
            console.warn("⚠️ WS UNKNOWN MESSAGE TYPE:", message.type);
          }
        }
        break;
    }
  },

  handleAnalytics: (payload) => {
    if (!payload) return

    // P5: skip set if analytics timestamp hasn't changed (prevents render on identical payload)
    const prev = get().analytics
    if (prev?.timestamp && prev.timestamp === payload.timestamp) return

    // STEP 2: FIX ZUSTAND STORE MAPPING - analytics update
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
  },

  // NEW: Methods for separated fields
  setAIAnalysis: (analysis) => {
    set({ aiAnalysis: analysis })
  },

  setTradeSetup: (trade) => {
    set({ tradeSetup: trade })
  }
}))
