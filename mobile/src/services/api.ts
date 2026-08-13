import { API_BASE_URL } from '../config/constants';
import { secureSession } from './secureSession';
import { useAuthStore } from '../store/useAuthStore';
import i18n from './i18n';

async function getAuthHeader(): Promise<Record<string, string>> {
  let token = await secureSession.getAccessToken();
  if (!token) {
    token = await secureSession.refreshAccessToken();
  }
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(res: Response) {
  if (res.status === 403) {
    const errorText = await res.clone().text();
    if (errorText.includes('Account is disabled')) {
      useAuthStore.getState().setAccountDisabled();
    }
  }
  return res;
}

export const api = {
  // Fetch active event & zones with active user language parameter
  async fetchZones(lang?: string) {
    try {
      const authHeader = await getAuthHeader();
      const activeLang = lang || i18n.language || 'en';
      const rawRes = await fetch(`${API_BASE_URL}/citizens/map-data?lang=${activeLang}`, { headers: authHeader });
      const res = await handleResponse(rawRes);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('API fetchZones error:', err);
      return { event: null, zones: [], gates: [] };
    }
  },

  // Fetch zone AI recommendation & drafted public announcement in active language
  async fetchZoneRecommendation(zoneId: string, lang?: string) {
    try {
      const authHeader = await getAuthHeader();
      const activeLang = lang || i18n.language || 'en';
      const rawRes = await fetch(`${API_BASE_URL}/operator/zones/${zoneId}/recommendation?lang=${activeLang}`, { headers: authHeader });
      const res = await handleResponse(rawRes);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('API fetchZoneRecommendation error:', err);
      throw err;
    }
  },

  // Register device FCM push token with user language context
  async registerDeviceToken(fcmToken: string, platform: string = 'android') {
    try {
      const authHeader = await getAuthHeader();
      const activeLang = i18n.language || 'en';
      const headers: Record<string, string> = { 'Content-Type': 'application/json', ...authHeader };
      const rawRes = await fetch(`${API_BASE_URL}/devices/register`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ fcm_token: fcmToken, platform, language: activeLang }),
      });
      const res = await handleResponse(rawRes);
      return await res.json();
    } catch (err) {
      console.error('Device FCM registration error:', err);
    }
  },

  // Submit incident report
  async submitIncident(incidentData: { type: string; description: string; lat: number; lng: number; zone_id?: string; image_uri?: string }) {
    const authHeader = await getAuthHeader();
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...authHeader };
    const rawRes = await fetch(`${API_BASE_URL}/citizens/incidents`, {
      method: 'POST',
      headers,
      body: JSON.stringify(incidentData),
    });
    const res = await handleResponse(rawRes);
    if (!res.ok) throw new Error(`Failed to submit incident report. HTTP ${res.status}`);
    return await res.json();
  },

  // Fetch officer assigned tasks
  async fetchOfficerTasks() {
    try {
      const authHeader = await getAuthHeader();
      const rawRes = await fetch(`${API_BASE_URL}/officers/tasks`, { headers: authHeader });
      const res = await handleResponse(rawRes);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('API fetchOfficerTasks error:', err);
      return [];
    }
  },

  // Update officer task status
  async updateTaskStatus(taskId: string, status: string) {
    const authHeader = await getAuthHeader();
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...authHeader };
    const rawRes = await fetch(`${API_BASE_URL}/officers/tasks/${taskId}/status`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ status }),
    });
    const res = await handleResponse(rawRes);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },

  // Verify incident (Field Officer)
  async verifyIncident(incidentId: string, status: 'confirmed' | 'false_alarm' | 'resolved', note?: string) {
    const authHeader = await getAuthHeader();
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...authHeader };
    const rawRes = await fetch(`${API_BASE_URL}/officers/incidents/${incidentId}/verify`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ status, officer_note: note }),
    });
    const res = await handleResponse(rawRes);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }
};
