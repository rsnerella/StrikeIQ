import { useMarketStore } from "../stores/marketStore"
import { wsLog, wsError, wsCritical } from "@/utils/uiLogger"

let socket: WebSocket | null = null
let isConnecting = false

let reconnectAttempts = 0
let visibilityListenerAdded = false
let reconnectTimer: any = null

const MAX_RECONNECTS = 10
declare global {
  interface Window {
    __WS_CONNECTED__?: boolean;
  }
}

const WS_URL = "ws://localhost:8000/ws/market"

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

  ;(window as any).__strikeiq_ws = socket

  socket.onopen = () => {
    console.log("WS OPEN")
    console.log("WS TRACE → SOCKET OPEN", {
      readyState: socket.readyState,
      time: new Date().toISOString()
    })

    window.__WS_CONNECTED__ = true

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

    const storedExpiry = localStorage.getItem("selectedExpiry")

    const expiry = storedExpiry && storedExpiry.length > 5
      ? storedExpiry
      : "2026-03-10"

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

        if (!socket || socket.readyState !== WebSocket.OPEN) {
          console.log("TAB ACTIVE – reconnecting WS")
          connectMarketWS()
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
    console.log("WS DATA", data)
  } catch (e) {
    console.warn("Invalid WS message", event.data)
  }
}

  socket.onclose = () => {
    console.log("WS CLOSED")
    console.log("WS TRACE → SOCKET CLOSED", {
      readyState: socket.readyState
    })

    window.__WS_CONNECTED__ = false

    if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("ws-disconnected"))
        console.log("WS TRACE → EVENT DISPATCHED ws-disconnected")
    }

    setTimeout(() => {
      connectMarketWS()
    }, 3000)
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

  console.log(`🔄 Reconnecting in ${safeDelay/1000}s... Attempt ${reconnectAttempts}/${MAX_RECONNECTS}`)

  reconnectTimer = setTimeout(() => {
    console.log(`🔄 Reconnecting... Attempt ${reconnectAttempts}/${MAX_RECONNECTS}`)
    connectMarketWS()
  }, safeDelay)
}

export function disconnectMarketWS() {
  if (socket) {
    console.warn("⚠️ MANUAL WS CLOSE TRIGGERED", (new Error()).stack || "No stack trace available");
    socket.close()
    socket = null
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
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
