/**
 * SESSION GUARD UTILITY
 * 
 * Responsibilities:
 * - Check token validity
 * - Restore session after server restart
 * - Refresh token automatically
 * - Handle backend offline scenarios
 * - Prevent auth redirect loops
 */

import axios, { AxiosError } from 'axios';

export interface SessionState {
  isAuthenticated: boolean;
  token: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  backendStatus: 'online' | 'offline' | 'unknown';
  lastCheck: number;
}

export interface AuthCallbacks {
  onAuthRequired?: (loginUrl: string) => void;
  onAuthSuccess?: () => void;
  onBackendOffline?: () => void;
  onBackendOnline?: () => void;
  onTokenRefresh?: () => void;
}

class SessionGuard {
  private state: SessionState = {
    isAuthenticated: false,
    token: null,
    refreshToken: null,
    expiresAt: null,
    backendStatus: 'unknown',
    lastCheck: 0,
  };

  private callbacks: AuthCallbacks = {};
  private refreshPromise: Promise<string> | null = null;
  private checkPromise: Promise<boolean> | null = null;
  private retryCount = 0;
  private maxRetries = 3;
  private retryDelay = 3000; // 3 seconds

  constructor() {
    this.loadStoredSession();
  }

  /**
   * Set authentication callbacks
   */
  setCallbacks(callbacks: AuthCallbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * Load session from localStorage
   */
  private loadStoredSession(): void {
    try {
      const stored = localStorage.getItem('strikeiq_session');
      if (stored) {
        const sessionData = JSON.parse(stored);
        this.state = { ...this.state, ...sessionData };
        
        // Check if token is still valid
        if (this.state.expiresAt && Date.now() < this.state.expiresAt) {
          this.state.isAuthenticated = true;
        } else {
          this.clearSession();
        }
      }
    } catch (error) {
      console.warn('[SessionGuard] Failed to load stored session:', error);
      this.clearSession();
    }
  }

  /**
   * Save session to localStorage
   */
  private saveSession(): void {
    try {
      localStorage.setItem('strikeiq_session', JSON.stringify({
        token: this.state.token,
        refreshToken: this.state.refreshToken,
        expiresAt: this.state.expiresAt,
        isAuthenticated: this.state.isAuthenticated,
      }));
    } catch (error) {
      console.warn('[SessionGuard] Failed to save session:', error);
    }
  }

  /**
   * Clear session from storage and memory
   */
  private clearSession(): void {
    this.state = {
      isAuthenticated: false,
      token: null,
      refreshToken: null,
      expiresAt: null,
      backendStatus: this.state.backendStatus,
      lastCheck: Date.now(),
    };
    
    try {
      localStorage.removeItem('strikeiq_session');
    } catch (error) {
      console.warn('[SessionGuard] Failed to clear session:', error);
    }
  }

  /**
   * Check authentication status with backend
   */
  async checkAuth(): Promise<boolean> {
    // Prevent duplicate checks
    if (this.checkPromise) {
      return this.checkPromise;
    }

    this.checkPromise = this.performAuthCheck();
    
    try {
      const result = await this.checkPromise;
      return result;
    } finally {
      this.checkPromise = null;
    }
  }

  private async performAuthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/status`, {
        timeout: 5000,
      });

      this.state.backendStatus = 'online';
      this.state.lastCheck = Date.now();
      this.retryCount = 0;

      if (response.data.authenticated) {
        this.state.isAuthenticated = true;
        this.callbacks.onAuthSuccess?.();
        return true;
      } else {
        this.state.isAuthenticated = false;
        
        if (response.data.login_url) {
          this.callbacks.onAuthRequired?.(response.data.login_url);
        }
        return false;
      }
    } catch (error: any) {
      // Handle network errors
      if (!error.response) {
        this.state.backendStatus = 'offline';
        this.callbacks.onBackendOffline?.();
        
        // Retry logic for backend offline
        if (this.retryCount < this.maxRetries) {
          this.retryCount++;
          console.log(`[SessionGuard] Backend offline, retrying in ${this.retryDelay}ms (attempt ${this.retryCount}/${this.maxRetries})`);
          
          setTimeout(() => {
            this.checkAuth();
          }, this.retryDelay);
        }
        return false;
      }

      // Handle HTTP errors
      if (error.response?.status === 401) {
        this.state.isAuthenticated = false;
        this.clearSession();
        
        if (error.response.data?.login_url) {
          this.callbacks.onAuthRequired?.(error.response.data.login_url);
        }
        return false;
      }

      // Handle other server errors
      this.state.backendStatus = 'offline';
      this.callbacks.onBackendOffline?.();
      return false;
    }
  }

  /**
   * Get valid token, refreshing if necessary
   */
  async getValidToken(): Promise<string | null> {
    // If we have a valid token, return it
    if (this.state.token && this.state.expiresAt && Date.now() < this.state.expiresAt) {
      return this.state.token;
    }

    // If no refresh token, user needs to login
    if (!this.state.refreshToken) {
      await this.checkAuth();
      return null;
    }

    // Refresh the token
    try {
      return await this.refreshToken();
    } catch (error) {
      console.error('[SessionGuard] Token refresh failed:', error);
      this.clearSession();
      await this.checkAuth();
      return null;
    }
  }

  /**
   * Refresh access token
   */
  private async refreshToken(): Promise<string> {
    // Prevent multiple refresh attempts
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this.performTokenRefresh();
    
    try {
      const token = await this.refreshPromise;
      return token;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async performTokenRefresh(): Promise<string> {
    try {
      this.callbacks.onTokenRefresh?.();
      
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`, {}, {
        timeout: 10000,
      });

      if (response.data.access_token) {
        this.state.token = response.data.access_token;
        this.state.expiresAt = response.data.expires_at 
          ? response.data.expires_at * 1000 // Convert to milliseconds
          : Date.now() + (3600 * 1000); // Default 1 hour
        
        this.state.isAuthenticated = true;
        this.saveSession();
        
        return this.state.token;
      } else {
        throw new Error('No access token in refresh response');
      }
    } catch (error: any) {
      if (error.response?.status === 401) {
        // Refresh token is invalid, clear session
        this.clearSession();
        throw new Error('Refresh token invalid');
      }
      throw error;
    }
  }

  /**
   * Set authentication after successful login
   */
  setAuth(token: string, refreshToken?: string, expiresIn?: number): void {
    this.state.token = token;
    this.state.refreshToken = refreshToken || null;
    this.state.expiresAt = expiresIn 
      ? Date.now() + (expiresIn * 1000)
      : Date.now() + (3600 * 1000); // Default 1 hour
    this.state.isAuthenticated = true;
    this.state.backendStatus = 'online';
    this.state.lastCheck = Date.now();
    
    this.saveSession();
    this.callbacks.onAuthSuccess?.();
  }

  /**
   * Logout and clear session
   */
  logout(): void {
    this.clearSession();
    this.callbacks.onAuthRequired?.('/auth');
  }

  /**
   * Get current session state
   */
  getState(): SessionState {
    return { ...this.state };
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.state.isAuthenticated && 
           this.state.token !== null && 
           this.state.expiresAt !== null && 
           Date.now() < this.state.expiresAt;
  }

  /**
   * Check if backend is online
   */
  isBackendOnline(): boolean {
    return this.state.backendStatus === 'online';
  }

  /**
   * Force backend status check
   */
  async checkBackendStatus(): Promise<boolean> {
    try {
      await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/status`, { timeout: 3000 });
      this.state.backendStatus = 'online';
      this.callbacks.onBackendOnline?.();
      return true;
    } catch (error) {
      this.state.backendStatus = 'offline';
      this.callbacks.onBackendOffline?.();
      return false;
    }
  }
}

// Create singleton instance
const sessionGuard = new SessionGuard();

export default sessionGuard;
export { SessionGuard };
