import React, { useEffect, useState } from 'react';
import { AlertTriangle, Info, AlertCircle, X, Bell, Activity } from 'lucide-react';
import { SectionLabel } from '../dashboard/StatCards';

interface Alert {
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
  metadata?: any;
}

interface AlertPanelProps {
  alerts: Alert[];
  maxVisible?: number;
}

const AlertPanel: React.FC<AlertPanelProps> = ({ alerts, maxVisible = 5 }) => {
  const [visibleAlerts, setVisibleAlerts] = useState<Alert[]>([]);
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

  useEffect(() => {
    const filtered = alerts
      .filter(alert => !dismissedAlerts.has(`${alert.alert_type}-${alert.timestamp}`))
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, maxVisible);

    setVisibleAlerts(filtered);
  }, [alerts, dismissedAlerts, maxVisible]);

  const getAlertStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          bg: 'bg-red-500/10',
          border: 'border-red-500/30',
          accent: 'bg-red-500',
          text: 'text-red-400',
          glow: 'alert-critical'
        };
      case 'high':
        return {
          bg: 'bg-orange-500/10',
          border: 'border-orange-500/30',
          accent: 'bg-orange-500',
          text: 'text-orange-400'
        };
      case 'medium':
        return {
          bg: 'bg-yellow-500/10',
          border: 'border-yellow-500/30',
          accent: 'bg-yellow-500',
          text: 'text-yellow-400'
        };
      case 'low':
        return {
          bg: 'bg-blue-500/10',
          border: 'border-blue-500/30',
          accent: 'bg-blue-500',
          text: 'text-blue-400'
        };
      default:
        return {
          bg: 'bg-slate-500/10',
          border: 'border-slate-500/30',
          accent: 'bg-slate-500',
          text: 'text-slate-400'
        };
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'high': return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'medium': return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      case 'low': return <Info className="w-4 h-4 text-blue-400" />;
      default: return <Info className="w-4 h-4 text-slate-400" />;
    }
  };

  const dismissAlert = (alert: Alert) => {
    const key = `${alert.alert_type}-${alert.timestamp}`;
    setDismissedAlerts(prev => new Set([...prev, key]));
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (visibleAlerts.length === 0) {
    return (
      <div className="trading-panel p-4 flex items-center justify-between group">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center">
            <Activity className="w-4 h-4 text-green-500" />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-black font-mono tracking-widest text-slate-500 uppercase">System Status</span>
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
    <div className="trading-panel p-6 relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
        <Bell className="w-24 h-24 text-white rotate-12" />
      </div>

      <div className="flex items-center justify-between mb-6 relative z-10">
        <div className="flex flex-col gap-1">
          <SectionLabel>Structural Alerts</SectionLabel>
          <span className="text-[10px] font-bold font-mono tracking-widest text-slate-600 uppercase">Intelligence Stream Active</span>
        </div>
        <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10">
          <span className="text-[10px] font-black font-mono text-slate-400 uppercase tracking-widest">
            {visibleAlerts.length} Active Events
          </span>
        </div>
      </div>

      <div className="space-y-3 relative z-10">
        {visibleAlerts.map((alert) => {
          const styles = getAlertStyles(alert.severity);
          return (
            <div
              key={`${alert.alert_type}-${alert.timestamp}`}
              className={`
                relative p-4 rounded-xl border transition-all duration-300 group/alert
                ${styles.bg} ${styles.border} ${styles.glow || ''}
                hover:bg-white/[0.04]
              `}
            >
              <div className="flex items-start gap-4">
                <div className={`mt-0.5 p-2 rounded-lg bg-black/20 border ${styles.border}`}>
                  {getSeverityIcon(alert.severity)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] font-black font-mono px-2 py-0.5 rounded uppercase tracking-wider ${styles.text} bg-black/40`}>
                        {alert.severity}
                      </span>
                      <span className="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">
                        {alert.alert_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <span className="text-[10px] font-bold font-mono text-slate-600 tabular-nums">
                      {formatTimestamp(alert.timestamp)}
                    </span>
                  </div>

                  <div className="text-sm font-bold text-white/90 leading-tight">
                    {alert.message}
                  </div>
                </div>

                <button
                  onClick={() => dismissAlert(alert)}
                  className="p-1.5 rounded-lg opacity-0 group-hover/alert:opacity-100 hover:bg-white/10 transition-all text-slate-500 hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {alerts.length > maxVisible && (
        <div className="mt-4 pt-4 border-t border-white/5 flex justify-center">
          <span className="text-[10px] font-black font-mono text-slate-600 uppercase tracking-[0.2em]">
            +{alerts.length - maxVisible} more events in buffer
          </span>
        </div>
      )}
    </div>
  );
};

export default AlertPanel;
