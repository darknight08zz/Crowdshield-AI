/**
 * CrowdShield Mobile Design System Tokens
 * Native TypeScript theme file matching web design system specifications.
 */

export const theme = {
  colors: {
    brand: {
      primary: '#0284C7',
      primaryHover: '#0369A1',
      primaryActive: '#075985',
      glow: 'rgba(2, 132, 199, 0.15)',
    },
    neutral: {
      bgPage: '#020617',
      bgSurface: '#0F172A',
      bgElevated: '#1E293B',
      borderSubtle: '#334155',
      borderStrong: '#475569',
      textMuted: '#94A3B8',
      textBody: '#CBD5E1',
      textHeading: '#F8FAFC',
    },
    risk: {
      LOW: {
        hex: '#10B981',
        bg: 'rgba(16, 185, 129, 0.15)',
        border: '#059669',
        label: 'LOW',
        shape: 'circle',
      },
      MODERATE: {
        hex: '#F59E0B',
        bg: 'rgba(245, 158, 11, 0.15)',
        border: '#D97706',
        label: 'MODERATE',
        shape: 'triangle',
      },
      HIGH: {
        hex: '#F97316',
        bg: 'rgba(249, 115, 22, 0.15)',
        border: '#EA580C',
        label: 'HIGH',
        shape: 'diamond',
      },
      CRITICAL: {
        hex: '#EF4444',
        bg: 'rgba(239, 68, 68, 0.20)',
        border: '#DC2626',
        label: 'CRITICAL',
        shape: 'octagon',
      },
    },
    system: {
      success: '#06B6D4',
      warning: '#EAB308',
      error: '#E11D48',
      info: '#3B82F6',
    },
  },
  typography: {
    fontPrimary: 'System',
    fontMono: 'monospace',
    sizes: {
      display: 32,
      pageTitle: 24,
      sectionHeader: 18,
      cardTitle: 15,
      body: 14,
      caption: 12,
      numeric: 22,
    },
  },
  spacing: {
    compact: {
      padding: 12,
      gap: 10,
      radius: 10,
    },
    spacious: {
      padding: 20,
      gap: 16,
      radius: 16,
    },
  },
} as const;

export type MobileRiskBucketKey = keyof typeof theme.colors.risk;
