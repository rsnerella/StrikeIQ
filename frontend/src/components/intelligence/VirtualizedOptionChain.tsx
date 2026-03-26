import React, { memo, useMemo, useCallback, useState } from 'react';
import { FixedSizeList } from 'react-window';
import { OptionChainData } from '@/types/dashboard';
import { useWSStore } from '@/core/ws/wsStore';
import { useShallow } from 'zustand/react/shallow';

interface VirtualizedOptionChainProps {
  optionChainData: OptionChainData;
}

// Row component for virtualized list
const OptionRow = memo(({ index, style, data }: any) => {
  const item = data[index];
  if (!item) return null;

  return (
    <div style={style} className="flex items-center border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
      <div className={`w-16 text-xs font-mono px-2 py-1 text-right ${item.call_ltp > 0 ? 'text-green-400' : 'text-gray-600'}`}>
        {item.call_ltp > 0 ? item.call_ltp.toFixed(2) : '—'}
      </div>
      <div className="w-20 text-xs font-mono text-red-400 px-2 py-1 text-right">
        {item.call_oi > 0 ? (item.call_oi / 1000).toFixed(1) + 'k' : '—'}
      </div>
      <div className="flex-1 text-xs font-mono font-bold text-gray-200 px-2 py-1 text-center bg-gray-900/40">
        {item.strike}
      </div>
      <div className="w-20 text-xs font-mono text-green-400 px-2 py-1 text-right">
        {item.put_oi > 0 ? (item.put_oi / 1000).toFixed(1) + 'k' : '—'}
      </div>
      <div className={`w-16 text-xs font-mono px-2 py-1 text-right ${item.put_ltp > 0 ? 'text-green-400' : 'text-gray-600'}`}>
        {item.put_ltp > 0 ? item.put_ltp.toFixed(2) : '—'}
      </div>
    </div>
  );
});

OptionRow.displayName = 'OptionRow';

const VirtualizedOptionChain: React.FC<VirtualizedOptionChainProps> = memo(({ optionChainData }) => {

  const [selectedType, setSelectedType] = useState<'calls' | 'puts' | 'both'>('both');

  // ✅ REACTIVE WS STORE SUBSCRIPTION (CRITICAL FIX)
  const { wsLiveData, wsSnapshot } = useWSStore(
    useShallow(state => ({
      wsLiveData: state.liveMarketData,
      wsSnapshot: state.optionChainSnapshot
    }))
  );

  // ✅ PATCH: Validate REST data structure before using it (empty arrays are truthy)
  const hasValidRest =
    optionChainData &&
    optionChainData.calls &&
    optionChainData.puts &&
    optionChainData.calls.length > 0;

  const actualLiveData =
    hasValidRest
      ? optionChainData
      : wsLiveData ?? wsSnapshot ?? null;

  // ✅ THIS WILL NOW RE-RUN ON WS PAYLOAD
  const processedData = useMemo(() => {

    if (!actualLiveData) return { calls: [], puts: [], combined: [] };

    const calls = actualLiveData.calls || [];
    const puts = actualLiveData.puts || [];

    const strikeMap = new Map();

    calls.forEach((c: any) => {
      const existing = strikeMap.get(c.strike) || { strike: c.strike, call_oi: 0, put_oi: 0, total_oi: 0, call_ltp: 0, put_ltp: 0 };
      strikeMap.set(c.strike, {
        ...existing,
        call_oi: c.open_interest || c.oi || 0,
        call_ltp: c.ltp || c.last_price || 0,
        total_oi: existing.total_oi + (c.open_interest || c.oi || 0)
      });
    });

    puts.forEach((p: any) => {
      const existing = strikeMap.get(p.strike) || { strike: p.strike, call_oi: 0, put_oi: 0, total_oi: 0, call_ltp: 0, put_ltp: 0 };
      strikeMap.set(p.strike, {
        ...existing,
        put_oi: p.open_interest || p.oi || 0,
        put_ltp: p.ltp || p.last_price || 0,
        total_oi: existing.total_oi + (p.open_interest || p.oi || 0)
      });
    });

    const totalOI = Array.from(strikeMap.values()).reduce((s: any, i: any) => s + i.total_oi, 0);

    const combined = Array.from(strikeMap.values()).map((v: any) => ({
      ...v,
      oi_concentration: totalOI > 0 ? (v.total_oi / totalOI) * 100 : 0
    })).sort((a: any, b: any) => a.strike - b.strike);

    return { combined };

  }, [optionChainData, wsLiveData, wsSnapshot]);  // 🔥 IMPORTANT

  const filteredData = useMemo(() => processedData.combined, [processedData]);

  const getItemKey = useCallback((index: number) => {
    const item = filteredData[index];
    return `${item.strike}`;
  }, [filteredData]);

  if (!actualLiveData || filteredData.length === 0) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-8 text-center">
        <div className="text-gray-400">No option chain data available</div>
      </div>
    );
  }

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Option Chain</h3>
      </div>

      <div className="flex items-center border-b border-gray-700 pb-2 mb-2 bg-[#1A2235] rounded-t pt-2">
        <div className="w-16 text-[10px] font-bold text-gray-400 px-2 text-right uppercase tracking-wider">C. LTP</div>
        <div className="w-20 text-[10px] font-bold text-red-400 px-2 text-right uppercase tracking-wider">Call OI</div>
        <div className="flex-1 text-[11px] font-black text-white px-2 text-center uppercase tracking-widest bg-gray-800/50 rounded py-1 mx-2">Strike</div>
        <div className="w-20 text-[10px] font-bold text-green-400 px-2 text-right uppercase tracking-wider">Put OI</div>
        <div className="w-16 text-[10px] font-bold text-gray-400 px-2 text-right uppercase tracking-wider">P. LTP</div>
      </div>

      <div className="border border-gray-800 rounded">
        <FixedSizeList
          height={400}
          width="100%"
          itemCount={filteredData.length}
          itemSize={32}
          itemData={filteredData}
          itemKey={getItemKey}
        >
          {({ index, style }: any) => (
            <OptionRow index={index} style={style} data={filteredData} />
          )}
        </FixedSizeList>
      </div>
    </div>
  );
});

VirtualizedOptionChain.displayName = 'VirtualizedOptionChain';
export default VirtualizedOptionChain;