// ── Shared design tokens for dashboard sub-components ────────────────────────

export const CARD = {
    background: 'rgba(8,11,20,0.60)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '16px',
    backdropFilter: 'blur(20px)',
    boxShadow: '0 4px 24px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.04)',
} as const;

export const CARD_HOVER_BORDER = 'rgba(0,229,255,0.25)';

// Shared section divider
export const DIVIDER = '1px solid rgba(255,255,255,0.06)';

// Micro-badge base style helper
export const badge = (bg: string, border: string, color: string) => ({
    background: bg,
    border: `1px solid ${border}`,
    color,
    padding: '2px 10px',
    borderRadius: '999px',
    fontSize: '10px',
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 700,
    letterSpacing: '0.06em',
} as const);
