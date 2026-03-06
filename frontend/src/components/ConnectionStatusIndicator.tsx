import React from 'react';
import { useConnectionGuard } from '../utils/connectionGuard';

/**
 * React component for connection status indicator
 */
export function ConnectionStatusIndicator() {
  const { isConnected, isReconnecting, reconnectAttempts, lastError } = useConnectionGuard();

  console.log("WS TRACE → UI RENDER", {
    isConnected,
    wsGlobal: (window as any).__WS_CONNECTED__
  });

  if (isConnected) {
    return (
      <div className="flex items-center gap-2 text-green-500">
        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
        <span className="text-xs">CONNECTED</span>
      </div>
    );
  }

  if (isReconnecting) {
    return (
      <div className="flex items-center gap-2 text-yellow-500">
        <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
        <span className="text-xs">
          RECONNECTING... ({reconnectAttempts})
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-red-500">
      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
      <span className="text-xs">
        DISCONNECTED {lastError ? `(${lastError})` : ''}
      </span>
    </div>
  );
}

export default ConnectionStatusIndicator;
