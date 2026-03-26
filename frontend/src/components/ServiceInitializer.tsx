"use client"

import { useEffect, useRef } from "react"
import { usePathname } from "next/navigation"
import { connectMarketWS } from "../services/wsService"
import { uiLog } from "@/utils/uiLogger"

interface Props {
  children: React.ReactNode
}

export default function ServiceInitializer({ children }: Props) {
  const pathname = usePathname()
  const initializedRef = useRef(false)

  useEffect(() => {
    // Prevent multiple initializations
    if (initializedRef.current) {
      uiLog("SERVICE INITIALIZATION SKIPPED", { pathname, alreadyInitialized: true })
      return
    }

    uiLog("SERVICE INITIALIZATION START", { pathname })
    
    // Initialize WebSocket connection
    connectMarketWS()
    
    initializedRef.current = true
    uiLog("SERVICE INITIALIZATION COMPLETE", { pathname })
  }, []) // Remove pathname dependency to prevent reconnects on route changes

  return <>{children}</>
}
