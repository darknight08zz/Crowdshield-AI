/**
 * PROTOTYPE THRESHOLDS DISCLAIMER:
 * These risk score thresholds (0-24 LOW, 25-49 MODERATE, 50-74 HIGH, 75-100 CRITICAL)
 * are prototype operational boundaries for system demonstration and testing.
 * They are NOT clinically or safety-validated real-world physical crowd safety limits,
 * and MUST be formally reviewed, calibrated, and validated against empirical event
 * incident telemetry or domain-expert/safety authority input before being deployed
 * for real-world event operations.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

export type RiskBucket = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'SAFE';

export const RISK_THRESHOLDS = {
  LOW: { min: 0, max: 24.99 },
  MODERATE: { min: 25, max: 49.99 },
  HIGH: { min: 50, max: 74.99 },
  CRITICAL: { min: 75, max: 100 },
};

export const RISK_COLORS: Record<string, { bg: string; border: string; text: string; badge: string; fill: string }> = {
  LOW: {
    bg: 'bg-emerald-950/40',
    border: 'border-emerald-500/50',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    fill: '#10b981',
  },
  SAFE: {
    bg: 'bg-emerald-950/40',
    border: 'border-emerald-500/50',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    fill: '#10b981',
  },
  MODERATE: {
    bg: 'bg-amber-950/40',
    border: 'border-amber-500/50',
    text: 'text-amber-400',
    badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    fill: '#f59e0b',
  },
  HIGH: {
    bg: 'bg-orange-950/40',
    border: 'border-orange-500/50',
    text: 'text-orange-400',
    badge: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    fill: '#f97316',
  },
  CRITICAL: {
    bg: 'bg-rose-950/50',
    border: 'border-rose-500/80',
    text: 'text-rose-400',
    badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse',
    fill: '#ef4444',
  },
};

export function getRiskCategory(score: number): 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' {
  if (score < 25) return 'LOW';
  if (score < 50) return 'MODERATE';
  if (score < 75) return 'HIGH';
  return 'CRITICAL';
}

export function evaluateMultiHorizonRisk(
  currentRisk: number,
  r2m?: number,
  r5m?: number,
  r10m?: number
) {
  const currBucket = getRiskCategory(currentRisk);
  const forecasts = [
    { label: '2min', score: r2m },
    { label: '5min', score: r5m },
    { label: '10min', score: r10m },
  ];

  let maxScore = currentRisk;
  let maxHorizon = 'current';
  let maxBucket = currBucket;

  for (const f of forecasts) {
    if (f.score !== undefined && f.score !== null) {
      const bucket = getRiskCategory(f.score);
      if (f.score > maxScore) {
        maxScore = f.score;
        maxHorizon = f.label;
        maxBucket = bucket;
      }
    }
  }

  const bucketOrder = ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'];
  const currIdx = bucketOrder.indexOf(currBucket);
  const maxIdx = bucketOrder.indexOf(maxBucket);
  const isEscalating = maxIdx > currIdx;

  let trajectoryWarning = `${currBucket} (STABLE)`;
  let displayStatus: string = currBucket;

  if (isEscalating) {
    trajectoryWarning = `CURRENTLY ${currBucket}, ESCALATING TO ${maxBucket} (+${maxHorizon})`;
    displayStatus = `${currBucket} → ${maxBucket} (+${maxHorizon})`;
  }

  return {
    currentScore: currentRisk,
    currentBucket: currBucket,
    maxForecastScore: maxScore,
    maxForecastHorizon: maxHorizon,
    maxForecastBucket: maxBucket,
    isEscalating,
    trajectoryWarning,
    displayStatus,
    palette: RISK_COLORS[currBucket] || RISK_COLORS.LOW,
  };
}

export const BEHAVIOR_COLORS: Record<string, { badge: string; label: string }> = {
  NORMAL: { badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', label: 'NORMAL FLOW' },
  SURGE: { badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse', label: 'SURGE' },
  REVERSE_FLOW: { badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40', label: 'REVERSE FLOW' },
  STAGNATION: { badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40', label: 'STAGNATION' },
  DISPERSED_INCIDENT_CLUSTER: { badge: 'bg-orange-500/20 text-orange-300 border-orange-500/40', label: 'DISPERSED CLUSTER' },
};
