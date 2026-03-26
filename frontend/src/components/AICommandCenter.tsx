"use client";
import React from 'react';
import { Activity, Brain } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';

export default function AICommandCenter() {
    // Law 7: Granular Store Subscriptions
    const analytics = useWSStore(s => s.analytics);
    const lastUpdate = useWSStore(s => s.lastUpdate);
    const hasData = lastUpdate > 0;

    if (!hasData) {
        return (
            <div className="trading-panel h-full flex flex-col justify-center items-center gap-6 opacity-40">
                <Activity className="w-8 h-8 text-slate-700 animate-pulse mb-2" />
                <span className="text-[10px] font-black font-mono tracking-[0.25em] text-slate-600 uppercase text-center max-w-[180px]">
                    Waiting for AI data...
                </span>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-[#030712]/50 backdrop-blur-xl border border-white/5 rounded-3xl overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                   <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                     <Brain className="w-4 h-4 text-blue-400" />
                   </div>
                   <h3 className="text-[11px] font-black font-mono tracking-widest text-slate-200 uppercase">AI Command Center</h3>
                </div>
            </div>
            <div className="flex-grow p-6 flex flex-col justify-center items-center gap-8">
                <div className="relative group">
                    <div className="absolute -inset-4 bg-blue-500/20 rounded-full blur-2xl group-hover:bg-blue-500/30 transition-all duration-1000 animate-pulse" />
                    <div className="relative w-32 h-32 rounded-full bg-slate-900 border-2 border-slate-800 flex items-center justify-center overflow-hidden">
                        <Activity className="w-12 h-12 text-blue-400 animate-pulse" />
                    </div>
                </div>
                <div className="text-center space-y-2">
                    <div className="text-2xl font-black text-white tracking-tighter">{(analytics?.confidence_score * 100 || 0).toFixed(1)}%</div>
                    <div className="text-[10px] font-black font-mono text-blue-400 tracking-[0.3em] uppercase">CONFLUENCE_SCORE</div>
                </div>
            </div>
        </div>
    );
}

