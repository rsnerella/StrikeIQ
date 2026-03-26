"use client";

import React, { memo, useRef, useCallback } from 'react';
import { Target, Shield, DollarSign, Activity, Percent } from 'lucide-react';
import { useWSStore } from '@/core/ws/wsStore';
import { SectionLabel } from '../dashboard/StatCards';
import { CARD_HOVER_BORDER } from '../dashboard/DashboardTypes';

// Skeleton Pulse for professional loading states
const SkeletonPulse = ({ className }: { className: string }) => (
    <div className={`animate-pulse bg-white/5 rounded-md ${className}`} />
);

const StrategyPlanPanel: React.FC = () => {
    // TEMPORARILY DISABLED to isolate infinite loop
    return (
        <div className="trading-panel h-full flex flex-col justify-center items-center gap-6 opacity-40">
            <Activity className="w-8 h-8 text-slate-700 animate-pulse mb-2" />
            <span className="text-[10px] font-black font-mono tracking-[0.25em] text-slate-600 uppercase text-center max-w-[180px]">
                Component temporarily disabled for debugging
            </span>
        </div>
    );
};

export default memo(StrategyPlanPanel);
