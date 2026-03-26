import axios from "axios";

/**
 * Centralized API client for StrikeIQ.
 * Uses environment variable for Railway backend in production.
 */

// Safe fetch guard
if (!process.env.NEXT_PUBLIC_API_URL) {
    console.error("API URL missing - set NEXT_PUBLIC_API_URL in environment");
}

const client = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    timeout: 5000,
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
});

// Request interceptor for basic error handling preparation
client.interceptors.request.use(
    (config) => {
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor with smarter retry and offline detection
client.interceptors.response.use(
    (response) => response,
    async (error) => {
        const config = error.config;

        // Detect if backend is offline (no response or Next.js proxy 500)
        const isOffline = !error.response || error.response.status === 500;

        // Skip retry and return a safe 'offline' resolution for offline states
        // This prevents the Axios 'reject' which triggers crash overlays in dev mode
        if (isOffline) {
            console.warn("🌐 StrikeIQ Backend Offline - Returning safe fallback to UI");
            return Promise.resolve({
                data: null,
                status: error.response?.status || 500,
                offline: true,
                message: "Backend services currently unreachable"
            });
        }

        // Only retry once for transient (NOT offline) errors
        if (config && !config._isRetry) {
            config._isRetry = true;
            try {
                console.warn(`🔄 Retrying transient failure: ${config.url}`);
                return await client(config);
            } catch (retryError) {
                console.warn("🌐 Backend offline, returning safe fallback");
                return {
                    status: 200,
                    statusText: "offline",
                    data: null,
                    headers: {},
                    config
                };
            }
        }

        // Handle direct timeouts or other non-offline errors as rejections
        if (error.code === "ECONNABORTED") {
            console.error("⏱️ API Timeout - server taking too long");
        }

        return Promise.reject(error);
    }
);

export default client;
