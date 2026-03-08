import React, { useEffect, useState } from "react";
import AuthScreen from "../../components/AuthScreen";
import { AuthRequiredData } from "../../types/dashboard";
import { useAuthStore, useAuthStatus } from "../../stores/authStore";
import { useRouter } from "next/navigation";

export default function AuthPage() {
  const authStatus = useAuthStatus()
  const { checkAuth } = useAuthStore()
  const [authData, setAuthData] = useState<AuthRequiredData | null>(null)
  const router = useRouter()

  useEffect(() => {
    // Always show auth page - no auto-redirect logic
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get("error");
    const message =
      urlParams.get("message") ||
      "Authentication required to access market data";

    const defaultAuthData: AuthRequiredData = {
      session_type: "AUTH_REQUIRED",
      mode: "AUTH",
      login_url:
        `https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=53c878a9-3f5d-44f9-aa2d-2528d34a24cd&redirect_uri=http://${window.location.hostname}:8000/api/v1/auth/upstox/callback`,
      message: error || message,
      timestamp: new Date().toISOString(),
    };

    setAuthData(defaultAuthData);
  }, []);

  // Show loading while auth check is in progress
  if (authStatus === 'loading') {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-white text-center">
          <div className="w-16 h-16 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!authData) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-white text-center">
          <p>Preparing login...</p>
        </div>
      </div>
    );
  }

  return <AuthScreen authData={authData} />;
}