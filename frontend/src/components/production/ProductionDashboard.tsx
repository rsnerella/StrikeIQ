/**
 * Production Dashboard Component for StrikeIQ
 * Stable dashboard that renders regardless of WebSocket/market state
 */

import React, { useState, useEffect } from 'react';
import MarketStatus from './MarketStatus';
import { useWSStore } from '../../core/ws/wsStore';
import { useShallow } from 'zustand/shallow';

const ProductionDashboard: React.FC = () => {
  // PERFORMANCE: Use grouped selectors to prevent unnecessary re-renders
  const { connected, marketOpen, lastMessage } = useWSStore(
    useShallow(state => ({
      connected: state.connected,
      marketOpen: state.marketOpen,
      lastMessage: state.lastMessage
    }))
  )

  // Default market state (stable even without WebSocket)
  const displayMarketOpen = marketOpen;
  const displayConnected = connected;

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">StrikeIQ Trading Dashboard</h1>
        
        {/* Status Bar */}
        <div className="flex items-center justify-between bg-slate-800 rounded-lg p-4">
          <div className="flex items-center space-x-6">
            <MarketStatus />
            
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-400">Market:</span>
              <span className={`text-sm font-medium ${displayMarketOpen ? 'text-green-500' : 'text-red-500'}`}>
                {displayMarketOpen ? 'OPEN' : 'CLOSED'}
              </span>
            </div>
          </div>
          
          <div className="text-sm text-gray-400">
            Last Update: {lastMessage?.timestamp ? new Date(lastMessage.timestamp).toLocaleTimeString() : 'Never'}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Data Panel */}
        <div className="bg-slate-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Market Data</h2>
          
          {!displayConnected ? (
            <div className="text-center py-8">
              <div className="text-yellow-500 mb-2">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <p className="text-gray-400">Market feed connecting...</p>
              <p className="text-sm text-gray-500 mt-2">
                Real-time data will appear when connection is established
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-400">Status:</span>
                <span className="text-green-500">Connected</span>
              </div>
              
              {lastMessage && (
                <div className="border-t border-slate-700 pt-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Latest Update</h3>
                  <div className="bg-slate-900 rounded p-3">
                    <pre className="text-xs text-gray-300 overflow-x-auto">
                      {JSON.stringify(lastMessage, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Trading Panel */}
        <div className="bg-slate-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Trading Intelligence</h2>
          
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-400">Market Status:</span>
              <span className={displayMarketOpen ? 'text-green-500' : 'text-red-500'}>
                {displayMarketOpen ? 'Active' : 'Closed'}
              </span>
            </div>
            
            <div className="flex justify-between">
              <span className="text-gray-400">Signals:</span>
              <span className="text-blue-500">Waiting for data...</span>
            </div>
            
            <div className="flex justify-between">
              <span className="text-gray-400">Analytics:</span>
              <span className="text-purple-500">Processing...</span>
            </div>
          </div>
          
          {!displayConnected && (
            <div className="mt-6 p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg">
              <p className="text-yellow-500 text-sm">
                ⚠️ Real-time features are limited while disconnected
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Connection Info */}
      <div className="mt-8 bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-2">Connection Details</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Connected:</span>
            <span className={`ml-2 ${displayConnected ? 'text-green-500' : 'text-red-500'}`}>
              {displayConnected ? 'Yes' : 'No'}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Attempts:</span>
            <span className="ml-2 text-white">0</span>
          </div>
          <div>
            <span className="text-gray-500">Error:</span>
            <span className="ml-2 text-white">None</span>
          </div>
          <div>
            <span className="text-gray-500">Messages:</span>
            <span className="ml-2 text-white">{lastMessage ? '1' : '0'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductionDashboard;
