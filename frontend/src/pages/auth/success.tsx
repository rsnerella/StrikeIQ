import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import { useAuthStore, useAuthStatus, useBackendStatus } from '@/stores/authStore'

export default function AuthSuccess() {
  const router = useRouter()
  const { checkAuth } = useAuthStore()
  const status = useAuthStatus()
  const backendStatus = useBackendStatus()
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    console.log("🚀 AUTH SUCCESS PAGE - Using authStore")
    
    // Trigger manual auth check only once since automatic checks are disabled
    if (!authChecked) {
      checkAuth()
      setAuthChecked(true)
    }
  }, [checkAuth, authChecked])

  useEffect(() => {
    if (status === 'loading') {
      return
    }
    
    if (status === 'authenticated') {
      console.log("🎉 AUTH SUCCESS PAGE - User is authenticated")
      
      // Redirect to / immediately when authenticated
      console.log("🔄 AUTH SUCCESS PAGE - Redirecting to dashboard")
      router.replace(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/upstox`);
    } else {
      console.log("❌ AUTH SUCCESS PAGE - User not authenticated")
    }
  }, [status, router])

  return (
    <>
      <Head>
        <title>Authentication Status - StrikeIQ</title>
        <meta name="description" content="Upstox authentication status" />
      </Head>
      
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          {status === 'loading' && (
            <>
              <div className="mb-8">
                <div className="w-20 h-20 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-4">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white"></div>
                </div>
                <h1 className="text-3xl font-bold text-white mb-2">Connecting your Upstox account...</h1>
                <p className="text-gray-300">Please wait while we verify your authentication</p>
              </div>
            </>
          )}
          
          {status === 'authenticated' && (
            <>
              <div className="mb-8">
                <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-3xl font-bold text-white mb-2">Broker Connected Successfully</h1>
                <p className="text-gray-300 mb-4">Your account has been connected successfully</p>
                <p className="text-sm text-gray-400">Redirecting to dashboard...</p>
              </div>
              
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto"></div>
            </>
          )}
          
          {status === 'unauthenticated' && (
            <>
              <div className="mb-8">
                <div className="w-20 h-20 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <h1 className="text-3xl font-bold text-white mb-2">Authentication Failed</h1>
                <p className="text-gray-300 mb-4">Please try connecting again</p>
              </div>
              
              <button
                onClick={() => router.replace(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/upstox`)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg transition-colors"
              >
                Try Authentication Again
              </button>
            </>
          )}
        </div>
      </div>
    </>
  )
}
