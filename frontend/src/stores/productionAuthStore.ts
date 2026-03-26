/**
 * Production-Grade Auth Store for StrikeIQ
 * Stable authentication state management with single check
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import api from '../lib/axios';

interface AuthState {
  authenticated: boolean;
  loading: boolean;
  checked: boolean;
  error: string | null;
  loginUrl: string | null;
  backendStatus: 'online' | 'offline' | 'unknown';
}

interface AuthActions {
  checkAuth: () => Promise<void>;
  setAuthenticated: (authenticated: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  authenticated: false,
  loading: true,
  checked: false,
  error: null,
  loginUrl: null,
  backendStatus: 'unknown',
};

export const useAuthStore = create<AuthStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      checkAuth: async () => {
        const state = get();
        
        // CRITICAL: Check auth only ONCE
        if (state.checked) {
          console.log('🔒 Auth already checked, skipping duplicate call');
          return;
        }

        console.log('🔍 Performing ONE-TIME auth check...');
        set({ loading: true, error: null });

        try {
          const response = await api.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/status`, { 
            timeout: 5000,
            validateStatus: (status) => status < 500 // Treat 4xx as valid responses
          });

          const data = response.data;
          console.log('✅ Auth status received:', data);
          
          if (data.authenticated) {
            set({ 
              authenticated: true, 
              loading: false, 
              checked: true,
              error: null,
              loginUrl: null,
              backendStatus: 'online'
            });
          } else {
            set({ 
              authenticated: false, 
              loading: false, 
              checked: true,
              error: null,
              loginUrl: data.login_url || '/auth',
              backendStatus: 'online'
            });
          }
        } catch (error: any) {
          console.error('❌ Auth check failed:', error.message);
          
          // Handle network errors and 401s
          if (error.code === 'ERR_NETWORK' || error.response?.status >= 500) {
            // Backend offline - don't set authenticated to false yet
            set({ 
              loading: false, 
              checked: true,
              error: 'Backend offline',
              backendStatus: 'offline'
            });
          } else if (error.response?.status === 401) {
            // Explicitly unauthenticated
            set({ 
              authenticated: false, 
              loading: false, 
              checked: true,
              error: null,
              loginUrl: '/auth',
              backendStatus: 'online'
            });
          } else {
            // Other errors
            set({ 
              authenticated: false, 
              loading: false, 
              checked: true,
              error: 'Authentication check failed',
              backendStatus: 'unknown'
            });
          }
        }
      },

      setAuthenticated: (authenticated: boolean) => {
        set({ 
          authenticated, 
          loading: false, 
          checked: true,
          error: null,
          backendStatus: 'online'
        });
      },

      setError: (error: string | null) => {
        set({ error, loading: false });
      },

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'auth-store',
    }
  )
);

// Selectors for optimized re-renders
export const useAuth = () => useAuthStore((state) => ({
  authenticated: state.authenticated,
  loading: state.loading,
  checked: state.checked,
  error: state.error,
  loginUrl: state.loginUrl,
  backendStatus: state.backendStatus,
}));

export const useAuthActions = () => useAuthStore((state) => ({
  checkAuth: state.checkAuth,
  setAuthenticated: state.setAuthenticated,
  setError: state.setError,
  reset: state.reset,
}));

// Global auth check function (runs only once)
let globalAuthChecked = false;

export const checkGlobalAuth = async () => {
  if (globalAuthChecked) {
    console.log('🔒 Global auth already checked');
    return;
  }

  const { checkAuth } = useAuthStore.getState();
  await checkAuth();
  globalAuthChecked = true;
  console.log('✅ Global auth check completed');
};
