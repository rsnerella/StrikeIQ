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
  }
}
const getWsUrl = () => {
  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl && !envUrl.includes("localhost")) {
    return envUrl;
  }
  if (typeof window !== "undefined") {
    return `ws://${window.location.hostname}:8000/ws/market`;
  }
  return "ws://localhost:8000/ws/market";
};

const WS_URL = getWsUrl();

export function connectMarketWS() {
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

    window.__WS_CONNECTED__ = true
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

    // P7: dynamic expiry fallback — next Thursday from today
    const getNextThursday = () => {
      const d = new Date()
      const day = d.getDay()
      const daysUntilThursday = (4 - day + 7) % 7 || 7
      d.setDate(d.getDate() + daysUntilThursday)
      return d.toISOString().split('T')[0]
    }
    const storedExpiry = localStorage.getItem("selectedExpiry")
    const expiry = storedExpiry && storedExpiry.length > 5 ? storedExpiry : getNextThursday()

    socket.send(JSON.stringify({
      type: "subscribe",
      symbol: "NIFTY",
      expiry
    }))

    console.log("📤 SUBSCRIBE SENT", { symbol: "NIFTY", expiry })

    if (!visibilityListenerAdded) {

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
      const data = JSON.parse(event.data)

      // Route analytics to handleAnalytics
      if (data.type === "analytics") {
        if (process.env.NODE_ENV === "development") {
          console.log("📊 ANALYTICS RECEIVED:", data)
        }
        const wsStore = useWSStore.getState()
        if (wsStore.handleAnalytics) {
          wsStore.handleAnalytics(data)
        }
        return
      }

      // Route ALL other message types through handleMessage
      // This covers: index_tick, option_chain_update, heatmap_update,
      // market_tick, market_data, chain_update
      const wsStore = useWSStore.getState()
      if (wsStore.handleMessage) {
        wsStore.handleMessage(data)
      }
    } catch (e) {
      console.warn("Invalid WS message", event.data)
    }
  }

  socket.onclose = (event) => {
    console.log("WS CLOSED", { code: event.code, wasClean: event.wasClean })

    window.__WS_CONNECTED__ = false
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

    wsError("WS ERROR", {
      error: err,
      readyState: socket?.readyState,
      url: WS_URL
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
  return {
    connected: socket?.readyState === WebSocket.OPEN,
    connecting: isConnecting,
    reconnectAttempts,
    url: WS_URL
  }
}
