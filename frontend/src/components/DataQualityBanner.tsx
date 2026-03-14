import React from 'react'
import { useMarketStore } from '@/stores/marketStore'

export const DataQualityBanner: React.FC = () => {
  const dataQuality = useMarketStore((s) => s.dataQuality)

  if (!dataQuality) return null

  if (dataQuality.source === 'full') {
    return (
      <div className="w-full bg-green-900/20 border-b border-green-800/40
                      text-green-400 text-xs px-4 py-1.5 flex items-center gap-2">
        <span>●</span>
        <span>Live feed active — LTP · OI · Greeks · Bid/Ask all streaming</span>
      </div>
    )
  }

  if (dataQuality.source === 'ltp_only') {
    return (
      <div className="w-full bg-yellow-900/20 border-b border-yellow-800/40
                      text-yellow-400 text-xs px-4 py-1.5 flex items-center gap-2">
        <span>⚠</span>
        <span>
          LTP streaming — OI and Greeks loading via REST fallback (2s refresh).
          Verify Upstox Plus subscription mode is active.
        </span>
      </div>
    )
  }

  return (
    <div className="w-full bg-gray-800/40 border-b border-gray-700/40
                    text-gray-500 text-xs px-4 py-1.5 flex items-center gap-2">
      <span className="animate-pulse">●</span>
      <span>Connecting to market feed...</span>
    </div>
  )
}
