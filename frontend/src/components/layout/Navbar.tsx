"use client";

import React, { useState, useEffect } from "react";
import { Wifi, WifiOff, Heart, BarChart2, Link2, Activity, Bell } from "lucide-react";
import { useMarketStore } from "@/stores/marketStore";
import { uiLogger, traceManager } from "../../utils/logger";

const HEARTBEAT_CSS = `
@keyframes ws-heartbeat {
  0% { transform: scale(1); }
  10% { transform: scale(1.4); }
  20% { transform: scale(1); }
  30% { transform: scale(1.28); }
  40% { transform: scale(1); }
}

@keyframes ecg-scan {
  0% { stroke-dashoffset:120; opacity:0; }
  10% { opacity:1; }
  80% { opacity:1; }
  100% { stroke-dashoffset:0; opacity:0; }
}

@keyframes flatline-blink {
  0%,100% { opacity:0.25; }
  50% { opacity:0.5; }
}
`;

const NAV_TABS = [
  { id: "dashboard", sectionId: "section-dashboard", label: "Dashboard", icon: BarChart2 },
  { id: "chain", sectionId: "oi-heatmap", label: "Options Chain", icon: Link2 },
  { id: "analytics", sectionId: "section-analytics", label: "Analytics", icon: Activity },
  { id: "alerts", sectionId: "section-alerts", label: "Alerts", icon: Bell },
] as const;

type TabId = typeof NAV_TABS[number]["id"];

function scrollToSection(sectionId: string) {
  const el = document.getElementById(sectionId);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function Navbar() {
  const connected = useMarketStore((s) => s.connected);

  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [marketStatus, setMarketStatus] = useState<"OPEN" | "CLOSED" | "UNKNOWN">("UNKNOWN");

  // Fetch market status on component mount
  useEffect(() => {
    const fetchMarketStatus = async () => {
      try {
        console.log("Fetching market status...");
        const response = await fetch("http://localhost:8000/api/v1/market/status");
        const data = await response.json();
        console.log("Market status response:", data);
        
        if (data.status === "OPEN") {
          setMarketStatus("OPEN");
        } else if (data.status === "CLOSED") {
          setMarketStatus("CLOSED");
        } else {
          setMarketStatus("UNKNOWN");
        }
      } catch (error) {
        console.error("Failed to fetch market status:", error);
        setMarketStatus("UNKNOWN");
      }
    };

    fetchMarketStatus();
    
    // Refresh market status every 30 seconds
    const interval = setInterval(fetchMarketStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);

  // Log when component reads store state
  const traceId = traceManager.getTraceId();
  uiLogger.info("UI MARKET STATUS RENDER", { traceId, connected, marketStatus });

  // Market status display logic - using API data
  let marketStatusText = "Checking Market...";
  let marketColor = "bg-gray-500";

  if (marketStatus === "OPEN") {
    marketStatusText = "Market Live";
    marketColor = "bg-green-500";
  } else if (marketStatus === "CLOSED") {
    marketStatusText = "Market Closed";
    marketColor = "bg-red-500";
  }

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: HEARTBEAT_CSS }} />

      <nav className="sticky top-0 z-50 w-full" style={{
        background: 'rgba(18,18,18,0.7)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)'
      }}>
        <div className="max-w-[1920px] mx-auto px-6">
          <div className="h-[60px] flex items-center justify-between">

            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 flex items-center justify-center rounded-xl border border-cyan-400/30 bg-cyan-400/10">
                <svg width="16" height="16" viewBox="0 0 16 16">
                  <path d="M2 12L6 6L9 9L13 3" stroke="#00E5FF" strokeWidth="2" strokeLinecap="round"/>
                  <circle cx="13" cy="3" r="1.5" fill="#00E5FF"/>
                </svg>
              </div>

              <div>
                <div className="text-lg font-bold text-cyan-400">StrikeIQ</div>
                <div className="text-[10px] text-indigo-300/70 uppercase tracking-widest">
                  Options Intelligence
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="hidden md:flex items-center gap-2 bg-white/5 border border-white/10 p-1 rounded-xl">

              {NAV_TABS.map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id);
                      scrollToSection(tab.sectionId);
                    }}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                      active
                        ? "bg-cyan-500/20 border border-cyan-400/30 text-cyan-400"
                        : "text-slate-400"
                    }`}
                  >
                    <Icon size={14} />
                    {tab.label}
                  </button>
                );
              })}

            </div>

            {/* Status */}
            <div className="flex items-center gap-3">

              {/* Market - using API data */}
              <div 
                className="px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1"
                style={{
                  background: marketStatus === "OPEN" 
                    ? 'rgba(34,197,94,0.12)' 
                    : marketStatus === "CLOSED"
                    ? 'rgba(255,70,70,0.12)'
                    : 'rgba(156,163,175,0.12)',
                  color: marketStatus === "OPEN" 
                    ? '#4ade80' 
                    : marketStatus === "CLOSED"
                    ? '#ff6b6b'
                    : '#9ca3af',
                  border: marketStatus === "OPEN" 
                    ? '1px solid rgba(34,197,94,0.35)' 
                    : marketStatus === "CLOSED"
                    ? '1px solid rgba(255,70,70,0.35)'
                    : '1px solid rgba(156,163,175,0.35)',
                  borderRadius: '8px',
                  padding: '4px 10px'
                }}
              >
                {marketStatus === "OPEN" ? (
                  <>
                    <Wifi size={12} /> OPEN
                  </>
                ) : marketStatus === "CLOSED" ? (
                  <>
                    <WifiOff size={12} /> CLOSED
                  </>
                ) : (
                  <>
                    <Wifi size={12} /> {marketStatusText}
                  </>
                )}
              </div>

              {/* WebSocket Heart */}
              <div
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border"
                style={{
                  background: connected 
                    ? "rgba(34,197,94,0.07)" 
                    : "rgba(239,68,68,0.06)",
                  border: connected 
                    ? "1px solid rgba(34,197,94,0.25)" 
                    : "1px solid rgba(239,68,68,0.18)",
                }}
              >
                <Heart
                  style={{
                    width: 13,
                    height: 13,
                    flexShrink: 0,
                    color: connected ? "#4ade80" : "#f87171",
                    fill: connected
                      ? "rgba(34,197,94,0.50)"
                      : "rgba(239,68,68,0.32)",
                    animation: connected ? "ws-heartbeat 0.85s ease-in-out infinite" : "none",
                    transformOrigin: "center",
                  }}
                />

                {/* ECG Graph */}
                <div className="hidden sm:block" style={{ width: 34, height: 15, overflow: "hidden" }}>
                  <svg viewBox="0 0 120 36" width="34" height="15">
                    {connected ? (
                      <path
                        d="M0,18 L28,18 L38,18 L46,4 L53,32 L60,18 L68,18 L75,10 L81,26 L87,18 L120,18"
                        fill="none"
                        stroke="#4ade80"
                        strokeWidth="2.4"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeDasharray="120"
                        style={{
                          animation: "ecg-scan 1.7s ease-in-out infinite",
                          filter: "drop-shadow(0 0 3px rgba(34,197,94,0.9))",
                        }}
                      />
                    ) : (
                      <path
                        d="M0,18 L120,18"
                        fill="none"
                        stroke="#f87171"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        style={{ animation: "flatline-blink 2s ease-in-out infinite" }}
                      />
                    )}
                  </svg>
                </div>

                <span className="hidden sm:inline text-[10px] font-bold text-slate-300">
                  WS
                </span>

              </div>

            </div>

          </div>
        </div>
      </nav>
    </>
  );
}
