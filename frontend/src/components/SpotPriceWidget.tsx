import React from 'react';
import { useDashboardData } from '@/hooks/useDashboardData';

interface SpotPriceWidgetProps {
  symbol: string;
}

const SpotPriceWidget: React.FC<SpotPriceWidgetProps> = ({ symbol }) => {
  const { spot, connected } = useDashboardData();

  return (
    <div className="bg-gray-900 text-white p-4 rounded-lg">
      <h3 className="text-lg font-bold mb-2">{symbol} Spot Price</h3>
      <div className="text-2xl font-mono">
        {spot > 0 ? `₹${spot.toFixed(2)}` : 'Waiting for data'}
      </div>
      <div className="text-sm mt-2">
        Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>
    </div>
  );
};

export default SpotPriceWidget;
