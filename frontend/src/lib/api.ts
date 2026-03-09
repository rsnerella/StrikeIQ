import axios from "axios"
import { isTokenExpired } from "@/utils/auth"
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

const api = axios.create({
  baseURL: "", // Use empty string to support relative URLs for Next.js rewrites
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
})

// Request interceptor
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

    // DISABLED: Auth checks are disabled per system memory
    // Allow requests to proceed without token validation
    return config
  },
  (error) => {
    apiError("API REQUEST ERROR", error)
    return Promise.reject(error)
  }
)

// Response interceptor for handling 401 errors
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
  (error) => {
    const { traceId, startTime } = error.config?.metadata || {}
    const latency = startTime ? performance.now() - startTime : 0

    // DISABLED: Auth checks are disabled per system memory
    // Do not redirect on 401 errors

    // Handle network errors or proxy 500s (backend offline)
    const isOffline = !error.response || error.response.status === 500;

    if (isOffline) {
      apiError("OFFLINE", { traceId, latency: `${latency.toFixed(2)}ms` })
      console.warn('🌐 StrikeIQ Backend Offline - Soft resolution triggered')
      return Promise.resolve({
        data: null,
        status: error.response?.status || 500,
        offline: true
      })
    }

    // Handle other HTTP errors
    apiError("API ERROR", {
      traceId,
      status: error.response?.status,
      message: error.response?.data?.detail || error.message,
      latency: `${latency.toFixed(2)}ms`
    })
    console.error(`❌ API Error: ${error.response?.status} - ${error.response?.data?.detail || error.message}`)
    return Promise.reject(error)
  }
)

export default api
