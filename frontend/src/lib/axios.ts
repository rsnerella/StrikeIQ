import axios from "axios"
import { getTraceId } from "@/utils/traceManager"
import { apiLog, apiError } from "@/utils/uiLogger"

// Extend axios config to include metadata
declare module "axios" {
  interface InternalAxiosRequestConfig {
    metadata?: {
      traceId: string
      startTime: number
    }
  }
}

const getBaseURL = () => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && !envUrl.includes("localhost")) {
    return envUrl;
  }
  
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:8000`;
  }
  
  return "http://localhost:8000";
}

// Create axios instance with default config
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 5000
})

// Request interceptor for tracing and performance
api.interceptors.request.use(
  (config) => {
    const traceId = getTraceId()
    config.metadata = { traceId, startTime: performance.now() }

    apiLog("API REQUEST START", {
      traceId,
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL
    })

    return config
  },
  (error) => {
    apiError("API REQUEST ERROR", error)
    return Promise.reject(error)
  }
)

// Response interceptor for tracing and error handling
api.interceptors.response.use(
  (response) => {
    const { traceId, startTime } = response.config.metadata || {}
    const latency = startTime ? performance.now() - startTime : 0

    apiLog("API RESPONSE RECEIVED", {
      traceId,
      status: response.status,
      latency: `${latency.toFixed(2)}ms`
    })

    return response
  },
  async (error) => {
    const { traceId, startTime } = error.config?.metadata || {}
    const latency = startTime ? performance.now() - startTime : 0

    if (error.code === "ERR_NETWORK") {
      apiError("NETWORK ERROR", { traceId, latency: `${latency.toFixed(2)}ms` })
      console.warn("Backend offline")
      return Promise.resolve({ data: { status: "offline" } })
    }

    // 401 FALLBACK: Only log error - NO automatic redirects
    if (error.response?.status === 401) {
      apiError("401 AUTH ERROR", { traceId, latency: `${latency.toFixed(2)}ms` })
      console.warn("🔐 401 received - authentication expired")
      return Promise.reject(error)
    }

    if (error.response?.status >= 500) {
      apiError("SERVER ERROR", {
        traceId,
        status: error.response.status,
        latency: `${latency.toFixed(2)}ms`
      })
      console.warn("Server error:", error.response.status)
      return Promise.resolve({ data: { status: "error" } })
    }

    apiError("API ERROR", {
      traceId,
      status: error.response?.status,
      message: error.message,
      latency: `${latency.toFixed(2)}ms`
    })

    return Promise.reject(error)
  }
)

export async function getValidExpiries(symbol: string): Promise<string[]> {
  try {
    const response = await api.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/market/expiries?symbol=${symbol}`)
    return response.data?.data || []
  } catch (error) {
    console.error("Failed to fetch expiries:", error)
    return []
  }
}

export default api
