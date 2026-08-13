import { API_BASE_URL } from './constants';

export interface ZoneData {
  id: string;
  name: string;
  capacity: number;
  current_density: number;
  risk_score: number;
  predicted_risk_2min?: number;
  predicted_risk_5min?: number;
  predicted_risk_10min?: number;
  trajectory_trend?: 'RAPID_ESCALATION' | 'ELEVATED_STABILIZING' | 'MODERATE_BUILDUP' | 'STABLE';
  status: 'SAFE' | 'MODERATE' | 'HIGH' | 'CRITICAL SURGE';
  inflow_rate?: number;
  outflow_rate?: number;
  avg_speed?: number;
  direction_conflict?: number;
  coordinates?: [number, number][];
}

export interface GateData {
  id: string;
  name: string;
  status: 'open' | 'restricted' | 'closed';
  type: 'entry' | 'exit' | 'emergency';
  zone_id: string;
  capacity_per_min?: number;
}

export interface BarricadeData {
  id: string;
  event_id: string;
  zone_id?: string;
  name: string;
  current_configuration: 'open' | 'narrow' | 'closed' | 'redirect_left' | 'redirect_right';
  moveable: boolean;
  position_geometry?: any;
}

export interface DensityGridData {
  zone_id: string;
  zone_name: string;
  calibration_method: 'homography' | 'area_only';
  is_calibrated: boolean;
  fallback_to_flat_fill: boolean;
  grid_dims: [number, number];
  cell_width_meters?: number;
  cell_height_meters?: number;
  average_density_peds_m2: number;
  max_localized_density_peds_m2: number;
  grid_densities_peds_m2: number[][] | null;
  grid_risk_scores: number[][] | null;
  warning_banner?: string;
}


export interface IncidentData {
  id: string;
  type: string;
  description: string;
  location_name: string;
  zone_id: string;
  status: 'pending' | 'verified' | 'resolving' | 'resolved' | 'false_alarm';
  reported_by: string;
  user_role: 'citizen' | 'field_officer';
  image_url?: string;
  created_at: string;
  lat: number;
  lng: number;
}

export interface OfficerData {
  id: string;
  name: string;
  badge_number: string;
  assigned_zone_name: string;
  assigned_zone_id: string;
  status: 'assigned' | 'in_progress' | 'completed' | 'on_break';
  current_task: string;
  battery_level: number;
  last_ping: string;
  email?: string;
  phone?: string;
  is_active?: boolean;
}

export interface RecommendationData {
  id: string;
  zone_id: string;
  zone_name: string;
  trigger_reason: string;
  proposed_action: string;
  confidence_score: number;
  status: 'pending' | 'approved' | 'rejected' | 'modified';
  created_at: string;
  projected_risk_after?: number;
  drafted_announcement?: string;
  behavior_classification?: string;
  recommended_actions?: any[];
}

export interface AuditLogData {
  id: string;
  actor_id?: string;
  user_email?: string;
  user_role?: string;
  action: string;
  target?: string;
  target_resource?: string;
  before_state?: any;
  after_state?: any;
  ip_address?: string;
  created_at?: string;
  timestamp?: string;
  details?: string;
}

export interface EventData {
  id: string;
  name: string;
  date: string;
  venue: string;
  status: 'upcoming' | 'active' | 'paused' | 'completed';
}

export interface UserData {
  id: string;
  name: string;
  email: string;
  phone?: string;
  role: 'citizen' | 'field_officer' | 'operator' | 'event_admin' | 'system_admin';
  is_active: boolean;
  created_at: string;
}

export interface NotificationPolicyRule {
  risk_range: string;
  inform_citizen: boolean;
  notify_operator: boolean;
  require_operator_approval: boolean;
  description: string;
}

export interface RbacMatrixItem {
  path: string;
  methods: string[];
  name: string;
  allowed_roles: string[];
}

export interface HealthServiceDetail {
  name: string;
  status: 'healthy' | 'degraded';
  detail: string;
}

export interface SystemHealthData {
  overall_status: 'healthy' | 'degraded';
  environment: string;
  services: {
    api: HealthServiceDetail;
    database: HealthServiceDetail;
    ai_engine: HealthServiceDetail;
    notifications: HealthServiceDetail;
  };
}

export const api = {
  // 1. Overview Map & Zone Telemetry Data
  async fetchOverviewData(): Promise<{ event: any; zones: ZoneData[]; gates: GateData[] }> {
    try {
      const res = await fetch(`${API_BASE_URL}/citizens/map-data`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchOverviewData error:', e);
      return { event: null, zones: [], gates: [] };
    }
  },

  // 2. Zone Risk Detail & XAI Explanation
  async fetchZoneRisk(zoneId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/operator/zones/${zoneId}/risk`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchZoneRisk error:', e);
      throw e;
    }
  },

  // Helper to validate UUID strings
  isValidUUID(id?: string): boolean {
    return Boolean(id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id));
  },

  // 2b. Event Adjacencies & Panic Propagation Graph
  async fetchEventAdjacencies(eventId: string) {
    if (!this.isValidUUID(eventId)) {
      return { adjacencies: [], propagation_graph: {} };
    }
    try {
      const res = await fetch(`${API_BASE_URL}/operator/events/${eventId}/adjacencies`);
      if (!res.ok) return { adjacencies: [], propagation_graph: {} };
      return await res.json();
    } catch (e) {
      return { adjacencies: [], propagation_graph: {} };
    }
  },

  // 2c. Barricade Configuration Endpoints (Prompt 2)
  async fetchEventBarricades(eventId: string): Promise<BarricadeData[]> {
    if (!this.isValidUUID(eventId)) {
      return [];
    }
    try {
      const res = await fetch(`${API_BASE_URL}/operator/events/${eventId}/barricades`);
      if (!res.ok) return [];
      return await res.json();
    } catch (e) {
      return [];
    }
  },


  async reconfigureBarricade(barricadeId: string, current_configuration: BarricadeData['current_configuration']) {
    try {
      const res = await fetch(`${API_BASE_URL}/operator/barricades/${barricadeId}/reconfigure`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_configuration }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API reconfigureBarricade error:', e);
      throw e;
    }
  },

  async fetchZoneDensityGrid(zoneId: string, rows: number = 10, cols: number = 10): Promise<DensityGridData> {
    try {
      const res = await fetch(`${API_BASE_URL}/operator/zones/${zoneId}/density-grid?grid_rows=${rows}&grid_cols=${cols}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchZoneDensityGrid error:', e);
      // Fallback response
      return {
        zone_id: zoneId,
        zone_name: `Zone ${zoneId}`,
        calibration_method: 'homography',
        is_calibrated: true,
        fallback_to_flat_fill: false,
        grid_dims: [rows, cols],
        average_density_peds_m2: 2.2,
        max_localized_density_peds_m2: 3.8,
        grid_densities_peds_m2: Array(rows).fill(Array(cols).fill(2.2)),
        grid_risk_scores: Array(rows).fill(Array(cols).fill(55.0))
      };
    }
  },



  // 3. Recommended Actions
  async fetchZoneRecommendation(zoneId: string, lang?: string): Promise<RecommendationData> {
    try {
      const url = `${API_BASE_URL}/operator/zones/${zoneId}/recommendation${lang ? `?lang=${lang}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchZoneRecommendation error:', e);
      throw e;
    }
  },

  // 4. Simulate Proposed Action
  async simulateIntervention(zoneId: string, proposedAction: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/operator/zones/${zoneId}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposed_action: proposedAction }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API simulateIntervention error:', e);
      throw e;
    }
  },

  // 5. Decide Recommendation (Approve / Modify / Reject)
  async decideRecommendation(
    recommendationId: string,
    decision: 'approved' | 'rejected' | 'modified',
    modifiedAction?: string,
    editedAnnouncement?: string,
    originalDraftAnnouncement?: string
  ) {
    try {
      const res = await fetch(`${API_BASE_URL}/operator/recommendations/${recommendationId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: decision,
          modified_action: modifiedAction,
          edited_announcement: editedAnnouncement,
          original_draft_announcement: originalDraftAnnouncement,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API decideRecommendation error:', e);
      throw e;
    }
  },

  // 6. Fetch Incidents
  async fetchIncidents(): Promise<IncidentData[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/citizens/incidents`);
      if (!res.ok) return [];
      return await res.json();
    } catch (e) {
      return [];
    }
  },


  // 7. Update Incident Status
  async updateIncidentStatus(incidentId: string, status: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/citizens/incidents/${incidentId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API updateIncidentStatus error:', e);
      throw e;
    }
  },

  // 8. Fetch Officers Roster
  async fetchOfficers(): Promise<OfficerData[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/officers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = await res.json();
      return (raw || []).map((off: any) => ({
        id: off.id,
        name: off.name || 'Field Officer',
        badge_number: `BADGE-${off.id ? off.id.substring(0, 5).toUpperCase() : 'FO-1'}`,
        assigned_zone_name: off.current_assignment?.zone_id ? `Sector (${off.current_assignment.zone_id.substring(0, 6)})` : 'Unassigned Baseline',
        assigned_zone_id: off.current_assignment?.zone_id || '',
        status: off.current_assignment?.status || 'on_break',
        current_task: off.current_assignment?.task_description || 'Standby & monitoring',
        battery_level: 95,
        last_ping: 'Just now',
        email: off.email,
        phone: off.phone,
        is_active: off.is_active,
      }));
    } catch (e) {
      console.error('API fetchOfficers error:', e);
      return [];
    }
  },

  // ==========================================
  // EVENT ADMINISTRATOR API METHODS
  // ==========================================

  async fetchEvents(): Promise<EventData[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/events`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchEvents error:', e);
      return [];
    }
  },

  async updateEvent(eventId: string, payload: Partial<EventData>) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API updateEvent error:', e);
      throw e;
    }
  },

  async fetchAdminZones(): Promise<ZoneData[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/zones`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchAdminZones error:', e);
      return [];
    }
  },

  async createZone(payload: { name: string; capacity: number; event_id?: string; geo_polygon?: any }) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/zones`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API createZone error:', e);
      throw e;
    }
  },

  async updateZone(zoneId: string, payload: Partial<ZoneData>) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/zones/${zoneId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API updateZone error:', e);
      throw e;
    }
  },

  async deleteZone(zoneId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/zones/${zoneId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API deleteZone error:', e);
      throw e;
    }
  },

  async fetchAdminGates(): Promise<GateData[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/gates`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchAdminGates error:', e);
      return [];
    }
  },

  async createGate(payload: { name: string; type: string; capacity_per_min: number; zone_id: string; status?: string }) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/gates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, status: payload.status || 'open' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API createGate error:', e);
      throw e;
    }
  },

  async updateGate(gateId: string, payload: Partial<GateData>) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/gates/${gateId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API updateGate error:', e);
      throw e;
    }
  },

  async deleteGate(gateId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/gates/${gateId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API deleteGate error:', e);
      throw e;
    }
  },

  async fetchAdminOfficers(): Promise<any[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/officers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchAdminOfficers error:', e);
      return [];
    }
  },

  async assignOfficer(payload: { officer_id: string; zone_id: string; task_description: string }) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/officers/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API assignOfficer error:', e);
      throw e;
    }
  },

  async fetchNotificationPolicy(): Promise<Record<string, NotificationPolicyRule>> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/notification-policy`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchNotificationPolicy error:', e);
      throw e;
    }
  },

  async updateNotificationPolicy(policy: Record<string, NotificationPolicyRule>) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/notification-policy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(policy),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API updateNotificationPolicy error:', e);
      throw e;
    }
  },

  // ==========================================
  // SYSTEM ADMINISTRATOR API METHODS
  // ==========================================

  async fetchAdminUsers(search?: string, role?: string): Promise<UserData[]> {
    try {
      const queryParams = new URLSearchParams();
      if (search) queryParams.append('search', search);
      if (role) queryParams.append('role', role);

      const res = await fetch(`${API_BASE_URL}/admin/users?${queryParams.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchAdminUsers error:', e);
      return [];
    }
  },

  async inviteStaffUser(payload: { email: string; name: string; role: string }) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (e) {
      console.error('API inviteStaffUser error:', e);
      throw e;
    }
  },

  async updateUserRole(userId: string, role: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API updateUserRole error:', e);
      throw e;
    }
  },

  async toggleUserStatus(userId: string, isActive: boolean) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: isActive }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API toggleUserStatus error:', e);
      throw e;
    }
  },

  async resetUserPassword(userId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/reset-password`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API resetUserPassword error:', e);
      throw e;
    }
  },

  async fetchRbacMatrix(): Promise<RbacMatrixItem[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/rbac-matrix`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchRbacMatrix error:', e);
      return [];
    }
  },

  async fetchSystemHealth(): Promise<SystemHealthData> {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchSystemHealth error:', e);
      throw e;
    }
  },

  async fetchSearchableAuditLogs(search?: string, action?: string): Promise<AuditLogData[]> {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (action) params.append('action', action);

      const res = await fetch(`${API_BASE_URL}/admin/audit-logs?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchSearchableAuditLogs error:', e);
      return [];
    }
  },

  // ==========================================
  // ANALYTICS & TRENDS API METHODS (Prompt 4)
  // ==========================================

  async fetchZoneTrends(eventId: string, zoneId?: string, hours: number = 1) {
    try {
      const params = new URLSearchParams();
      if (zoneId) params.append('zone_id', zoneId);
      params.append('hours', hours.toString());

      const res = await fetch(`${API_BASE_URL}/events/${eventId}/analytics/zone-trends?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchZoneTrends error:', e);
      return { snapshots: [], derived_stats: {} };
    }
  },

  async fetchEventAnalyticsSummary(eventId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/analytics/summary`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API fetchEventAnalyticsSummary error:', e);
      return null;
    }
  },

  async exportPostEventReport(eventId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/analytics/export-report`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('API exportPostEventReport error:', e);
      throw e;
    }
  },
};

