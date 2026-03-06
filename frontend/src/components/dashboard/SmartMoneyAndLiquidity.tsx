"use client";
import React, { memo } from 'react';
import { Minus } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import { SmartMoneyPanel } from '../intelligence/SmartMoneyPanel';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

const MemoizedSmartMoney = memo(SmartMoneyPanel);

interface SmartMoneyAndLiquidityProps {
    data: LiveMarketData | null;
    isLiveMode: boolean;
    isSnapshotMode: boolean;
    mode: string;
}

export function SmartMoneyAndLiquidity({ data, isLiveMode, isSnapshotMode, mode }: SmartMoneyAndLiquidityProps) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">

            {/* Smart Money */}
            <div
                className="w-full rounded-2xl p-4 sm:p-5 transition-all duration-300"
                style={CARD}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = CARD_HOVER_BORDER)}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)')}
            >
                <div className="flex items-center justify-between mb-3">
                    <SectionLabel>Smart Money</SectionLabel>
                    {isSnapshotMode && (
                        <span
                            className="text-[10px] font-mono px-2 py-0.5 rounded-full"
                            style={{ color: '#60a5fa', background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.20)' }}
                        >
                            DISABLED
                        </span>
                    )}
                </div>
                <MemoizedSmartMoney smartMoneyData={(data as any)?.smart_money_activity ?? null} />
            </div>

            {/* Liquidity */}
            <div
                className="w-full rounded-2xl p-4 sm:p-5 transition-all duration-300"
                style={CARD}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = CARD_HOVER_BORDER)}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)')}
            >
                <SectionLabel>Liquidity</SectionLabel>
                <div className="mt-3 space-y-2.5">
                    {[
                        { label: 'Total OI', value: (((data as any)?.analytics?.total_call_oi || 0) + ((data as any)?.analytics?.total_put_oi || 0)).toLocaleString() },
                        { label: 'OI Change', value: ((data as any)?.analytics?.oi_change_24h?.toFixed(0) ?? '0') },
                        { label: 'Volume', value: (((data as any)?.analytics?.total_volume || 0)).toLocaleString() },
                        { label: 'VWAP', value: ((data as any)?.analytics?.vwap?.toFixed(2) ?? '0.00') },
                    ].map(({ label, value }) => (
                        <div key={label} className="flex justify-between items-center">
                            <span className="text-[11px] font-mono" style={{ color: 'rgba(148,163,184,0.55)' }}>{label}</span>
                            <span className="text-[11px] font-mono font-semibold text-white tabular-nums">{value}</span>
                        </div>
                    ))}
                </div>

                {/* Liquidity Pressure Meter */}
                <div className="mt-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-mono" style={{ color: 'rgba(148,163,184,0.55)' }}>Liquidity Pressure</span>
                        <span className="text-[11px] font-mono font-semibold text-white tabular-nums">
                           { ((data as any)?.analytics?.liquidity_pressure) ? `${(((data as any).analytics?.liquidity_pressure) * 100).toFixed(1)}%` : 'N/A'}
                        </span>
                    </div>
                    <div 
                        className="w-full h-2 rounded-full overflow-hidden"
                        style={{ 
                            background: 'linear-gradient(90deg, #00ff9d, #ffaa00, #ff4d4d)',
                            borderRadius: '4px'
                        }}
                    >
                        <div 
                            className="h-full bg-black/30 transition-all duration-300"
                            style={{ 
                                width: ((data as any)?.analytics?.liquidity_pressure) 
                                    ? `${Math.max(0, Math.min(100, (1 - ((data as any).analytics.liquidity_pressure) * 100)))}%` 
                                    : '0%' 
                            }}    
                        />
                    </div>
                    <div className="flex justify-between mt-1">
                        <span className="text-[10px] font-mono" style={{ color: '#00ff9d' }}>LOW</span>
                        <span className="text-[10px] font-mono" style={{ color: '#ffaa00' }}>MEDIUM</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
