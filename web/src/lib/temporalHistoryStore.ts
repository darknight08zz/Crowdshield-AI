import { RealtimeInferenceResultData } from './api';

export interface TemporalSample {
  timestamp: string;
  telemetry_timestamp: string;
  prediction_timestamp: string;
  camera_id: string;
  zone_id: string;
  event_id: string;
  person_count: number;
  tracked_person_count: number;
  density: number;
  average_speed: number;
  median_speed: number;
  inflow_rate: number;
  outflow_rate: number;
  flow_imbalance: number;
  net_accumulation: number;
  direction_conflict_score: number;
  reverse_flow_ratio: number;
  blockage_score: number;
  current_physics_risk: number;
  ai_probability: number | null;
  operational_warning_state: 'NORMAL' | 'WATCH' | 'EARLY_WARNING' | 'HIGH_RISK' | 'DEGRADED' | 'WARMING_UP';
  camera_health_status: 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'CV_UNAVAILABLE';
  ai_status: 'SUCCESS' | 'WARMING_UP' | 'AI_UNAVAILABLE' | 'CAMERA_OFFLINE';
  is_stale: boolean;
  is_degraded: boolean;
  lead_time_seconds: number | null;
}

export interface AlertStateTransition {
  id: string;
  timestamp: string;
  event_id: string;
  camera_id: string;
  zone_id: string;
  previous_state: string;
  new_state: string;
  physics_risk: number;
  ai_probability: number | null;
  camera_health: string;
  is_stale: boolean;
  is_degraded: boolean;
  warning_reason?: string;
  is_recovery: boolean;
}

export const MAX_HISTORY_POINTS = 300;

export function buildStreamKey(eventId: string, cameraId: string, zoneId: string): string {
  return `${eventId || 'EVT-DEFAULT'}:${cameraId || 'CAM-DEFAULT'}:${zoneId || 'ZONE-DEFAULT'}`;
}

export class TemporalHistoryStore {
  private historyMap: Map<string, TemporalSample[]> = new Map();
  private transitionsMap: Map<string, AlertStateTransition[]> = new Map();
  private globalTransitions: AlertStateTransition[] = [];
  private listeners: Set<() => void> = new Set();

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    this.listeners.forEach((fn) => fn());
  }

  /**
   * Adds incoming canonical RealtimeInferenceResultData payload to history store.
   * Enforces:
   * 1. Key isolation by (event_id, camera_id, zone_id)
   * 2. Duplicate sample prevention based on telemetry_timestamp & stream key
   * 3. Chronological sorting and out-of-order protection
   * 4. Bounded window size (MAX_HISTORY_POINTS = 300)
   * 5. Deduplicated state transition timeline & recovery tracking
   */
  public addSample(payload: RealtimeInferenceResultData): { sample: TemporalSample; transition: AlertStateTransition | null } | null {
    if (!payload) return null;

    const streamKey = buildStreamKey(payload.event_id, payload.camera_id, payload.zone_id);
    const existingSamples = this.historyMap.get(streamKey) || [];

    const telemetryTs = payload.telemetry_timestamp || payload.prediction_timestamp || new Date().toISOString();
    const sampleTimestamp = payload.prediction_timestamp || telemetryTs;

    const pAny = payload as any;
    const tel = payload.telemetry || {};

    // Duplicate check
    const densityVal = tel.density ?? pAny.density ?? 0;
    const isDuplicate = existingSamples.some(
      (s) => s.telemetry_timestamp === telemetryTs || (s.timestamp === sampleTimestamp && s.density === densityVal)
    );
    if (isDuplicate) {
      return null;
    }

    const physicsRisk = payload.current_physics_risk ?? payload.current_risk_score ?? 0;
    const aiProb = typeof payload.ai_probability === 'number' ? payload.ai_probability : null;
    const horizonSec = payload.provenance?.horizon_seconds ?? 300;

    const sample: TemporalSample = {
      timestamp: sampleTimestamp,
      telemetry_timestamp: telemetryTs,
      prediction_timestamp: payload.prediction_timestamp || telemetryTs,
      camera_id: payload.camera_id,
      zone_id: payload.zone_id,
      event_id: payload.event_id,
      person_count: tel.person_count ?? pAny.person_count ?? 0,
      tracked_person_count: tel.tracked_person_count ?? pAny.tracked_person_count ?? 0,
      density: tel.density ?? pAny.density ?? 0,
      average_speed: tel.average_speed ?? pAny.average_speed ?? 0,
      median_speed: tel.median_speed ?? pAny.median_speed ?? 0,
      inflow_rate: tel.inflow_rate ?? pAny.inflow_rate ?? 0,
      outflow_rate: tel.outflow_rate ?? pAny.outflow_rate ?? 0,
      flow_imbalance: tel.flow_imbalance ?? pAny.flow_imbalance ?? 0,
      net_accumulation: tel.net_accumulation ?? pAny.net_accumulation ?? 0,
      direction_conflict_score: tel.direction_conflict_score ?? pAny.direction_conflict_score ?? 0,
      reverse_flow_ratio: tel.reverse_flow_ratio ?? pAny.reverse_flow_ratio ?? 0,
      blockage_score: tel.blockage_score ?? pAny.blockage_score ?? 0,
      current_physics_risk: physicsRisk,
      ai_probability: aiProb,
      operational_warning_state: payload.operational_warning_state || 'NORMAL',
      camera_health_status: payload.camera_health_status || 'ONLINE',
      ai_status: payload.ai_status || 'SUCCESS',
      is_stale: Boolean(payload.is_stale),
      is_degraded: Boolean(pAny.is_degraded || payload.provenance?.is_degraded),
      lead_time_seconds: horizonSec,
    };

    // Insert sample ensuring chronological timestamp order
    const updatedSamples = [...existingSamples, sample].sort((a, b) => {
      return new Date(a.telemetry_timestamp).getTime() - new Date(b.telemetry_timestamp).getTime();
    });

    // Enforce Bounded History
    if (updatedSamples.length > MAX_HISTORY_POINTS) {
      updatedSamples.splice(0, updatedSamples.length - MAX_HISTORY_POINTS);
    }

    this.historyMap.set(streamKey, updatedSamples);

    // Evaluate Warning State Transitions
    let transition: AlertStateTransition | null = null;
    const streamTransitions = this.transitionsMap.get(streamKey) || [];
    const lastState = streamTransitions.length > 0
      ? streamTransitions[streamTransitions.length - 1].new_state
      : (existingSamples.length > 0 ? existingSamples[existingSamples.length - 1].operational_warning_state : null);

    const currentState = sample.operational_warning_state;

    if (lastState && lastState !== currentState) {
      const severityOrder: Record<string, number> = {
        WARMING_UP: 0,
        DEGRADED: 1,
        NORMAL: 2,
        WATCH: 3,
        EARLY_WARNING: 4,
        HIGH_RISK: 5,
      };

      const isRecovery = (severityOrder[currentState] ?? 2) < (severityOrder[lastState] ?? 2);

      transition = {
        id: `tr-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        timestamp: sample.telemetry_timestamp,
        event_id: sample.event_id,
        camera_id: sample.camera_id,
        zone_id: sample.zone_id,
        previous_state: lastState,
        new_state: currentState,
        physics_risk: physicsRisk,
        ai_probability: aiProb,
        camera_health: sample.camera_health_status,
        is_stale: sample.is_stale,
        is_degraded: sample.is_degraded,
        warning_reason: payload.warning_reason,
        is_recovery: isRecovery,
      };

      const updatedStreamTransitions = [...streamTransitions, transition];
      if (updatedStreamTransitions.length > MAX_HISTORY_POINTS) {
        updatedStreamTransitions.splice(0, updatedStreamTransitions.length - MAX_HISTORY_POINTS);
      }
      this.transitionsMap.set(streamKey, updatedStreamTransitions);

      this.globalTransitions = [transition, ...this.globalTransitions].slice(0, MAX_HISTORY_POINTS);
    }

    this.notify();
    return { sample, transition };
  }

  public getHistory(eventId: string, cameraId: string, zoneId: string): TemporalSample[] {
    const streamKey = buildStreamKey(eventId, cameraId, zoneId);
    return this.historyMap.get(streamKey) || [];
  }

  public getTransitions(eventId: string, cameraId: string, zoneId: string): AlertStateTransition[] {
    const streamKey = buildStreamKey(eventId, cameraId, zoneId);
    return this.transitionsMap.get(streamKey) || [];
  }

  public getGlobalTransitions(): AlertStateTransition[] {
    return [...this.globalTransitions];
  }

  public clear(eventId?: string, cameraId?: string, zoneId?: string) {
    if (eventId && cameraId && zoneId) {
      const key = buildStreamKey(eventId, cameraId, zoneId);
      this.historyMap.delete(key);
      this.transitionsMap.delete(key);
    } else {
      this.historyMap.clear();
      this.transitionsMap.clear();
      this.globalTransitions = [];
    }
    this.notify();
  }
}

export const globalTemporalHistoryStore = new TemporalHistoryStore();
