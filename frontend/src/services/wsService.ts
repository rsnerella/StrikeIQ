import { useMarketStore } from "../stores/marketStore"
import { useWSStore } from "../core/ws/wsStore"

let socket: WebSocket | null = null
let isConnecting = false

let reconnectAttempts = 0
let visibilityListenerAdded = false
let reconnectTimer: any = null

const MAX_RECONNECTS = 5
const WS_URL = "ws://localhost:8000/ws/market"

export function connectMarketWS() {

  if (
    socket &&
    (socket.readyState === WebSocket.OPEN ||
     socket.readyState === WebSocket.CONNECTING)
  ) {
    console.log("🔒 WebSocket already active")
    return socket
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
      (window as any).__strikeiq_ws.close()
    } catch {}
  }

  socket = new WebSocket(WS_URL)

  ;(window as any).__strikeiq_ws = socket

  socket.onopen = () => {

    console.log("✅ WebSocket connected")

    const wsStore = useWSStore.getState()
    const marketStore = useMarketStore.getState()

    wsStore.setConnected(true)
    
    marketStore.updateMarketData({
        connected: true,
        lastUpdate: new Date().toISOString()
    })

    reconnectAttempts = 0
    isConnecting = false

    if (!visibilityListenerAdded) {

      visibilityListenerAdded = true

      document.addEventListener("visibilitychange", () => {

        if (document.hidden) {

          console.log("📴 Browser tab inactive")

        } else {

          console.log("📡 Browser tab active")

        }

      })

    }

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
  }

  socket.onmessage = (event) => {

let data

try {

  data =
    typeof event.data === "string"
      ? JSON.parse(event.data)
      : event.data

} catch (e) {

  console.error("Invalid WS message", e)

  return
}

if (!data || !data.type) return

const store = useWSStore.getState()

// FIX 4: Add frontend spot handler
if (data.type === "spot_tick") {

const store = useWSStore.getState()

store.setMarketData({
symbol: data.symbol,
spot: data.spot
})

console.log("📈 NIFTY SPOT UPDATE:", data.spot)

return
}

if (data.type === "market_status") {

   const status = data.status ?? "closed"

   store.setConnected(true)
   store.setMarketOpen(status === "open")

   return
 }

  if (data.type === "market_data") {
    console.log("📡 WS MARKET DATA RECEIVED")

    // Handle spot price updates
    if (data.spot !== undefined) {
      const marketStore = useMarketStore.getState()
      marketStore.setSpot(data.spot)
      console.log("📍 SPOT UPDATED:", data.spot)
    }

    store.setMarketData(data)
    store.setConnected(true)

    return
  }

  if (data.type === "option_chain") {

    console.log("📡 WS OPTION CHAIN RECEIVED")

    const marketStore = useMarketStore.getState()
    marketStore.setOptionChain(data.chain)
    store.setConnected(true)

    return
  }

  if (data.type === "ai_signal") {

    console.log("🤖 WS AI SIGNAL RECEIVED:", data.signals)

    const marketStore = useMarketStore.getState()
    marketStore.setAISignals(data.signals || [])
    store.setConnected(true)

    return
  }

}

  socket.onclose = () => {

    console.log("❌ WebSocket closed")

    const wsStore = useWSStore.getState()
    const marketStore = useMarketStore.getState()

    wsStore.setConnected(false)
    
    marketStore.updateMarketData({
        connected: false,
        marketOpen: false,
        lastUpdate: new Date().toISOString()
    })

}

  socket.onerror = (err) => {

    console.error("WebSocket error", err)

    if (socket) {
      console.error("Socket readyState:", socket.readyState)
    }

  }

  return socket
}

function scheduleReconnect() {

  if (reconnectAttempts >= MAX_RECONNECTS) {
    console.error("❌ Max reconnect attempts reached")
    return
  }

  const delay = 1000 * Math.pow(2, reconnectAttempts)

  reconnectTimer = setTimeout(() => {

    reconnectAttempts++

    console.log("🔄 Reconnecting WebSocket attempt", reconnectAttempts)

    connectMarketWS()

  }, delay)
}
