import { useEffect, useState } from "react"

export function useConnectionGuard() {

  const [isConnected, setIsConnected] = useState(true)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastError, setLastError] = useState<string | null>(null)

  useEffect(() => {

    function handleOnline() {
      console.log("🌐 Browser online")
      setIsConnected(true)
      setIsReconnecting(false)
      setLastError(null)
    }

    function handleOffline() {
      console.log("🚫 Browser offline")
      setIsConnected(false)
      setLastError("Browser offline")
    }

    const connectHandler = () => {
      console.log("WS TRACE → EVENT RECEIVED ws-connected")
      setIsConnected(true)
      setIsReconnecting(false)
      setLastError(null)
    }

    const disconnectHandler = () => {
      console.log("WS TRACE → EVENT RECEIVED ws-disconnected")
      setIsConnected(false)
      setLastError("WebSocket disconnected")
    }

    window.addEventListener("online", handleOnline)
    window.addEventListener("offline", handleOffline)
    window.addEventListener("ws-connected", connectHandler)
    window.addEventListener("ws-disconnected", disconnectHandler)

    return () => {
      window.removeEventListener("online", handleOnline)
      window.removeEventListener("offline", handleOffline)
      window.removeEventListener("ws-connected", connectHandler)
      window.removeEventListener("ws-disconnected", disconnectHandler)
    }

  }, [])

  return {
    isConnected,
    isReconnecting,
    reconnectAttempts,
    lastError
  }
}
