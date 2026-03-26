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
  setTradeSetup: (trade: any) => void
}

// Helper to only call set if data actually changed
const selectiveUpdate = (set: any, get: any, updates: any) => {
  const state = get();
  const toUpdate: any = {};

  Object.entries(updates).forEach(([key, newVal]) => {
    if (key === 'lastUpdate') return; // Handle lastUpdate separately
    const oldVal = (state as any)[key];
    if (JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
      toUpdate[key] = newVal;
    }
  });

  if (Object.keys(toUpdate).length > 0) {
    if (updates.lastUpdate) {
      toUpdate.lastUpdate = updates.lastUpdate;
    }
    set(toUpdate);
  } else if (updates.lastUpdate && (updates as any)._force) {
     set({ lastUpdate: updates.lastUpdate });
  }
};

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
    if (process.env.NODE_ENV === 'development') {
      console.log("[STORE HANDLE ENTRY]", message.type)
    }

    // STEP 5: RAW WS LOGGING (development only)
    if (process.env.NODE_ENV === 'development' && message.type !== 'pong' && message.type !== 'ping') {
      console.log('RAW WS MESSAGE:', message.type, Object.keys(message));
    }

    const marketContextStore = useMarketContextStore.getState();
    const selectedSymbol = marketContextStore?.symbol || 'NIFTY';

    switch (message.type) {
      case 'market_update': {
        const now = Date.now()
        if (now - get()._lastChainUpdate < get()._THROTTLE_MS) {
          return
        }
        const p = message;
        if (p.symbol && p.symbol !== selectedSymbol) return;

        // Extract spot from any alias
        const spotRaw = p.spot ?? p.spotPrice ?? p.liveSpot ?? p.currentSpot ?? 0;
        const spot = typeof spotRaw === 'number' && spotRaw > 0 ? spotRaw : 0;

        // Development logging (reduced frequency)
        if (process.env.NODE_ENV === 'development' && now % 10000 < 100) { // Log every 10 seconds
          console.log(
            '[wsStore] market_update |',
            'spot=', spot,
            'pcr=', p.option_chain?.pcr,
            'calls=', Object.keys(p.option_chain?.calls || {}).length,
            'ai_ready=', p.ai_ready
          );
        }

        // Fix: Pre-calculate potentially new objects to allow selectiveUpdate to compare them
        const currentCalls = get().calls || {};
        const incomingCalls = p.option_chain?.calls || {};
        const newCalls = Object.keys(incomingCalls).length > 0 
          ? { ...currentCalls, ...incomingCalls }
          : currentCalls;

        const currentPuts = get().puts || {};
        const incomingPuts = p.option_chain?.puts || {};
        const newPuts = Object.keys(incomingPuts).length > 0
          ? { ...currentPuts, ...incomingPuts }
          : currentPuts;

        selectiveUpdate(set, get, {
          // SPOT — all aliases
          spot: spot > 0 ? spot : get().spot,
          spotPrice:    spot > 0 ? spot : get().spotPrice,
          liveSpot:     spot > 0 ? spot : get().liveSpot,
          currentSpot:  spot > 0 ? spot : get().currentSpot,

          // Core
          atm:          p.atm       ?? get().atm,
          symbol:       p.symbol    ?? get().symbol,
          lastUpdate:   p.timestamp ?? now, // Use same 'now' for consistency
          aiReady:      p.ai_ready  ?? p.aiReady ?? get().aiReady,

          // Option chain fields
          pcr:          p.option_chain?.pcr           ?? get().pcr,
          callWall:     p.option_chain?.call_wall      ?? get().callWall,
          putWall:      p.option_chain?.put_wall       ?? get().putWall,
          maxPain:      p.option_chain?.max_pain       ?? get().maxPain,
          gexFlip:      p.option_chain?.gex_flip       ?? get().gexFlip,
          netGex:       p.option_chain?.net_gex        ?? get().netGex,
          ivAtm:        p.option_chain?.iv_atm         ?? get().ivAtm,
          ivPercentile: p.option_chain?.iv_percentile  ?? get().ivPercentile,
          
          calls: newCalls,
          puts: newPuts,
          optionChain:  p.option_chain                 ?? get().optionChain,

          // AI analysis — accept both key names
          regime:        (p.market_analysis ?? p.aiIntelligence)?.regime          ?? get().regime,
          bias:          (p.market_analysis ?? p.aiIntelligence)?.bias            ?? get().bias,
          biasStrength:  (p.market_analysis ?? p.aiIntelligence)?.bias_strength   ?? get().biasStrength,
          keyLevels:     (p.market_analysis ?? p.aiIntelligence)?.key_levels      ?? get().keyLevels,
          gammaAnalysis: (p.market_analysis ?? p.aiIntelligence)?.gamma_analysis  ?? get().gammaAnalysis,
          volState:      (p.market_analysis ?? p.aiIntelligence)?.volatility_state ?? get().volState,
          technicals:    (p.market_analysis ?? p.aiIntelligence)?.technical_state  ?? get().technicals,
          summary:       (p.market_analysis ?? p.aiIntelligence)?.summary          ?? get().summary,

          // Plans and alerts
          tradePlan:     p.trade_plan     ?? get().tradePlan,
          earlyWarnings: Array.isArray(p.early_warnings) ? p.early_warnings : get().earlyWarnings ?? [],
          newsAlerts:    Array.isArray(p.news_alerts)    ? p.news_alerts    : get().newsAlerts    ?? [],
          paperTrading:  p.paper_trading  ?? get().paperTrading,

          // Data quality — Remove constant Date.now() to prevent loops
          dataQuality: {
            hasSpot:    spot > 0,
            hasOi:      (p.option_chain?.call_wall ?? 0) > 0,
            hasGreeks:  (p.option_chain?.iv_atm    ?? 0) > 0,
            aiReady:    p.ai_ready ?? false,
            // lastUpdate: now, // REMOVED: frequent timestamp updates defeat optimization
            source:     spot > 0 ? 'live' : 'rest_poller',
          },
          
          // 🔥 ADD PERFORMANCE DATA
          performance: p.performance ?? get().performance ?? {
            total_trades: 0,
            wins: 0,
            losses: 0,
            win_rate: 0,
            total_pnl: 0
          },
          analytics_full: p.analytics_full ?? get().analytics_full ?? {
            equity_curve: [],
            max_drawdown: 0,
            strategy_stats: {},
            current_equity: 0,
            peak_equity: 0
          },
          strategy_weights: p.strategy_weights ?? get().strategy_weights ?? {
            "TREND": 1.0,
            "REVERSAL": 1.0,
            "WEAK_TREND": 0.5,
            "RANGE": 1.0,
            "NONE": 0.0
          },
          
          _lastChainUpdate: now
        });
        break;
      }

      case 'analytics_update': {
        const a = message.analytics || {}
        const spot = a.spot || a.spotPrice || message.spot || 0

        // Only log on significant changes (development only)
        if (process.env.NODE_ENV === 'development') {
           const prev = get().analytics;
           if (prev?.strategy !== a.strategy || prev?.confidence !== a.confidence) {
              console.log("[WS ANALYTICS UPDATE]", {
                strategy: a.strategy,
                confidence: a.confidence
              });
           }
        }

        selectiveUpdate(set, get, {
            spotPrice:    spot > 0 ? spot : get().spotPrice,
            liveSpot:     spot > 0 ? spot : get().liveSpot,
            currentSpot:  spot > 0 ? spot : get().currentSpot,
            lastUpdate:   message.timestamp || Date.now(),
            aiReady:      true,

            analytics: {
              ...get().analytics,
              ...a,

              strategy:
                a.strategy !== undefined
                  ? a.strategy
                  : get().analytics?.strategy ?? 'NO_TRADE',

              confidence:
                a.confidence !== undefined
                  ? a.confidence
                  : get().analytics?.confidence ?? null,

              execution:
                a.execution !== undefined
                  ? a.execution
                  : get().analytics?.execution ?? {},

              metadata: a.metadata
                ? {
                    ...get().analytics?.metadata,
                    ...a.metadata
                  }
                : get().analytics?.metadata ?? {}
            },

            // Map from analytics object
            regime:        a.regime         || a.market_regime   || get().regime        || 'RANGING',
            bias:          a.bias           || a.market_bias     || get().bias          || 'NEUTRAL',
            biasStrength:  a.bias_strength  || a.confidence      || get().biasStrength  || 0,
            keyLevels:     a.key_levels     || a.levels          || get().keyLevels     || {},
            volState:      a.volatility_state || a.volatility    || get().volState      || {},
            technicals:    a.technical_state  || a.technicals    || get().technicals    || {},
            summary:       a.summary        || get().summary      || '',
            tradePlan:     a.trade_plan     || a.signal          || get().tradePlan     || null,
            earlyWarnings: Array.isArray(a.early_warnings) ? a.early_warnings :
                           Array.isArray(a.warnings)       ? a.warnings       :
                           get().earlyWarnings || [],
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
          const ltp = tick.ltp ?? 0;
          selectiveUpdate(set, get, {
            spot: ltp > 0 ? ltp : get().spot,
            spotPrice: ltp > 0 ? ltp : get().spotPrice,
            liveSpot: ltp > 0 ? ltp : get().liveSpot,
            currentSpot: ltp > 0 ? ltp : get().currentSpot,
            lastUpdate: Date.now(),
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
            analytics: message.intelligence,
            lastUpdate: Date.now(),
            error: null
          })
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

    // Throttle total store updates for analytics to 200ms
    const now = Date.now();
    const lastUpdate = get().lastUpdate;
    if (now - lastUpdate < 200) return;

    // STEP 2: FIX ZUSTAND STORE MAPPING - analytics update
    const renderableData = payload.analytics 
      ? { ...payload.analytics, symbol: payload.symbol, _timestamp: payload.timestamp } 
      : { ...payload };
    
    selectiveUpdate(set, get, {
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
      // Phase 8: Extract spot and chain from bundle for full sync - FIX CIRCULAR DEPENDENCY
      spot: renderableData.snapshot?.spot ?? 0,
      optionChainSnapshot: renderableData.option_chain,
      lastUpdate: now,
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
