/**
 * Market Data Display Component
 * Shows live market data from WebSocket store
 */

import React from 'react';
import { useMarketData } from '@/hooks/useMarketData';

export function MarketDataDisplay() {
  const { data, isConnected, error, loading } = useMarketData();

  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Market Data</h3>
        <div className={`px-2 py-1 rounded text-xs font-semibold ${
          isConnected ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>
      
      {loading && (
        <div className="mb-4 p-2 bg-blue-900/50 rounded-lg">
          <div className="text-blue-300 text-sm">Loading market data...</div>
        </div>
      )}
      
      {error && (
        <div className="mb-4 p-2 bg-red-900/50 rounded-lg">
          <div className="text-red-300 text-sm">Error: {error}</div>
        </div>
      )}
      
      {!data && !loading && (
        <div className="mb-4 p-2 bg-gray-700 rounded-lg">
          <div className="text-gray-400 text-sm">No market data available</div>
        </div>
      )}
      
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">Symbol:</span>
          <span className="text-white font-mono">{data?.symbol || 'NIFTY'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Spot:</span>
          <span className="text-white font-mono">{data?.spot ?? 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Expected Move:</span>
          <span className="text-white font-mono">{data?.expected_move ?? 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Regime:</span>
          <span className="text-white font-mono">{data?.structural_regime ?? 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Regime Confidence:</span>
          <span className="text-white font-mono">{data?.regime_confidence ?? 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Last Update:</span>
          <span className="text-white font-mono text-xs">
            {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : 'N/A'}
          </span>
        </div>
      </div>

      {/* Debug: Show raw data */}
      <div className="mt-4 p-2 bg-black rounded">
        <div className="text-xs text-gray-400 mb-1">Debug - Raw Data:</div>
        <pre className="text-xs text-green-400 overflow-auto max-h-32">
          {JSON.stringify(data ?? {}, null, 2)}
        </pre>
      </div>
    </div>
  );
}
