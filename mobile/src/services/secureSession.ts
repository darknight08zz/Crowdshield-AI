import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL } from '../config/constants';

const ACCESS_TOKEN_KEY = 'cs_access_token';
const REFRESH_TOKEN_KEY = 'cs_refresh_token';
const USER_SESSION_KEY = 'cs_user_session';
const BIOMETRICS_KEY = 'cs_biometrics_enabled';
const ONBOARDING_KEY = 'cs_onboarding_completed';

export interface StoredUser {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  role: 'citizen' | 'field_officer' | 'operator' | 'event_admin' | 'system_admin';
  account_status: string;
}

export const secureSession = {
  async saveTokens(accessToken: string, refreshToken: string) {
    try {
      await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
      await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
    } catch (e) {
      console.error('Failed to save tokens to SecureStore:', e);
    }
  },

  async saveUserSession(user: StoredUser) {
    try {
      await SecureStore.setItemAsync(USER_SESSION_KEY, JSON.stringify(user));
    } catch (e) {
      console.error('Failed to save user session to SecureStore:', e);
    }
  },

  async getAccessToken(): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  async getRefreshToken(): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  async getUserSession(): Promise<StoredUser | null> {
    try {
      const raw = await SecureStore.getItemAsync(USER_SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async clearSession() {
    try {
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
      await SecureStore.deleteItemAsync(USER_SESSION_KEY);
    } catch (e) {
      console.error('Failed to clear session from SecureStore:', e);
    }
  },

  async setBiometricsEnabled(enabled: boolean) {
    try {
      await SecureStore.setItemAsync(BIOMETRICS_KEY, enabled ? 'true' : 'false');
    } catch (e) {
      console.error('Failed to set biometrics flag:', e);
    }
  },

  async getBiometricsEnabled(): Promise<boolean> {
    try {
      const val = await SecureStore.getItemAsync(BIOMETRICS_KEY);
      return val === 'true';
    } catch {
      return false;
    }
  },

  async setOnboardingCompleted(completed: boolean) {
    try {
      await SecureStore.setItemAsync(ONBOARDING_KEY, completed ? 'true' : 'false');
    } catch (e) {
      console.error('Failed to set onboarding flag:', e);
    }
  },

  async getOnboardingCompleted(): Promise<boolean> {
    try {
      const val = await SecureStore.getItemAsync(ONBOARDING_KEY);
      return val === 'true';
    } catch {
      return false;
    }
  },

  async refreshAccessToken(): Promise<string | null> {
    try {
      const refreshToken = await this.getRefreshToken();
      if (!refreshToken) return null;

      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return null;

      const data = await res.json();
      if (data.access_token) {
        await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, data.access_token);
        if (data.refresh_token) {
          await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.refresh_token);
        }
        return data.access_token;
      }
      return null;
    } catch (e) {
      console.error('Silent token refresh failed:', e);
      return null;
    }
  }
};
