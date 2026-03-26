import type { AppProps } from 'next/app'
import { useEffect } from 'react'
import dynamic from 'next/dynamic'
import { useRouter } from 'next/router'

import { AuthProvider } from '@/contexts/AuthContext'

import AppBootstrapGuard from '@/components/AppBootstrapGuard'
// import RouteGuard from '@/components/RouteGuard'  // DISABLED
import ServiceInitializer from '@/components/ServiceInitializer'

import '@/styles/globals.css'

const Navbar = dynamic(() => import('@/components/layout/Navbar'), {
  ssr: false
})

function MyApp({ Component, pageProps }: AppProps) {

  const router = useRouter()

  const isAuthPage = router.pathname.startsWith('/auth')

  useEffect(() => {
    document.documentElement.classList.add('dark')
    
    // DEBUG: Log environment variables
    console.log('🌐 API URL:', process.env.NEXT_PUBLIC_API_URL);
    console.log('🌐 WS URL:', process.env.NEXT_PUBLIC_WS_URL);
    
    // DEBUG: Log any router changes
    console.log('🌐 _app.tsx - Current pathname:', router.pathname)
  }, [router.pathname])

  useEffect(() => {
    // DEBUG: Log when component mounts
    console.log('🌐 _app.tsx - Component mounted, pathname:', router.pathname)
  }, [])

  return (

    <AuthProvider>

      <AppBootstrapGuard>

        {/* <RouteGuard> */}  {/* DISABLED */}

          <ServiceInitializer>

            {!isAuthPage && <Navbar />}

            <Component {...pageProps} />

          </ServiceInitializer>

        {/* </RouteGuard> */}  {/* DISABLED */}

      </AppBootstrapGuard>

    </AuthProvider>

  )
}

export default MyApp