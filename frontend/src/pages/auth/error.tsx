import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { AlertTriangle, RefreshCw, ExternalLink } from 'lucide-react';

export default function AuthError() {
  const router = useRouter();
  const [message, setMessage] = useState<string>('');
  const [isRedirecting, setIsRedirecting] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const errorMessage = urlParams.get('message') || 'unknown_error';
    setMessage(errorMessage);
  }, []);

  const handleRetryAuth = () => {
    setIsRedirecting(true);
    // Redirect to auth initiation using router.replace
    router.replace(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/upstox`);
  };

  const getErrorMessage = (msg: string) => {
    switch (msg) {
      case 'missing_state':
        return {
          title: 'Authentication State Missing',
          description: 'The authentication flow was interrupted. This can happen if you access the callback URL directly or if the session expired.',
          solution: 'Please restart the authentication process from the beginning.'
        };
      case 'invalid_state':
        return {
          title: 'Invalid Authentication State',
          description: 'The authentication state is invalid or has expired.',
          solution: 'Please restart the authentication process for security reasons.'
        };
      case 'csrf_detected':
        return {
          title: 'Security Check Failed',
          description: 'A potential security issue was detected with your authentication request.',
          solution: 'For your security, please restart the authentication process.'
        };
      default:
        return {
          title: 'Authentication Error',
          description: 'An error occurred during the authentication process.',
          solution: 'Please try again or contact support if the problem persists.'
        };
    }
  };

  const errorInfo = getErrorMessage(message);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white/10 backdrop-blur-md rounded-2xl shadow-2xl border border-white/20 p-8">
        <div className="text-center">
          {/* Error Icon */}
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>

          {/* Error Title */}
          <h1 className="text-2xl font-bold text-white mb-4">
            {errorInfo.title}
          </h1>

          {/* Error Description */}
          <p className="text-gray-300 mb-6">
            {errorInfo.description}
          </p>

          {/* Solution */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
            <p className="text-blue-300 text-sm">
              <strong>Solution:</strong> {errorInfo.solution}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <button
              onClick={handleRetryAuth}
              disabled={isRedirecting}
              className="w-full bg-analytics text-white py-3 px-6 rounded-lg font-semibold hover:bg-analytics/80 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRedirecting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Redirecting...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Restart Authentication
                </>
              )}
            </button>

            <button
              onClick={() => router.push('/')}
              className="w-full bg-white/10 text-white py-3 px-6 rounded-lg font-semibold hover:bg-white/20 transition-all duration-200 flex items-center justify-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Go to Dashboard
            </button>
          </div>

          {/* Technical Details */}
          <div className="mt-6 p-3 bg-black/20 rounded-lg">
            <p className="text-xs text-gray-400">
              Error Code: {message.toUpperCase()}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Timestamp: {new Date().toISOString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
