/**
 * Axios Interceptors with Full Debug Logging
 * Logs all HTTP requests, responses, and errors with trace tracking
 */

import axios from 'axios';
import { apiLogger, traceManager } from './logger';

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

// Create axios instance with interceptors
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const traceId = traceManager.getTraceId();
    const url = config.url || '';

    apiLogger.info("API REQUEST", {
      traceId,
      url: config.baseURL + url,
      method: config.method?.toUpperCase(),
      headers: config.headers,
      data: config.data ? JSON.stringify(config.data).substring(0, 200) : undefined
    });

    return config;
  },
  (error) => {
    const traceId = traceManager.getTraceId();
    apiLogger.error("API REQUEST ERROR", { traceId, error: String(error) });
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    const traceId = traceManager.getTraceId();
    const url = response.config.url || '';

    apiLogger.info("API RESPONSE", {
      traceId,
      url: response.config.baseURL + url,
      method: response.config.method?.toUpperCase(),
      status: response.status,
      statusText: response.statusText,
      data: response.data ? JSON.stringify(response.data).substring(0, 200) : undefined
    });

    return response;
  },
  (error) => {
    const traceId = traceManager.getTraceId();
    const url = error.config?.url || '';

    apiLogger.error("API ERROR", {
      traceId,
      url: error.config?.baseURL + url,
      method: error.config?.method?.toUpperCase(),
      status: error.response?.status,
      statusText: error.response?.statusText,
      error: error.message,
      data: error.response?.data ? JSON.stringify(error.response?.data).substring(0, 200) : undefined
    });

    return Promise.reject(error);
  }
);

export default api;
