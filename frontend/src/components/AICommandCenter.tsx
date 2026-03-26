"use client";
import React from 'react';
import { Activity } from 'lucide-react';

export function AICommandCenter() {
    // TEMPORARILY DISABLED to isolate infinite loop
    return (
        <div className="trading-panel h-full flex flex-col justify-center items-center gap-6 opacity-40">
            <Activity className="w-8 h-8 text-slate-700 animate-pulse mb-2" />
            <span className="text-[10px] font-black font-mono tracking-[0.25em] text-slate-600 uppercase text-center max-w-[180px]">
                Component temporarily disabled for debugging
            </span>
        </div>
    );
}
