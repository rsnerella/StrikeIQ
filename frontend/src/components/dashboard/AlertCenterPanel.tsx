"use client";
import React, { useState, useEffect } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Activity, Zap, Shield } from 'lucide-react';
import { CARD, CARD_HOVER_BORDER } from './DashboardTypes';
import { SectionLabel } from './StatCards';
import type { LiveMarketData } from '../../hooks/useLiveMarketData';

interface AlertCenterPanelProps {
    data: LiveMarketData | null;
}

interface Alert {
    id: string;
    type: 'warning' | 'danger' | 'info';
    icon: React.ReactNode;
    title: string;
    description: string;
    timestamp: number;
}

export function AlertCenterPanel({ data }: AlertCenterPanelProps) {
    const [alerts, setAlerts] = useState<Alert[]>([]);

    // Extract alert data from backend
    const backendAlerts = (data as any)?.intelligence?.alerts || [];
    const breachProbability = (data as any)?.intelligence?.breach_probability || 0;
    const gammaFlipLevel = (data as any)?.intelligence?.gamma_flip_level || 0;
    const spot = (data as any)?.spot || 0;
    const volatilityRegime = (data as any)?.intelligence?.volatility_regime || 'normal';
    const flowImbalance = (data as any)?.intelligence?.flow_imbalance || 0;
    const intentScore = (data as any)?.intelligence?.intent_score || 0;

    // Generate alerts based on backend analytics
    useEffect(() => {
        const generatedAlerts: Alert[] = [];

        // Backend alerts
        backendAlerts.forEach((alert: any, index: number) => {
            generatedAlerts.push({
                id: `backend-${index}`,
                type: alert.severity === 'high' ? 'danger' : 'warning',
                icon: <AlertTriangle className="w-4 h-4" />,
                title: alert.title || 'System Alert',
                description: alert.message || 'Alert detected',
                timestamp: Date.now() - index * 1000
            });
        });

        // Gamma flip alert
        const distanceToFlip = Math.abs(spot - gammaFlipLevel);
        if (distanceToFlip < 50 && gammaFlipLevel > 0) {
            generatedAlerts.push({
                id: 'gamma-flip',
                type: 'warning',
                icon: <Zap className="w-4 h-4" />,
                title: 'Gamma Flip Nearby',
                description: `Approaching critical flip level at ${gammaFlipLevel.toFixed(0)}`,
                timestamp: Date.now()
            });
        }

        // Breakout probability alert
        if (breachProbability > 60) {
            generatedAlerts.push({
                id: 'breakout-probability',
                type: breachProbability > 80 ? 'danger' : 'warning',
                icon: <TrendingUp className="w-4 h-4" />,
                title: 'Breakout Probability',
                description: `${breachProbability.toFixed(0)}% chance of range breach detected`,
                timestamp: Date.now()
            });
        }

        // Volatility spike alert
        if (volatilityRegime === 'extreme') {
            generatedAlerts.push({
                id: 'volatility-spike',
                type: 'danger',
                icon: <Activity className="w-4 h-4" />,
                title: 'Volatility Spike',
                description: 'Extreme volatility regime - high risk conditions',
                timestamp: Date.now()
            });
        }

        // Institutional flow alert
        if (Math.abs(flowImbalance) > 0.4) {
            generatedAlerts.push({
                id: 'institutional-flow',
                type: 'info',
                icon: <TrendingDown className="w-4 h-4" />,
                title: 'Smart Money Flow',
                description: `Strong ${flowImbalance > 0 ? 'call' : 'put'} accumulation detected`,
                timestamp: Date.now()
            });
        }

        // High institutional intent alert
        if (intentScore > 75) {
            generatedAlerts.push({
                id: 'high-intent',
                type: 'info',
                icon: <Shield className="w-4 h-4" />,
                title: 'Institutional Intent',
                description: `Activity score elevated at ${intentScore.toFixed(0)}%`,
                timestamp: Date.now()
            });
        }

        // Sort alerts by timestamp and limit to 5 most recent
        const sortedAlerts = generatedAlerts
            .sort((a, b) => b.timestamp - a.timestamp)
            .slice(0, 5);

        setAlerts(sortedAlerts);
    }, [backendAlerts, breachProbability, gammaFlipLevel, spot, volatilityRegime, flowImbalance, intentScore]);

    const getAlertColor = (type: string) => {
        switch (type) {
            case 'danger':
                return { bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.25)', color: '#f87171', shadow: '0 0 12px rgba(239,68,68,0.1)' };
            case 'warning':
                return { bg: 'rgba(251,146,60,0.08)', border: 'rgba(251,146,60,0.25)', color: '#fb923c', shadow: '0 0 12px rgba(251,146,60,0.1)' };
            case 'info':
                return { bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.25)', color: '#60a5fa', shadow: '0 0 12px rgba(59,130,246,0.1)' };
            default:
                return { bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.18)', color: '#94a3b8', shadow: 'none' };
        }
    };

    const formatTime = (timestamp: number) => {
        const now = Date.now();
        const diff = now - timestamp;
        if (diff < 60000) return 'NOW';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}M`;
        return `${Math.floor(diff / 3600000)}H`;
    };

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
                <SectionLabel>Risk Alerts</SectionLabel>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold font-mono tracking-widest text-slate-500 uppercase">
                        {alerts.length} ACTIVE
                    </span>
                    {alerts.length > 0 && (
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                        </span>
                    )}
                </div>
            </div>

            {/* Alerts List */}
            <div className="space-y-3">
                {alerts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 rounded-xl bg-white/2 border border-white/5 border-dashed">
                        <Shield className="w-10 h-10 mb-3 text-green-500/30" />
                        <div className="text-[11px] font-bold font-mono tracking-widest text-green-500/50 uppercase">
                            No Active Risks
                        </div>
                    </div>
                ) : (
                    alerts.map((alert) => {
                        const colors = getAlertColor(alert.type);
                        return (
                            <div
                                key={alert.id}
                                className="group rounded-xl p-3.5 flex items-start gap-3.5 transition-all duration-300 hover:bg-white/5"
                                style={{
                                    background: colors.bg,
                                    border: `1px solid ${colors.border}`,
                                    boxShadow: colors.shadow
                                }}
                            >
                                <div style={{ color: colors.color }} className="mt-0.5 opacity-80 group-hover:opacity-100 transition-opacity">
                                    {alert.icon}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-baseline justify-between mb-1">
                                        <span
                                            className="text-[11px] font-bold font-mono tracking-wider uppercase truncate"
                                            style={{ color: colors.color }}
                                        >
                                            {alert.title}
                                        </span>
                                        <span className="text-[9px] font-bold font-mono text-slate-500 shrink-0 ml-2">
                                            {formatTime(alert.timestamp)}
                                        </span>
                                    </div>
                                    <div className="text-[10px] font-mono leading-relaxed text-slate-400">
                                        {alert.description}
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Alert Summary */}
            {alerts.length > 0 && (
                <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] font-bold font-mono tracking-widest uppercase text-slate-600">
                        Signal Severity
                    </span>
                    <div className="flex items-center gap-4">
                        {[
                            { color: '#f87171', label: 'CRITICAL', active: alerts.some(a => a.type === 'danger') },
                            { color: '#fb923c', label: 'WARNING', active: !alerts.some(a => a.type === 'danger') && alerts.some(a => a.type === 'warning') },
                            { color: '#60a5fa', label: 'MONITOR', active: alerts.every(a => a.type === 'info') },
                        ].filter(z => z.active).map(z => (
                            <div key={z.label} className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: z.color }}></div>
                                <span className="text-[9px] font-bold font-mono tracking-widest" style={{ color: z.color }}>{z.label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

