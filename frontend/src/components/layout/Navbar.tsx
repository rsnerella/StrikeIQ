"use client";

import React, { useState, useEffect } from "react";
import { Wifi, WifiOff, Heart, BarChart2, Link2, Activity, Bell, Home, TrendingUp, Brain, Settings } from "lucide-react";
import { useMarketStore } from "@/stores/marketStore";
import { useWSStore } from "@/core/ws/wsStore";
import api from "@/api/client";

const HEARTBEAT_CSS = `
@keyframes ws-heartbeat {
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

const BOTTOM_NAV_TABS = [
  { id: "dashboard", sectionId: "section-dashboard", label: "Dashboard", icon: Home },
  { id: "chain", sectionId: "oi-heatmap", label: "Option Chain", icon: Link2 },
  { id: "smart-money", sectionId: "section-analytics", label: "Smart Money", icon: TrendingUp },
  { id: "ai-signals", sectionId: "section-alerts", label: "AI Signals", icon: Brain },
  { id: "settings", sectionId: "section-settings", label: "Settings", icon: Settings },
] as const;

type TabId = typeof BOTTOM_NAV_TABS[number]["id"];

function scrollToSection(sectionId: string) {
  const el = document.getElementById(sectionId);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function Navbar() {

  const connected = useMarketStore((s) => s.connected);

  const [activeTab, setActiveTab] = useState<TabId>("dashboard");

  const marketStatus = useWSStore((s) => s.marketStatus);
  const setMarketStatus = useWSStore((s) => s.setMarketStatus);

  useEffect(() => {
    const fetchMarketStatus = async () => {
      try {
        const response = await api.get('/v1/market/status');
        const data = response.data;

        if (data && (data.market_status || data.status)) {
          setMarketStatus(data.market_status || data.status || "UNKNOWN");
        }
      } catch (err) {
        console.warn("Failed to fetch market status", err);
      }
    };

    fetchMarketStatus();
    const interval = setInterval(fetchMarketStatus, 30000);

    return () => clearInterval(interval);
  }, [setMarketStatus]);

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: HEARTBEAT_CSS }} />

      <nav
        className="sticky top-0 z-50 w-full"
        style={{
          background: "rgba(4,6,14,0.85)",
          backdropFilter: "blur(24px) saturate(180%)",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          boxShadow: "0 1px 0 rgba(0,229,255,0.06), 0 4px 24px rgba(0,0,0,0.50)",
        }}
      >
        {/* Top accent line */}
        <div
          style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: '1px',
            background: 'linear-gradient(90deg, transparent, rgba(0,229,255,0.50), rgba(99,102,241,0.30), transparent)',
          }}
        />

        <div className="w-full max-w-[1920px] mx-auto px-3 md:px-6">

          <div className="h-[58px] md:h-[64px] flex items-center justify-between gap-4">

            {/* LOGO */}

            <div className="flex items-center gap-3 shrink-0">

              <div
                className="w-9 h-9 flex items-center justify-center rounded-xl"
                style={{
                  background: 'rgba(0,229,255,0.10)',
                  border: '1px solid rgba(0,229,255,0.28)',
                  boxShadow: '0 0 16px rgba(0,229,255,0.18)',
                }}
              >

                <svg width="16" height="16" viewBox="0 0 16 16">
                  <path d="M2 12L6 6L9 9L13 3" stroke="#00E5FF" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="13" cy="3" r="1.5" fill="#00E5FF" />
                </svg>

              </div>

              <div>
                <div
                  className="text-[17px] font-extrabold tracking-tight"
                  style={{
                    background: 'linear-gradient(90deg, #00E5FF, #818cf8)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  StrikeAi
                </div>
                <div className="text-[9px] text-indigo-300/60 uppercase tracking-[0.22em] font-semibold">
                  Ai Driven Options Intelligence
                </div>
              </div>

            </div>


            {/* DESKTOP TABS */}

            <div
              className="hidden md:flex items-center gap-1 p-1 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
            >

              {BOTTOM_NAV_TABS.filter(tab => ['dashboard', 'chain', 'smart-money', 'ai-signals'].includes(tab.id)).map((tab) => {

                const Icon = tab.icon;
                const active = activeTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id);
                      scrollToSection(tab.sectionId);
                    }}
                    className={`relative flex items-center gap-2 px-4 py-2 rounded-lg text-[11px] font-bold tracking-wide transition-all duration-200 ${active
                      ? "text-cyan-400"
                      : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                      }`}
                    style={active ? {
                      background: 'rgba(0,229,255,0.10)',
                      border: '1px solid rgba(0,229,255,0.22)',
                      boxShadow: '0 0 12px rgba(0,229,255,0.12)',
                    } : undefined}
                  >
                    <Icon size={13} />
                    <span className="uppercase tracking-widest">{tab.label}</span>
                  </button>
                );

              })}

            </div>

            {/* STATUS AREA */}

            <div className="flex items-center gap-2 shrink-0">

              {/* MARKET STATUS */}

              <div
                className="px-3 py-1.5 rounded-full text-[10px] font-bold font-mono flex items-center gap-1.5 tracking-widest transition-all duration-500"
                style={{
                  minWidth: 100,
                  background:
                    marketStatus === "OPEN"
                      ? "rgba(34,197,94,0.10)"
                      : marketStatus === "PREOPEN"
                        ? "rgba(251,191,36,0.10)"
                        : marketStatus === "CLOSED"
                          ? "rgba(255,70,70,0.08)"
                          : "rgba(99,102,241,0.10)",
                  color:
                    marketStatus === "OPEN"
                      ? "#4ade80"
                      : marketStatus === "PREOPEN"
                        ? "#facc15"
                        : marketStatus === "CLOSED"
                          ? "#ff6b6b"
                          : "#a5b4fc",
                  border:
                    marketStatus === "OPEN"
                      ? "1px solid rgba(34,197,94,0.30)"
                      : marketStatus === "PREOPEN"
                        ? "1px solid rgba(251,191,36,0.30)"
                        : marketStatus === "CLOSED"
                          ? "1px solid rgba(255,70,70,0.22)"
                          : "1px solid rgba(99,102,241,0.28)",
                }}
              >

                {marketStatus === "OPEN" ? (
                  <>
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-70" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-400" />
                    </span>
                    LIVE
                  </>
                ) : marketStatus === "PREOPEN" ? (
                  <>
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-60" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-yellow-400" />
                    </span>
                    PREOPEN
                  </>
                ) : marketStatus === "CLOSED" ? (
                  <>
                    <WifiOff size={10} />
                    CLOSED
                  </>
                ) : (
                  // UNKNOWN / CHECKING — show an indigo pulsing dot
                  <>
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-50" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-400" />
                    </span>
                    CHECKING
                  </>
                )}

              </div>

              {/* WS HEART — UNCHANGED */}

              <div
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl"
                style={{
                  minWidth: 58,
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
                    animation: connected
                      ? "ws-heartbeat 0.85s ease-in-out infinite"
                      : "none",
                    transformOrigin: "center",
                  }}
                />

                <div
                  className="hidden sm:block"
                  style={{ width: 34, height: 15, overflow: "hidden" }}
                >

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
                          filter:
                            "drop-shadow(0 0 3px rgba(34,197,94,0.9))",
                        }}
                      />
                    ) : (
                      <path
                        d="M0,18 L120,18"
                        fill="none"
                        stroke="#f87171"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        style={{
                          animation:
                            "flatline-blink 2s ease-in-out infinite",
                        }}
                      />
                    )}

                  </svg>

                </div>

                <span className="hidden sm:inline text-[10px] font-bold font-mono"
                  style={{ color: connected ? '#4ade80' : '#f87171' }}
                >
                  WS
                </span>

              </div>

            </div>

          </div>

        </div>


      </nav>

      {/* BOTTOM NAVIGATION FOR MOBILE */}
      <nav className="fixed bottom-0 left-0 right-0 h-16 bg-black border-t border-gray-800 flex justify-around items-center md:hidden z-50"
        style={{
          background: 'rgba(4,6,14,0.95)',
          backdropFilter: 'blur(24px) saturate(180%)',
          borderTop: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        {BOTTOM_NAV_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                scrollToSection(tab.sectionId);
              }}
              className={`flex flex-col items-center justify-center gap-1 p-2 rounded-lg transition-all duration-200 ${active
                ? "text-cyan-400"
                : "text-slate-400 hover:text-slate-200"
                }`}
              style={active ? {
                background: 'rgba(0,229,255,0.10)',
                border: '1px solid rgba(0,229,255,0.22)',
              } : undefined}
            >
              <Icon size={18} />
              <span className="text-[9px] font-medium uppercase tracking-wider">{tab.label.split(' ')[0]}</span>
            </button>
          );
        })}
      </nav>
    </>
  );
}