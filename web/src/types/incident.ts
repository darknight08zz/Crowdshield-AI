export interface IncidentTransitionData {
  transition_id: string;
  incident_id: string;
  previous_status: string;
  new_status: string;
  timestamp: string;
  actor_type: 'SYSTEM' | 'OPERATOR';
  actor_id?: string | null;
  reason?: string | null;
  metadata_json?: Record<string, any> | null;
}

export interface CreationSnapshotData {
  source_type: string;
  warning_state_at_creation: string;
  physics_risk_at_creation?: number | null;
  ai_probability_at_creation?: number | null;
  telemetry_timestamp?: string | null;
  prediction_timestamp?: string | null;
}

export interface LatestSnapshotData {
  latest_warning_state?: string | null;
  latest_physics_risk?: number | null;
  latest_ai_probability?: number | null;
  latest_telemetry_timestamp?: string | null;
}

export interface IncidentProvenanceData {
  model_version: string;
  prediction_target: string;
  label_type: string;
  model_status: string;
  ground_truth_status: string;
  generalization_status: string;
  disclaimer: string;
}

export type CanonicalIncidentStatus = 
  | 'OPEN' 
  | 'ACKNOWLEDGED' 
  | 'INVESTIGATING' 
  | 'MITIGATING' 
  | 'RESOLVED' 
  | 'FALSE_POSITIVE';

export interface IncidentCanonicalData {
  incident_id: string;
  event_id: string;
  camera_id?: string | null;
  zone_id: string;
  status: CanonicalIncidentStatus;
  source_type: string;
  
  creation_snapshot: CreationSnapshotData;
  latest_snapshot: LatestSnapshotData;
  
  camera_health_status?: string | null;
  is_stale: boolean;
  is_degraded: boolean;
  
  provenance: IncidentProvenanceData;
  
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  resolution_type?: string | null;
  resolution_notes?: string | null;
  
  transitions: IncidentTransitionData[];
  created_at: string;
  updated_at: string;
}

export interface IncidentTransitionRequestData {
  new_status: CanonicalIncidentStatus;
  reason?: string;
}

/**
 * Deterministic Lifecycle State Machine Mapping for Valid Transitions (Part 7)
 */
export const VALID_TRANSITIONS: Record<CanonicalIncidentStatus, CanonicalIncidentStatus[]> = {
  OPEN: ['ACKNOWLEDGED', 'FALSE_POSITIVE'],
  ACKNOWLEDGED: ['INVESTIGATING', 'FALSE_POSITIVE', 'RESOLVED'],
  INVESTIGATING: ['MITIGATING', 'RESOLVED'],
  MITIGATING: ['RESOLVED'],
  RESOLVED: [],
  FALSE_POSITIVE: [],
};
