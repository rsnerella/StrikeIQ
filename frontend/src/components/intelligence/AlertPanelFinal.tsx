import React, { useEffect, useState, memo } from 'react';
import { AlertTriangle, Info, AlertCircle, X, Bell, Activity } from 'lucide-react';
import { SectionLabel } from '../dashboard/StatCards';
import { useWSStore } from '@/core/ws/wsStore';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

const AlertPanel: React.FC = () => {
    // Law 7: Granular Store Subscriptions
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;
    const analysis = useWSStore(s => s.chartAnalysis);
    const alerts = analysis?.events || [];
    
    const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

    useEffect(() => {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes alert-glow {
                0%, 100% { box-shadow: 0 0 15px rgba(239, 68, 68, 0.1); }
                50% { box-shadow: 0 0 25px rgba(239, 68, 68, 0.3); }
            }
            .alert-critical { animation: alert-glow 2s ease-in-out infinite; }
        `;
        document.head.appendChild(style);
        return () => { 
            if (document.head.contains(style)) {
                document.head.removeChild(style);
            }
        };
    }, []);

    const visibleAlerts = alerts
        .filter(a => !dismissedAlerts.has(`${a.type}-${a.timestamp}`))
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        .slice(0, 5);

    const getAlertStyles = (severity: string) => {
        switch (severity.toLowerCase()) {
            case 'critical': return { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', glow: 'alert-critical' };
            case 'high': return { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400' };
            case 'medium': return { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400' };
            default: return { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400' };
        }
    };

    const formatTimestamp = (ts: string) => {
        const diff = Date.now() - new Date(ts).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'JUST NOW';
        if (mins < 60) return `${mins}M AGO`;
        return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    if (!hasData) {
        return (
            <div className="flex items-center justify-between p-2 opacity-40">
                <div className="flex items-center gap-4">
                    <SkeletonPulse className="w-8 h-8 rounded-lg" />
                    <SkeletonPulse className="w-48 h-4" />
                </div>
                <SkeletonPulse className="w-24 h-6 rounded-full" />
            </div>
        );
    }

    if (visibleAlerts.length === 0) {
        return (
            <div className="flex items-center justify-between p-2 group">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                        <Activity className="w-4 h-4 text-green-500" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[9px] font-black font-mono tracking-widest text-slate-500 uppercase">System Status</span>
                        <span className="text-xs font-bold text-green-500 uppercase tracking-tighter">No Active Anomalies Detected</span>
                    </div>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[9px] font-black font-mono text-green-500 uppercase">Live monitoring</span>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between mb-2">
                <SectionLabel>Structural Alerts</SectionLabel>
                <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10">
                    <span className="text-[10px] font-black font-mono text-slate-500 uppercase tracking-widest">
                        {visibleAlerts.length} Active Events
                    </span>
                </div>
            </div>

            <div className="space-y-2">
                {visibleAlerts.map((alert, idx) => {
                    const styles = getAlertStyles(alert.severity);
                    return (
                        <div key={idx} className={`relative p-3 rounded-xl border transition-all duration-300 ${styles.bg} ${styles.border} ${styles.glow || ''} hover:bg-white/[0.04]`}>
                            <div className="flex items-start gap-3">
                                <div className={`mt-0.5 p-1.5 rounded-lg bg-black/20 border ${styles.border}`}>
                                    {alert.severity === 'critical' || alert.severity === 'high' ? <AlertTriangle className={`w-3.5 h-3.5 ${styles.text}`} /> : <Info className={`w-3.5 h-3.5 ${styles.text}`} />}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className={`text-[8px] font-black font-mono px-1.5 py-0.5 rounded uppercase ${styles.text} bg-black/40`}>{alert.severity}</span>
                                        <span className="text-[9px] font-bold font-mono text-slate-600 tabular-nums">{formatTimestamp(alert.timestamp)}</span>
                                    </div>
                                    <div className="text-xs font-bold text-white/90 leading-tight uppercase tracking-tight">{alert.message}</div>
                                </div>
                                <button
                                    onClick={() => setDismissedAlerts(prev => new Set([...prev, `${alert.type}-${alert.timestamp}`]))}
                                    className="p-1 rounded-lg hover:bg-white/10 text-slate-500 hover:text-white transition-all"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default memo(AlertPanel);
