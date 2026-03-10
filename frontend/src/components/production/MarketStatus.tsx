/**
 * Production Market Status Component for StrikeIQ
 * Stable UI that doesn't break on WebSocket failures
 */

import React from 'react';
import { useWSStore } from '../../core/ws/wsStore';

interface MarketStatusProps {
  className?: string;
}

const MarketStatus: React.FC<MarketStatusProps> = ({ className = '' }) => {
  // PERFORMANCE: Use proper selector to prevent unnecessary re-renders
  const connected = useWSStore(state => state.connected);

  const getStatusColor = () => {
    if (connected) return 'text-green-500';
    return 'text-red-500';
  };

  const getStatusText = () => {
    if (connected) return 'Connected';
    return 'Disconnected';
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${getStatusColor()}`}></div>
      <span className={`text-sm ${getStatusColor()}`}>
        {getStatusText()}
      </span>
    </div>
  );
};

export default MarketStatus;
