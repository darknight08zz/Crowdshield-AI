export type OfficerStatus = 'AVAILABLE' | 'ASSIGNED' | 'BUSY' | 'OFFLINE';
export type LocationStatus = 'LOCATION_CURRENT' | 'LOCATION_STALE' | 'LOCATION_UNKNOWN';

export type DispatchStatus =
  | 'UNASSIGNED'
  | 'ASSIGNED'
  | 'ACKNOWLEDGED'
  | 'EN_ROUTE'
  | 'ON_SCENE'
  | 'RESPONDING'
  | 'COMPLETED'
  | 'CANCELLED';

export interface ResponseOfficer {
  officer_id: string;
  user_id?: string;
  name: string;
  role: string;
  status: OfficerStatus;
  current_latitude?: number;
  current_longitude?: number;
  location_status: LocationStatus;
  location_timestamp?: string;
  assigned_event_id: string;
  created_at: string;
  updated_at: string;
}

export interface DispatchTransition {
  transition_id: string;
  dispatch_id: string;
  previous_status: DispatchStatus;
  new_status: DispatchStatus;
  timestamp: string;
  actor_type: 'SYSTEM' | 'OPERATOR' | 'FIELD_OFFICER';
  actor_id?: string;
  reason?: string;
  metadata_json?: Record<string, any>;
}

export interface DispatchAssignment {
  dispatch_id: string;
  incident_id: string;
  event_id: string;
  officer_id: string;
  status: DispatchStatus;
  assigned_by: string;
  assigned_at: string;
  acknowledged_at?: string;
  en_route_at?: string;
  on_scene_at?: string;
  responding_at?: string;
  completed_at?: string;
  cancelled_at?: string;
  eta_minutes?: number;
  dispatch_reason?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  officer?: ResponseOfficer;
  transitions?: DispatchTransition[];
}

export interface FieldOfficerAssignmentContext {
  dispatch: DispatchAssignment;
  incident_id: string;
  zone_id: string;
  event_id: string;
  camera_id?: string;
  warning_state: string;
  physics_risk?: number;
  ai_probability?: number;
  model_version: string;
  label_type: string;
  model_status: string;
  disclaimer: string;
}

export const VALID_DISPATCH_TRANSITIONS: Record<DispatchStatus, DispatchStatus[]> = {
  UNASSIGNED: ['ASSIGNED'],
  ASSIGNED: ['ACKNOWLEDGED', 'CANCELLED'],
  ACKNOWLEDGED: ['EN_ROUTE', 'CANCELLED'],
  EN_ROUTE: ['ON_SCENE', 'CANCELLED'],
  ON_SCENE: ['RESPONDING', 'CANCELLED'],
  RESPONDING: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
};
