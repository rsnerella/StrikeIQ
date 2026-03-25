import React, { useEffect, useState } from 'react';
import { Lock, AlertCircle } from 'lucide-react';
import Navbar from './layout/Navbar';

interface AuthData {
  session_type?: string;
  mode?: string;
  login_url?: string;
  message?: string;
  timestamp?: string;
}

interface AuthScreenProps {
  authData?: AuthData;
}

export default function AuthScreen({ authData }: AuthScreenProps) {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get auth data from URL params or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    const message = urlParams.get('message') || 'Authentication required to access market data';

    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a]">
        <Navbar />
        <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
          <div className="text-white text-center">
            <div className="w-16 h-16 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p>Loading authentication...</p>
          </div>
        </div>
      </div>
    );
  }

  // Use login_url from authData if available
  const loginUrl = authData?.login_url ||
    (typeof window !== "undefined"
      ? `https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=53c878a9-3f5d-44f9-aa2d-2528d34a24cd&redirect_uri=${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/upstox/callback`
      : `https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=53c878a9-3f5d-44f9-aa2d-2528d34a24cd&redirect_uri=${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/upstox/callback`);

  const displayMessage = authData?.message || 'Please authenticate to access StrikeIQ market intelligence';

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <Navbar />

      {/* Main Content */}
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)] px-4">
        <div className="max-w-md w-full">
          {/* Authentication Card */}
          <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-8 shadow-2xl">

            {/* Lock Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-orange-500/20 rounded-full flex items-center justify-center">
                <Lock size={32} className="text-orange-500" />
              </div>
            </div>

            {/* Title */}
            <h1 className="text-2xl font-bold text-white text-center mb-2">
              Authentication Required
            </h1>

            {/* Subtitle */}
            <p className="text-gray-400 text-center mb-8">
              Authentication required to access market data
            </p>

            {/* Session Expired Button */}
            <div className="flex items-center justify-center mb-6">
              <button className="flex items-center gap-2 px-4 py-2 bg-[#2a2a2a] hover:bg-[#333333] rounded-lg transition-colors">
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
                <span className="text-gray-300 text-sm">Session Expired</span>
              </button>
            </div>

            {/* Get Authorization Button */}
            <a
              href={loginUrl}
              className="block w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 px-6 rounded-lg transition-colors text-center"
            >
              Get Authorization
            </a>

            {/* Redirect Message */}
            <div className="mt-6 text-center">
              <p className="text-gray-500 text-sm">
                You will be redirected to the authorization server
              </p>
              <p className="text-gray-600 text-xs mt-1">
                After authentication, you will be redirected back to the application
              </p>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
