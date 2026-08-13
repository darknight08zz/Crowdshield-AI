/**
 * CrowdShield Web Design System Tokens
 * Single source of truth for color palettes, typography, spacing, and risk bucket styling.
 */

export const theme = {
  fonts: {
    primary: 'Plus Jakarta Sans, system-ui, sans-serif',
    mono: 'JetBrains Mono, monospace',
  },
  colors: {
    brand: {
      primary: '#0284c7',
      hover: '#0369a1',
      active: '#075985',
      glow: 'rgba(2, 132, 199, 0.15)',
    },
    neutral: {
      bgPage: '#020617',
      bgSurface: '#0f172a',
      bgElevated: '#1e293b',
      borderSubtle: '#334155',
      borderStrong: '#475569',
      textMuted: '#94a3b8',
      textBody: '#cbd5e1',
      textHeading: '#f8fafc',
    },
    risk: {
      LOW: {
        hex: '#10b981',
        bg: 'rgba(16, 185, 129, 0.12)',
        border: '#059669',
        label: 'LOW',
        shape: 'circle',
      },
      MODERATE: {
        hex: '#f59e0b',
        bg: 'rgba(245, 158, 11, 0.12)',
        border: '#d97706',
        label: 'MODERATE',
        shape: 'triangle',
      },
      HIGH: {
        hex: '#f97316',
        bg: 'rgba(249, 115, 22, 0.15)',
        border: '#ea580c',
        label: 'HIGH',
        shape: 'diamond',
      },
      CRITICAL: {
        hex: '#ef4444',
        bg: 'rgba(239, 68, 68, 0.20)',
        border: '#dc2626',
        label: 'CRITICAL',
        shape: 'octagon',
      },
    },
    system: {
      success: '#06b6d4',
      warning: '#eab308',
      error: '#e11d48',
      info: '#3b82f6',
    },
  },
  density: {
    controlRoom: {
      padding: 'p-3.5',
      gap: 'gap-3.5',
      cardRadius: 'rounded-xl',
    },
    citizen: {
      padding: 'p-6',
      gap: 'gap-6',
      cardRadius: 'rounded-2xl',
    },
  },
  motion: {
    transitionFast: 'transition-all duration-150 ease-in-out',
    transitionNormal: 'transition-colors duration-200 ease-in-out',
  },
} as const;

export type RiskBucketKey = keyof typeof theme.colors.risk;
