"use client";
import React from 'react';
import { Target, Magnet, TrendingUp, Calendar, Activity } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface ExpiryMagnetPanelProps {
    data: LiveMarketData | null;
}

export function ExpiryMagnetPanel({ data }: ExpiryMagnetPanelProps) {
    // Extract expiry magnet data from backend
    const expiryMagnet = (data as any)?.intelligence?.expiry_magnet_analysis || {};
    const magnetStrike = expiryMagnet.magnet_strike || 0;
    const pinProbability = expiryMagnet.pin_probability || 0;
    const distanceFromStrike = expiryMagnet.distance_from_strike || 0;
    const spot = (data as any)?.spot || 0;
    const daysToExpiry = expiryMagnet.days_to_expiry || 0;

    // Get pin probability level
    const getPinProbabilityLevel = (probability: number) => {
        if (probability >= 70) return { label: 'CRITICAL', color: '#f87171', bgColor: 'rgba(239,68,68,0.12)', borderColor: 'rgba(239,68,68,0.25)' };
        if (probability >= 50) return { label: 'HIGH', color: '#fb923c', bgColor: 'rgba(251,146,60,0.12)', borderColor: 'rgba(251,146,60,0.25)' };
        if (probability >= 30) return { label: 'MODERATE', color: '#60a5fa', bgColor: 'rgba(59,130,246,0.12)', borderColor: 'rgba(59,130,246,0.25)' };
        return { label: 'STABLE', color: '#4ade80', bgColor: 'rgba(34,197,94,0.12)', borderColor: 'rgba(34,197,94,0.25)' };
    };

    const pinLevel = getPinProbabilityLevel(pinProbability);

    // Calculate magnet strength based on OI concentration
    const calculateMagnetStrength = () => {
        let strength = 0;
        if (pinProbability >= 70) strength += 40;
        else if (pinProbability >= 50) strength += 25;
        else if (pinProbability >= 30) strength += 15;
        const distancePercent = Math.abs(distanceFromStrike) / 100;
        if (distancePercent < 0.2) strength += 30;
        else if (distancePercent < 0.5) strength += 20;
        else if (distancePercent < 1.0) strength += 10;
        if (daysToExpiry <= 1) strength += 30;
        else if (daysToExpiry <= 3) strength += 20;
        else if (daysToExpiry <= 7) strength += 10;
        return Math.min(100, strength);
    };

    const magnetStrength = calculateMagnetStrength();

    // Get magnet direction
    const getMagnetDirection = () => {
        if (Math.abs(distanceFromStrike) < 5) {
            return {
                label: 'PINNED',
                color: '#f87171',
                icon: <Magnet className="w-4 h-4" />,
                message: 'Price pinning at magnet zone'
            };
        } else if (spot < magnetStrike) {
            return {
                label: 'BULLISH PULL',
                color: '#4ade80',
                icon: <TrendingUp className="w-4 h-4" />,
                message: 'Upward magnetic attraction'
            };
        } else {
            return {
                label: 'BEARISH PULL',
                color: '#f87171',
                icon: <TrendingUp className="w-4 h-4 rotate-180" />,
                message: 'Downward magnetic attraction'
            };
        }
    };

    const magnetDirection = getMagnetDirection();

    // Get expiry urgency
    const getExpiryUrgency = (days: number) => {
        if (days <= 1) return { label: 'EXPIRY TODAY', color: '#f87171' };
        if (days <= 3) return { label: 'NEAR EXPIRY', color: '#fb923c' };
        if (days <= 7) return { label: 'THIS WEEK', color: '#60a5fa' };
        return { label: 'FUTURE EXP.', color: '#4ade80' };
    };

    const expiryUrgency = getExpiryUrgency(daysToExpiry);

    return (
        <div
            className="trading-panel h-full"
            onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = CARD_HOVER_BORDER;
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
            }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <SectionLabel>Expiry Magnet</SectionLabel>
                <div className="flex items-center gap-2">
                    <span
                        className="text-[10px] font-bold font-mono tracking-widest px-3 py-1 rounded-full flex items-center gap-2 uppercase"
                        style={{
                            background: `${expiryUrgency.color}15`,
                            border: `1px solid ${expiryUrgency.color}30`,
                            color: expiryUrgency.color,
                            boxShadow: `0 0 10px ${expiryUrgency.color}10`
                        }}
                    >
                        <Calendar className="w-3.5 h-3.5" />
                        {expiryUrgency.label}
                    </span>
                </div>
            </div>

            {/* Magnet Strike Visualization */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Magnetic Strike Zone
                    </span>
                    <span className="text-[16px] font-bold font-mono tracking-tight text-blue-400" style={{ textShadow: '0 0 10px rgba(96,165,250,0.3)' }}>
                        {magnetStrike.toFixed(0)}
                    </span>
                </div>

                {/* Strike Visualization */}
                <div className="relative h-6 rounded-full overflow-hidden border border-white/5" style={{ background: 'rgba(255,255,255,0.04)' }}>
                    {/* Magnetic field effect */}
                    <div
                        className="absolute inset-y-0 opacity-40"
                        style={{
                            left: '50%',
                            width: '40%',
                            transform: 'translateX(-50%)',
                            background: 'radial-gradient(circle, rgba(59,130,246,0.6) 0%, transparent 80%)',
                            animation: 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                        }}
                    />

                    {/* Magnet zone indicator */}
                    <div
                        className="absolute top-0 bottom-0 w-1 bg-blue-400 z-10"
                        style={{ left: '50%', transform: 'translateX(-50%)', boxShadow: '0 0 12px #60a5fa' }}
                    />

                    {/* Current spot pointer */}
                    <div
                        className="absolute top-1 bottom-1 w-1.5 bg-white z-20 rounded-full transition-all duration-700 ease-out"
                        style={{
                            left: spot < magnetStrike ? '25%' : spot > magnetStrike ? '75%' : '50%',
                            transform: 'translateX(-50%)',
                            boxShadow: '0 0 8px #fff'
                        }}
                    />
                </div>

                <div className="flex justify-between mt-2">
                    <span className="text-[9px] font-bold font-mono tracking-widest text-blue-500/50 uppercase">Strike Center</span>
                    <span className="text-[9px] font-bold font-mono tracking-widest text-slate-500 uppercase">
                        Spot: {spot.toFixed(1)}
                    </span>
                </div>
            </div>

            {/* Pin Probability */}
            <div className="mb-6 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Pinning Probability
                    </span>
                    <div className="flex items-center gap-3">
                        <span
                            className="text-[16px] font-bold font-mono tracking-tight"
                            style={{ color: pinLevel.color, textShadow: `0 0 10px ${pinLevel.color}30` }}
                        >
                            {pinProbability.toFixed(0)}%
                        </span>
                        <span
                            className="text-[9px] font-bold font-mono px-2 py-0.5 rounded tracking-widest uppercase border"
                            style={{
                                background: pinLevel.bgColor,
                                borderColor: pinLevel.borderColor,
                                color: pinLevel.color
                            }}
                        >
                            {pinLevel.label}
                        </span>
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                    <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                            width: `${pinProbability}%`,
                            background: `linear-gradient(90deg, #1e293b, ${pinLevel.color})`,
                        }}
                    />
                </div>
            </div>

            {/* Distance and Direction Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Gap to Pin
                    </div>
                    <div className="text-xl font-bold text-white tabular-nums tracking-tight">
                        {Math.abs(distanceFromStrike).toFixed(1)}
                        <span className="text-[10px] ml-1 text-slate-500">PTS</span>
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-blue-500/50 uppercase">
                        {distanceFromStrike > 0 ? 'TRADING ABOVE' : distanceFromStrike < 0 ? 'TRADING BELOW' : 'LOCKED AT PIN'}
                    </div>
                </div>

                <div
                    className="rounded-xl p-4 flex flex-col gap-1 transition-all hover:bg-white/5"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="text-[10px] font-bold font-mono tracking-wider uppercase text-slate-500">
                        Market Bias
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                        <span style={{ color: magnetDirection.color }} className="animate-pulse">
                            {magnetDirection.icon}
                        </span>
                        <span
                            className="text-[13px] font-bold font-mono tracking-widest uppercase"
                            style={{ color: magnetDirection.color }}
                        >
                            {magnetDirection.label}
                        </span>
                    </div>
                    <div className="text-[9px] font-bold font-mono tracking-widest mt-1 text-slate-600 uppercase">
                        OI ATTRACTION
                    </div>
                </div>
            </div>

            {/* Analysis Footer */}
            <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
                        <Target className="w-4 h-4 text-blue-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-bold font-mono tracking-widest text-blue-400 uppercase mb-0.5">
                            Magnet Strength: {magnetStrength.toFixed(0)}%
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 truncate">
                            {magnetDirection.message}
                        </div>
                    </div>
                </div>

                <div className="text-[10px] font-bold font-mono tracking-widest text-center py-2 px-3 rounded-lg bg-white/2 border border-white/5 uppercase opacity-80">
                    {pinProbability >= 70
                        ? '🧲 CRITICAL PINNING - EXPECT CHOPPY RANGE-BOUND'
                        : pinProbability >= 50
                            ? '🎯 MODERATE ATTRACTION - WATCH FOR GRAVITY'
                            : '✅ WEAK INFLUENCE - PRICE ACTION DOMINANT'
                    }
                </div>
            </div>
        </div>
    );
}

export default React.memo(ExpiryMagnetPanel);
