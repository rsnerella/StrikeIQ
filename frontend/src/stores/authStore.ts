import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../lib/axios'

interface AuthState {
  status: 'loading' | 'authenticated' | 'unauthenticated'
  error: string | null
  loginUrl: string | null
  backendStatus: 'online' | 'offline' | 'unknown'
}

interface AuthActions {
  checkAuth: () => Promise<void>
  reset: () => void
}

type AuthStore = AuthState & AuthActions

const initialState: AuthState = {
  status: 'unauthenticated',
  error: null,
  loginUrl: null,
  backendStatus: 'unknown'
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      checkAuth: async () => {
        console.log('🔍 AUTH STATUS API CALL')
        
        set({ status: 'loading', error: null })

        try {
          const response = await api.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/status`, {
            timeout: 10000
          })

          const data = response.data
          console.log('✅ AUTH STATUS RESPONSE:', data)

          if (data.authenticated) {
            set({
              status: 'authenticated',
              error: null,
              loginUrl: null,
              backendStatus: 'online'
            })
          } else {
            set({
              status: 'unauthenticated',
              error: null,
              loginUrl: data.login_url || '/auth',
              backendStatus: 'online'
            })
          }

        } catch (error: any) {
          console.error('❌ AUTH STATUS FAILED', error.message)

          // Backend unreachable
          if (!error.response || error.response.status >= 500) {
            set({
              status: 'unauthenticated',
              error: 'Backend offline',
              loginUrl: null,
              backendStatus: 'offline'
            })
            return
          }

          set({
            status: 'unauthenticated',
            error: 'Authentication check failed',
            loginUrl: null,
            backendStatus: 'online'
          })
        }
      },

      reset: () => {
        set(initialState)
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        status: state.status,
        backendStatus: state.backendStatus,
        loginUrl: state.loginUrl
      }),
      onRehydrateStorage: () => (state) => {
        console.log('🔄 Auth store rehydrated from localStorage:', state)
      }
    }
  )
)

// Selectors for cleaner usage
export const useAuthStatus = () => useAuthStore(state => state.status)
export const useAuthError = () => useAuthStore(state => state.error)
export const useLoginUrl = () => useAuthStore(state => state.loginUrl)
export const useBackendStatus = () => useAuthStore(state => state.backendStatus)
export const useAuthActions = () => useAuthStore(state => ({ checkAuth: state.checkAuth, reset: state.reset }))
