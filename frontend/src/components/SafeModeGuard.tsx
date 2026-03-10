import React from 'react';
import { useWSStore } from '@/core/ws/wsStore';

interface SafeModeGuardProps {
    engineMode: string;
    dataSource: string;
    children: React.ReactNode;
    fallback?: React.ReactNode;
}

/**
 * SafeModeGuard - WS-AWARE VERSION
 * Forces LIVE UI when WebSocket spot_price exists
 */
const SafeModeGuard: React.FC<SafeModeGuardProps> = ({
    engineMode,
    dataSource,
    children,
    fallback = null
}) => {

    // 🔥 WS-AWARE LIVE OVERRIDE FIX
    const store = useWSStore.getState();

    const wsSpot =
        store.liveData?.spot_price ??
        store.optionChainSnapshot?.spot_price ??
        0;

    // FORCE LIVE if WS has valid spot
    const effectiveMode =
        engineMode !== "LIVE" && wsSpot > 0
            ? "LIVE"
            : engineMode;

    console.log("🛡️ SafeModeGuard MODE FIX:", {
        engineMode,
        wsSpot,
        effectiveMode
    });

    // SNAPSHOT GUARD
    if (effectiveMode === "SNAPSHOT" && dataSource === "rest_snapshot") {
        console.log("🛡️ Snapshot mode active");
        return <>{children}</>;
    }

    // ENGINE MODE UI VALIDATION GUARD (WITH WS OVERRIDE)
    if (effectiveMode !== "LIVE") {
        console.log(`🛡️ Disabling live UI - Mode: ${effectiveMode}`);

        if (fallback) {
            return <>{fallback}</>;
        }

        return (
            <div className="opacity-50 pointer-events-none">
                {children}
            </div>
        );
    }

    console.log("✅ SafeModeGuard: LIVE MODE UNLOCKED VIA WS");
    return <>{children}</>;
};

/**
 * Hook to check if component should be enabled based on mode
 */
export const useModeGuard = (
    engineMode: string,
    requiredMode: 'LIVE' | 'SNAPSHOT' | 'HALTED' | 'ANY'
) => {
    if (requiredMode === 'ANY') return true;
    return engineMode === requiredMode;
};

/**
 * 🔥 FULL FIXED EFFECTIVE SPOT HOOK
 * Survives WS reconnect flicker
 */
export const useEffectiveSpot = (data: any, engineMode: string) => {

    const store = useWSStore.getState();

    // STEP 2: Enable live mode - prioritize liveData over snapshot
    const spot = store.liveData?.spot_price ?? store.optionChainSnapshot?.spot_price ?? 0;

    const restSpotPrice =
        data?.spot_price ??
        data?.spot ??
        data?.optionChain?.spot_price ??
        data?.optionChain?.spot;

    const effectiveSpot = spot ?? restSpotPrice ?? 0;

    let source = 'DEFAULT';
    if (store.liveData?.spot_price) source = 'WS';
    else if (store.optionChainSnapshot?.spot_price) source = 'SNAPSHOT';
    else if (restSpotPrice) source = 'REST';

    console.log(`🎯 Effective spot: ${effectiveSpot} (Mode: ${engineMode}, Source: ${source})`);
    console.log(`🔍 Snapshot Cache:`, {
        liveData: store.liveData?.spot_price,
        snapshot: store.optionChainSnapshot?.spot_price
    });

    return effectiveSpot;
};

/**
 * Hook to check if analytics should use snapshot mode
 */
export const useSnapshotAnalytics = (engineMode: string, dataSource: string) => {
    const isSnapshotMode = engineMode === "SNAPSHOT" || engineMode === "HALTED";
    const isRestSource = dataSource === "rest_snapshot";

    return {
        shouldUseSnapshot: isSnapshotMode && isRestSource,
        showSnapshotLabel: isSnapshotMode,
        disableLiveCalculations: isSnapshotMode,
        useRestPremiums: isSnapshotMode,
        useRestOI: isSnapshotMode
    };
};

/**
 * Hook to prevent timeout in snapshot mode
 */
export const useTimeoutProtection = (engineMode: string) => {
    const shouldPreventTimeouts = engineMode !== "LIVE";

    return {
        shouldPreventRetries: shouldPreventTimeouts,
        shouldPreventWSWait: shouldPreventTimeouts,
        shouldPreventPremiumWait: shouldPreventTimeouts,
        abortWSDependentCalls: shouldPreventTimeouts
    };
};

export default SafeModeGuard;