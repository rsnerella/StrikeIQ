import { useMarketStore } from "../stores/marketStore"
import { useWSStore } from "../core/ws/wsStore"
import { wsLog, wsError, wsCritical } from "@/utils/uiLogger"

let socket: WebSocket | null = null
let isConnecting = false
let intentionalClose = false  // BUG 10 FIX: guard against reconnect on intentional disconnect

let reconnectAttempts = 0
let visibilityListenerAdded = false
let reconnectTimer: any = null
let lastVisibilityReconnect = 0  // MOBILE FIX: throttle visibility reconnects

const MAX_RECONNECTS = 10
declare global {
  interface Window {
    __WS_CONNECTED__?: boolean;
    __wsRateTracker?: { count: number; startTime: number };
  }
}
export function connectMarketWS() {
  // Ensure client-side only
  if (typeof window === "undefined") return;
  
  if (socket &&
    (socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING)) {
    console.log("🔒 WebSocket already connecting")
    return
  }

  console.log("WS CONNECTING")
  console.log("⚡ CONNECT() EXECUTED", {
    reconnectAttempts,
    time: Date.now()
  })

  const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "wss://strikeiq-production-e1cd.up.railway.app/ws/market";

  if (!WS_URL) {
    console.error("❌ WS URL missing");
    return;
  }

  wsLog("WS CONNECTING", { url: WS_URL, reconnectAttempts })

  if (reconnectAttempts > MAX_RECONNECTS) {
    wsError("WS RECONNECT LIMIT REACHED", { reconnectAttempts, maxReconnects: MAX_RECONNECTS })
    console.error("❌ Max reconnect attempts reached")
    return null
  }

  if (
    (window as any).__strikeiq_ws &&
    (window as any).__strikeiq_ws.readyState === WebSocket.OPEN
  ) {
    console.log("🔒 Returning existing WebSocket instance")
    return (window as any).__strikeiq_ws
  }

  if (isConnecting) {
    console.log("🔒 WebSocket already connecting")
    return null
  }

  if (socket && socket.readyState === WebSocket.OPEN) {
    return socket
  }

  isConnecting = true

  // CLEAN OLD SOCKET
  if (socket) {
    socket.onopen = null
    socket.onclose = null
    socket.onmessage = null
  }

  // Close any existing WebSocket connection before creating a new one
  if ((window as any).__strikeiq_ws) {
    try {
      console.warn("⚠️ MANUAL WS CLOSE TRIGGERED", (new Error()).stack || "No stack trace available");
      (window as any).__strikeiq_ws.close()
    } catch (error) {
      // Ignore errors when closing existing WebSocket
    }
  }

  console.log("🧠 WS CONNECT CALLED", {
    time: new Date().toISOString(),
    stack: new Error().stack || "No stack trace available"
  })

  socket = new WebSocket(WS_URL)

    ; (window as any).__strikeiq_ws = socket

  socket.onopen = () => {
    console.log("WS OPEN")
    console.log("WS TRACE → SOCKET OPEN", {
      readyState: socket.readyState,
      time: new Date().toISOString()
    })

    if (typeof window !== "undefined") {
      window.__WS_CONNECTED__ = true
    }
    reconnectAttempts = 0  // P6: reset counter on successful connect

    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("ws-connected"))
      console.log("WS TRACE → EVENT DISPATCHED ws-connected")
    }

    // Update marketStore with connection state
    const marketStore = useMarketStore.getState()
    marketStore.updateMarketData({
      connected: true,
      lastUpdate: Date.now()
    })

    const getNextThursday = () => {
      const d = new Date()
      const day = d.getDay()
      const daysUntilThursday = (4 - day + 7) % 7 || 7
      d.setDate(d.getDate() + daysUntilThursday)
      return d.toISOString().split('T')[0]
    }
    const storedExpiry = localStorage.getItem("selectedExpiry")
    const fallbackExpiry = storedExpiry && storedExpiry.length > 5 ? storedExpiry : getNextThursday()

    const stateSymbol = (window as any).__last_ws_symbol || "NIFTY";
    const stateExpiry = (window as any).__last_ws_expiry || fallbackExpiry;

    socket.send(JSON.stringify({
      type: "subscribe",
      symbol: stateSymbol,
      expiry: stateExpiry
    }))

    ;(window as any).__last_ws_symbol = stateSymbol;
    ;(window as any).__last_ws_expiry = stateExpiry;

    console.log("📤 INITIAL SUBSCRIBE SENT", { symbol: stateSymbol, expiry: stateExpiry })

    if (!visibilityListenerAdded && typeof window !== "undefined" && typeof document !== "undefined") {

      visibilityListenerAdded = true

      document.addEventListener("visibilitychange", () => {
        console.log("VISIBILITY CHANGE", { hidden: document.hidden })

        if (document.hidden) {
          console.log("TAB HIDDEN – keeping WS alive")
          return
        }

        // MOBILE FIX: Add throttling to prevent rapid reconnects on mobile
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          const now = Date.now()
          if (now - lastVisibilityReconnect > 5000) {
            console.log("TAB ACTIVE – reconnecting WS (throttled)")
            lastVisibilityReconnect = now
            connectMarketWS()
          } else {
            console.log("TAB ACTIVE – reconnect throttled (recent attempt)")
          }
        }
      })

    }

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
  }

  socket.onmessage = (event) => {
    try {
      // Guard: skip non-JSON frames (plain text status/error messages)
      const raw = event.data
      if (typeof raw !== 'string') {
        console.warn('WS NON-STRING FRAME SKIPPED:', typeof raw)
        return
      }
      
      // Check if it looks like JSON (starts with { or [)
      const trimmed = raw.trim()
      if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
        console.warn('WS NON-JSON FRAME SKIPPED:', raw?.substring(0, 100))
        return
      }
      
      const data = JSON.parse(raw)
      
      // STEP 1: VERIFY WS RAW MESSAGE
      console.log("[WS RAW MESSAGE FULL]", data)
      
      // STEP 2: VERIFY MESSAGE TYPE
      console.log("[WS MESSAGE TYPE]", data.type)
      
      // PERFORMANCE: Count message rate to detect performance issues
      console.count("WS_MESSAGE")
      
      // PERFORMANCE: Calculate average rate per second
      if (typeof window !== "undefined" && !window.__wsRateTracker) {
        window.__wsRateTracker = { count: 0, startTime: Date.now() }
      }
      if (typeof window !== "undefined") {
        window.__wsRateTracker.count++
        const elapsed = (Date.now() - window.__wsRateTracker.startTime) / 1000
        if (elapsed >= 5) {
          const rate = Math.round(window.__wsRateTracker.count / elapsed)
          console.log(`WS MESSAGE RATE: ${rate}/sec (average over ${elapsed.toFixed(1)}s)`)
          window.__wsRateTracker = { count: 0, startTime: Date.now() }
        }
      }
      
      // STEP 3: Add WS message debug
      console.log("WS TICK →", data);

      // Route analytics to handleAnalytics
      if (data.type === "analytics" || data.type === "analytics_update") {
        if (process.env.NODE_ENV === "development") {
          console.log("📊 ANALYTICS RECEIVED:", data)
        }
        
        // STEP 1: VERIFY WS PAYLOAD STRUCTURE
        console.log("[WS RAW ANALYTICS]", data.analytics)
        console.log("[WS RECEIVED]", data.analytics)
        console.log("[WS FINAL ANALYTICS]", data.analytics)
        
        const wsStore = useWSStore.getState()
        if (wsStore.handleAnalytics) {
          wsStore.handleAnalytics(data)
        }
        return
      }

      // Route ALL other message types through handleMessage
      // This covers: index_tick, option_chain_update, heatmap_update,
      // market_tick, market_data, chain_update
      
      // STEP 3: VERIFY HANDLE FORWARDING
      console.log("[WS → STORE FORWARD]", data.type)
      
      const wsStore = useWSStore.getState()
      if (wsStore.handleMessage) {
        wsStore.handleMessage(data)
      }
    } catch (err) {
      console.warn('WS JSON PARSE ERROR:', err, 'raw:', event.data?.substring(0, 200))
      // Do NOT rethrow — just skip this frame
      return
    }
  }

  socket.onclose = (event) => {
    console.log("WS CLOSED", { code: event.code, wasClean: event.wasClean })

    if (typeof window !== "undefined") {
      window.__WS_CONNECTED__ = false
    }
    isConnecting = false

    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("ws-disconnected"))
    }

    // BUG 10 FIX: Do not reconnect on intentional close
    if (intentionalClose) {
      console.log("🔒 WS closed intentionally — skipping reconnect")
      intentionalClose = false
      return
    }

    scheduleReconnect()
  }

  socket.onerror = (err) => {
    console.error("🔥 WS ERROR", err)
    console.log("WS TRACE → SOCKET ERROR", err)

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    wsError("WS ERROR", {
      error: err,
      readyState: socket?.readyState,
      url: wsUrl
    })

    console.error("WebSocket error", err)

    if (socket) {
      console.error("Socket readyState:", socket.readyState)
    }

    // Safe reconnect: only attempt if socket is not in OPEN state
    if (socket?.readyState !== WebSocket.OPEN) {
      console.log("🔄 Socket not open, will attempt reconnect")
      scheduleReconnect()
    } else {
      console.log("📡 Socket still open, no reconnect needed")
    }
  }

  return socket
}

function scheduleReconnect() {
  if (reconnectAttempts >= MAX_RECONNECTS) {
    wsError("WS RECONNECT LIMIT REACHED", { reconnectAttempts, maxReconnects: MAX_RECONNECTS })
    console.error("❌ Max reconnect attempts reached")
    return
  }

  reconnectAttempts++
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000) // Exponential backoff, max 30s

  // Ensure minimum 3-second delay when backend is down
  const safeDelay = Math.max(delay, 3000)

  wsLog("WS SCHEDULING RECONNECT", {
    attempt: reconnectAttempts,
    delay: safeDelay,
    maxDelay: 30000
  })

  console.log(`🔄 Reconnecting in ${safeDelay / 1000}s... Attempt ${reconnectAttempts}/${MAX_RECONNECTS}`)

  reconnectTimer = setTimeout(() => {
    console.log(`🔄 Reconnecting... Attempt ${reconnectAttempts}/${MAX_RECONNECTS}`)
    connectMarketWS()
  }, safeDelay)
}

export function disconnectMarketWS() {
  // BUG 10 FIX: Set flag before close so onclose does not auto-reconnect
  intentionalClose = true

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (socket) {
    socket.close()
    socket = null
  }

  const marketStore = useMarketStore.getState()
  marketStore.updateMarketData({
    connected: false,
    lastUpdate: Date.now()
  })
}

export function getWSConnectionStatus() {
  if (typeof window === "undefined") {
    return {
      connected: false,
      connecting: false,
      reconnectAttempts: 0,
      url: "client-side-only"
    };
  }
  
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
  return {
    connected: socket?.readyState === WebSocket.OPEN,
    connecting: isConnecting,
    reconnectAttempts,
    url: wsUrl
  };
}

export function resubscribeMarketWS(symbol: string, expiry: string | null) {
  if (!symbol || typeof window === "undefined") return;
  
  const oldSymbol = (window as any).__last_ws_symbol;
  const oldExpiry = (window as any).__last_ws_expiry;
  
  if (oldSymbol === symbol && oldExpiry === expiry) {
    return; // Prevent duplicate subscriptions
  }

  (window as any).__last_ws_symbol = symbol;
  (window as any).__last_ws_expiry = expiry;
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    if (oldSymbol) {
      socket.send(JSON.stringify({
        type: "unsubscribe",
        symbol: oldSymbol,
        expiry: oldExpiry
      }));
      console.log("📤 UNSUBSCRIBE SENT", { symbol: oldSymbol, expiry: oldExpiry });
    }
    
    socket.send(JSON.stringify({
      type: "subscribe",
      symbol,
      expiry
    }));
    console.log("📤 RESUBSCRIBE SENT", { symbol, expiry });
  } else {
    connectMarketWS();
  }
}
