"use client";
import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export interface PremiumDropdownProps {
    value: string;
    onChange: (v: string) => void;
    options: string[];
    placeholder?: string;
    minWidth?: number;
    loading?: boolean;
    disabled?: boolean;
    /** Optional prefix icon rendered inside the trigger button */
    icon?: React.ReactNode;
    /** Format each option label (default: identity) */
    formatLabel?: (v: string) => string;
}

const DD_ANIMATION = `
@keyframes premiumDdFade {
  from { opacity: 0; transform: translateY(-5px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
`;

/**
 * PremiumDropdown — shared glassmorphism custom select used across StrikeIQ dashboard.
 * Replaces all native <select> elements.
 */
export function PremiumDropdown({
    value,
    onChange,
    options,
    placeholder = '—',
    minWidth = 148,
    loading = false,
    disabled = false,
    icon,
    formatLabel,
}: PremiumDropdownProps) {
    const [open, setOpen] = useState(false);
    const wrapRef = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        function handler(e: MouseEvent) {
            if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        if (open) document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    const [focusedIndex, setFocusedIndex] = useState(-1);

    // Reset focus and add keyboard nav
    useEffect(() => {
        if (!open) return;

        // Init focus on current value
        const idx = options.indexOf(value);
        setFocusedIndex(idx >= 0 ? idx : 0);

        function handleKeyDown(e: KeyboardEvent) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setFocusedIndex(prev => (prev < options.length - 1 ? prev + 1 : prev));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setFocusedIndex(prev => (prev > 0 ? prev - 1 : prev));
            } else if (e.key === 'Enter') {
                e.preventDefault();
                setFocusedIndex(prev => {
                    if (prev >= 0 && prev < options.length) {
                        onChange(options[prev]);
                        setOpen(false);
                    }
                    return prev;
                });
            } else if (e.key === 'Escape') {
                e.preventDefault();
                setOpen(false);
            }
        }
        
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [open, options, value, onChange]);

    const isDisabled = disabled || loading;
    const label = loading ? 'Loading…' : (value || placeholder);
    const fmt = formatLabel ?? ((v: string) => v);

    return (
        <div
            ref={wrapRef}
            style={{ position: 'relative', minWidth, userSelect: 'none' }}
        >
            <style>{DD_ANIMATION}</style>

            {/* ── Trigger button ─────────────────────────────────────── */}
            <button
                onClick={() => !isDisabled && setOpen(o => !o)}
                disabled={isDisabled}
                aria-haspopup="listbox"
                aria-expanded={open}
                style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    padding: '7px 10px 7px 12px',
                    borderRadius: 10,
                    background: open
                        ? 'rgba(0,229,255,0.09)'
                        : 'rgba(255,255,255,0.045)',
                    border: open
                        ? '1px solid rgba(0,229,255,0.35)'
                        : '1px solid rgba(255,255,255,0.10)',
                    boxShadow: open
                        ? '0 0 0 3px rgba(0,229,255,0.09), inset 0 1px 0 rgba(255,255,255,0.05)'
                        : 'inset 0 1px 0 rgba(255,255,255,0.03)',
                    cursor: isDisabled ? 'not-allowed' : 'pointer',
                    transition: 'all 0.18s ease',
                    outline: 'none',
                    opacity: isDisabled ? 0.5 : 1,
                }}
            >
                {/* Left: icon + label */}
                <span style={{ display: 'flex', alignItems: 'center', gap: 7, overflow: 'hidden' }}>
                    {icon && (
                        <span style={{ color: 'rgba(148,163,184,0.55)', flexShrink: 0, display: 'flex' }}>
                            {icon}
                        </span>
                    )}
                    <span style={{
                        fontSize: 11,
                        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                        fontWeight: 700,
                        letterSpacing: '0.06em',
                        color: value ? '#e2e8f0' : 'rgba(148,163,184,0.45)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}>
                        {label}
                    </span>
                </span>

                {/* Right: chevron */}
                <ChevronDown
                    size={12}
                    style={{
                        flexShrink: 0,
                        color: 'rgba(148,163,184,0.50)',
                        transition: 'transform 0.18s ease',
                        transform: open ? 'rotate(180deg)' : 'none',
                    }}
                />
            </button>

            {/* ── Dropdown panel ─────────────────────────────────────── */}
            {open && options.length > 0 && (
                <div
                    role="listbox"
                    style={{
                        position: 'absolute',
                        top: 'calc(100% + 6px)',
                        left: 0,
                        minWidth: '100%',
                        zIndex: 9999,
                        background: 'rgba(7,11,22,0.97)',
                        border: '1px solid rgba(0,229,255,0.18)',
                        borderRadius: 12,
                        boxShadow:
                            '0 20px 60px rgba(0,0,0,0.75), 0 0 0 1px rgba(0,229,255,0.07), inset 0 1px 0 rgba(255,255,255,0.04)',
                        backdropFilter: 'blur(28px)',
                        overflow: 'hidden',
                        animation: 'premiumDdFade 0.15s ease forwards',
                    }}
                >
                    {/* Top accent glow line */}
                    <div style={{
                        position: 'absolute', top: 0, left: 0, right: 0, height: 1,
                        background: 'linear-gradient(90deg, transparent 5%, rgba(0,229,255,0.45) 50%, transparent 95%)',
                    }} />

                    {/* Options list */}
                    <div 
                        onWheel={(e) => e.stopPropagation()}
                        style={{ padding: '4px 4px 4px', maxHeight: 260, overflowY: 'auto' }}
                    >
                        {options.map((opt, i) => {
                            const selected = opt === value;
                            const isFocused = i === focusedIndex;
                            return (
                                <button
                                    key={opt}
                                    role="option"
                                    aria-selected={selected}
                                    onClick={() => { onChange(opt); setOpen(false); }}
                                    style={{
                                        width: '100%',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        gap: 8,
                                        padding: '8px 10px',
                                        borderRadius: 8,
                                        background: selected
                                            ? 'rgba(0,229,255,0.10)'
                                            : isFocused ? 'rgba(255,255,255,0.05)' : 'transparent',
                                        border: selected
                                            ? '1px solid rgba(0,229,255,0.22)'
                                            : isFocused ? '1px solid rgba(255,255,255,0.07)' : '1px solid transparent',
                                        cursor: 'pointer',
                                        transition: 'all 0.12s ease',
                                        marginBottom: 2,
                                        outline: 'none',
                                        textAlign: 'left',
                                    }}
                                    onMouseEnter={() => setFocusedIndex(i)}
                                    onMouseLeave={() => setFocusedIndex(-1)}
                                >
                                    <span style={{
                                        fontSize: 11,
                                        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                                        fontWeight: 700,
                                        letterSpacing: '0.05em',
                                        color: selected ? '#00E5FF' : '#94a3b8',
                                        transition: 'color 0.12s ease',
                                    }}>
                                        {fmt(opt)}
                                    </span>
                                    {selected && (
                                        <Check
                                            size={11}
                                            style={{ color: '#00E5FF', flexShrink: 0 }}
                                        />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Empty state */}
            {open && options.length === 0 && !loading && (
                <div style={{
                    position: 'absolute',
                    top: 'calc(100% + 6px)',
                    left: 0,
                    right: 0,
                    zIndex: 9999,
                    background: 'rgba(7,11,22,0.97)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 12,
                    padding: '12px 14px',
                }}>
                    <span style={{
                        fontSize: 11,
                        fontFamily: "'JetBrains Mono', monospace",
                        color: 'rgba(148,163,184,0.40)',
                    }}>
                        No options available
                    </span>
                </div>
            )}
        </div>
    );
}
