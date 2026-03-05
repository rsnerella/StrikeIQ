import React, { useState, useEffect } from 'react';
import { Clock, Wifi, WifiOff } from 'lucide-react';
import api from '../../lib/api';

// Updated interface for new API
interface MarketStatusData {
  status: 'OPEN' | 'PREOPEN' | 'CLOSED' | 'UNKNOWN';
}

const MarketStatusBanner: React.FC = () => {
  const [marketStatus, setMarketStatus] = useState<'OPEN' | 'PREOPEN' | 'CLOSED' | 'UNKNOWN'>('UNKNOWN');
  const [backendConnected, setBackendConnected] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMarketStatus = async () => {
      try {
        const response = await api.get('/api/v1/market/status');
        if (response.data && response.data.status) {
          setMarketStatus(response.data.status as 'OPEN' | 'PREOPEN' | 'CLOSED' | 'UNKNOWN');
          setBackendConnected(true);
        }
      } catch (error) {
        console.error('Error fetching market status:', error);
        setBackendConnected(false);
        setMarketStatus('UNKNOWN');
      } finally {
        setLoading(false);
      }
    };

    fetchMarketStatus();
    const interval = setInterval(fetchMarketStatus, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-3 h-3 bg-gray-500 rounded-full animate-pulse"></div>
            <span className="text-gray-400 text-sm">Loading market status...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!backendConnected || marketStatus === 'UNKNOWN') {
    return (
      <div className="bg-red-900/20 border-b border-red-800/50 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span className="text-red-400 text-sm">Backend Offline</span>
          </div>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OPEN': return { bg: 'bg-green-900/20 border-green-800/50', dot: 'bg-green-500', text: 'text-green-400', label: '🟢 MARKET OPEN' };
      case 'PREOPEN': return { bg: 'bg-yellow-900/20 border-yellow-800/50', dot: 'bg-yellow-500', text: 'text-yellow-400', label: '🟡 PRE-OPEN' };
      case 'CLOSED': return { bg: 'bg-red-900/20 border-red-800/50', dot: 'bg-red-500', text: 'text-red-400', label: '🔴 MARKET CLOSED' };
      default: return { bg: 'bg-gray-900/20 border-gray-800/50', dot: 'bg-gray-500', text: 'text-gray-400', label: '⚪ UNKNOWN' };
    }
  };

  const statusStyle = getStatusColor(marketStatus);

  return (
    <div className={`${statusStyle.bg} border-b px-6 py-3`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6">
          {/* Market Status */}
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${statusStyle.dot}`}></div>
            <span className={`text-sm font-medium ${statusStyle.text}`}>
              {statusStyle.label}
            </span>
          </div>

          {/* Server Time - Fallback since new API doesn't provide it */}
          <div className="flex items-center space-x-2 text-gray-400">
            <Clock className="w-4 h-4" />
            <span className="text-sm">
              {new Date().toLocaleString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour12: true,
                hour: '2-digit',
                minute: '2-digit'
              })} IST
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketStatusBanner;
