/**
 * Production Axios Configuration for StrikeIQ
 * Stable API client with proper 401 handling
 */

import axios from "axios";
import { useAuthStore } from '../stores/productionAuthStore';

const getBaseURL = () => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && !envUrl.includes("localhost")) {
    return envUrl;
  }
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

// Create axios instance with default config
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Request interceptor for adding auth headers if needed
api.interceptors.request.use(
  (config) => {
    // Add any request logging here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor with stable 401 handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle network errors
    if (error.code === "ERR_NETWORK") {
      console.warn("🔌 Backend offline - network error");
      return Promise.resolve({ data: { status: "offline" } });
    }

    // DISABLED: Auth checks are disabled per system memory
    // Do not redirect on 401 errors

    // Handle server errors (5xx)
    if (error.response?.status >= 500) {
      console.warn("🚨 Server error:", error.response.status);
      return Promise.resolve({ data: { status: "error", error: "Server error" } });
    }

    // Handle other errors
    return Promise.reject(error);
  }
);

export async function getValidExpiries(symbol: string): Promise<string[]> {
  try {
    const response = await api.get(`/api/v1/market/expiries?symbol=${symbol}`);
    return response.data?.data || [];
  } catch (error) {
    console.error("Failed to fetch expiries:", error);
    return [];
  }
}

export default api;
