"use client";
import React from 'react';
import { WifiOff, Database } from 'lucide-react';
import { CARD } from './DashboardTypes';

export function LoadingBlock() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] relative overflow-hidden">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none" />

            <div className="relative mb-10 group">
                <div className="absolute inset-0 rounded-full bg-cyan-500/30 blur-2xl animate-pulse" />
                <div
                    className="w-24 h-24 rounded-full border-[2px] animate-[spin_3s_linear_infinite] relative z-10"
                    style={{ borderColor: 'rgba(0,229,255,0.1)', borderTopColor: '#00E5FF' }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                    <div
                        className="w-16 h-16 rounded-full border-[2px] animate-[spin_2s_linear_infinite] relative z-20"
                        style={{ borderColor: 'rgba(124,58,237,0.1)', borderTopColor: '#7C3AED', animationDirection: 'reverse' }}
                    />
                </div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-2 h-2 bg-white rounded-full animate-ping shadow-[0_0_20px_white]" />
                </div>
            </div>

            <div className="flex flex-col items-center gap-2 relative z-10">
                <span className="text-xs font-black font-mono tracking-[0.4em] text-cyan-500 uppercase">
                    Initializing Strike Engine
                </span>
                <div className="flex items-center gap-1.5 h-1 w-32 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 animate-[prog_2s_ease-in-out_infinite]" style={{ width: '40%' }} />
                </div>
                <span className="text-[10px] font-bold font-mono text-slate-600 uppercase tracking-widest mt-2">
                    Establishing Secure WebSocket Node...
                </span>
            </div>

            <style jsx>{`
                @keyframes prog {
                    0% { transform: translateX(-100%); width: 30%; }
                    50% { width: 60%; }
                    100% { transform: translateX(300%); width: 30%; }
                }
            `}</style>
        </div>
    );
}

export function SnapshotReadyBlock() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[40vh] mx-4 my-10 p-12 trading-panel relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Database className="w-32 h-32 text-blue-400 rotate-12" />
            </div>

            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 bg-blue-500/10 border border-blue-500/20 shadow-[0_0_20px_rgba(59,130,246,0.1)]">
                <Database className="w-8 h-8 text-blue-400" />
            </div>

            <h3 className="text-xl font-black text-white tracking-tight mb-2 uppercase italic">Engine on Standby</h3>
            <p className="text-sm text-center max-w-sm text-slate-500 leading-relaxed font-medium mb-6">
                Direct WebSocket feed inactive. Utilizing high-fidelity REST snapshots for current analytical state.
            </p>

            <div className="px-5 py-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-[10px] font-black font-mono text-blue-400 tracking-[0.2em] uppercase">
                Snapshot Mode Active
            </div>
        </div>
    );
}

export function ErrorBlock({ message }: { message: string }) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[40vh] mx-4 my-10 p-12 trading-panel relative overflow-hidden group">
            <div className="absolute -bottom-10 -left-10 p-4 opacity-5">
                <WifiOff className="w-48 h-48 text-red-500 -rotate-12" />
            </div>

            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 bg-red-500/10 border border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.1)]">
                <WifiOff className="w-8 h-8 text-red-400" />
            </div>

            <h3 className="text-xl font-black text-white tracking-tight mb-2 uppercase italic">Circuit Interrupted</h3>
            <p className="text-sm text-center max-w-sm text-slate-500 leading-relaxed font-medium mb-6">
                {message || "Telemetry stream lost. Retrying connection to primary data nodes..."}
            </p>

            <div className="px-5 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-[10px] font-black font-mono text-red-400 tracking-[0.2em] uppercase">
                System Offline
            </div>
        </div>
    );
}

