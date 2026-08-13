/**
 * PROTOTYPE THRESHOLDS DISCLAIMER:
 * These risk score thresholds (0-24 LOW, 25-49 MODERATE, 50-74 HIGH, 75-100 CRITICAL)
 * are prototype operational boundaries for system demonstration and testing.
 * They are NOT clinically or safety-validated real-world physical crowd safety limits,
 * and MUST be formally reviewed, calibrated, and validated against empirical event
 * incident telemetry or domain-expert/safety authority input before being deployed
 * for real-world event operations.
 */

import Constants from 'expo-constants';
import { Platform } from 'react-native';

const getBackendHost = () => {
  // Inspect Expo Go host URI to dynamically extract developer machine IPv4 address
  const hostUri = Constants.expoConfig?.hostUri || (Constants as any).manifest2?.extra?.expoGo?.developer?.manifest?.debuggerHost || '';
  
  // Extract IPv4 pattern (works for both direct IP like 10.120.171.227:8081 and tunnel hostnames like u879-10-120-171-227.exp.direct)
  const ipMatch = hostUri.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
  if (ipMatch && ipMatch[1] && ipMatch[1] !== '127.0.0.1') {
    const url = `http://${ipMatch[1]}:8000/api/v1`;
    console.log(`[CrowdShield Mobile API] Auto-detected developer PC IP (${ipMatch[1]}): ${url}`);
    return url;
  }

  // Default LAN IP fallback (Developer Machine IP)
  const fallback = 'http://10.120.171.227:8000/api/v1';
  console.log(`[CrowdShield Mobile API] Using LAN fallback backend URL: ${fallback}`);
  return fallback;
};

export const API_BASE_URL = getBackendHost();

export const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || '';
export const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || '';

export const RISK_COLOR_MAP = {
  LOW: '#10b981',       // Emerald Green (Risk 0 - 24)
  SAFE: '#10b981',      // Emerald Green Alias
  MODERATE: '#f59e0b',  // Amber Yellow (Risk 25 - 49)
  HIGH: '#f97316',      // Orange (Risk 50 - 74)
  CRITICAL: '#ef4444',  // Red (Risk 75 - 100)
};

export const getRiskCategory = (score: number) => {
  if (score < 25) return { label: 'LOW', key: 'LOW', color: RISK_COLOR_MAP.LOW, bg: '#064e3b' };
  if (score < 50) return { label: 'MODERATE', key: 'MODERATE', color: RISK_COLOR_MAP.MODERATE, bg: '#78350f' };
  if (score < 75) return { label: 'HIGH', key: 'HIGH', color: RISK_COLOR_MAP.HIGH, bg: '#7c2d12' };
  return { label: 'CRITICAL', key: 'CRITICAL', color: RISK_COLOR_MAP.CRITICAL, bg: '#7f1d1d' };
};

export const evaluateMultiHorizonRisk = (
  currentRisk: number,
  r2m?: number,
  r5m?: number,
  r10m?: number
) => {
  const currCat = getRiskCategory(currentRisk);
  const forecasts = [
    { label: '2m', score: r2m },
    { label: '5m', score: r5m },
    { label: '10m', score: r10m },
  ];

  let maxScore = currentRisk;
  let maxHorizon = 'current';
  let maxCat = currCat;

  for (const f of forecasts) {
    if (f.score !== undefined && f.score !== null) {
      const cat = getRiskCategory(f.score);
      if (f.score > maxScore) {
        maxScore = f.score;
        maxHorizon = f.label;
        maxCat = cat;
      }
    }
  }

  const order = ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'];
  const currIdx = order.indexOf(currCat.key);
  const maxIdx = order.indexOf(maxCat.key);
  const isEscalating = maxIdx > currIdx;

  let displayLabel = `${currCat.label} (${currentRisk.toFixed(0)}%)`;
  if (isEscalating) {
    displayLabel = `${currCat.label} → ${maxCat.label} (+${maxHorizon})`;
  }

  return {
    currentScore: currentRisk,
    currentCategory: currCat,
    maxForecastCategory: maxCat,
    maxHorizon,
    isEscalating,
    displayLabel,
  };
};
