import { create } from 'zustand';
import { secureSession, StoredUser } from '../services/secureSession';

export type UserRole = 'citizen' | 'field_officer' | 'operator' | 'event_admin' | 'system_admin';

interface AuthState {
  user: StoredUser | null;
  role: UserRole;
  accessToken: string | null;
  accountStatus: 'active' | 'unverified' | 'disabled';
  isLoading: boolean;
  biometricsLocked: boolean;
  onboardingCompleted: boolean;
  
  initializeAuth: () => Promise<void>;
  setSession: (user: StoredUser, accessToken: string, refreshToken: string) => Promise<void>;
  setRole: (role: UserRole) => void;
  setAccountDisabled: () => void;
  unlockBiometrics: () => void;
  setOnboardingCompleted: (completed: boolean) => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  role: 'citizen',
  accessToken: null,
  accountStatus: 'active',
  isLoading: true,
  biometricsLocked: false,
  onboardingCompleted: false,

  initializeAuth: async () => {
    try {
      const storedUser = await secureSession.getUserSession();
      const token = await secureSession.getAccessToken();
      const onboarding = await secureSession.getOnboardingCompleted();
      const biometricsEnabled = await secureSession.getBiometricsEnabled();

      if (storedUser && token) {
        if (storedUser.account_status === 'disabled') {
          set({
            user: storedUser,
            role: storedUser.role,
            accessToken: token,
            accountStatus: 'disabled',
            isLoading: false,
            onboardingCompleted: onboarding
          });
          return;
        }

        const isOfficer = storedUser.role === 'field_officer';
        set({
          user: storedUser,
          role: storedUser.role,
          accessToken: token,
          accountStatus: (storedUser.account_status as any) || 'active',
          isLoading: false,
          biometricsLocked: isOfficer && biometricsEnabled,
          onboardingCompleted: onboarding
        });
      } else {
        set({
          user: null,
          role: 'citizen',
          accessToken: null,
          accountStatus: 'active',
          isLoading: false,
          biometricsLocked: false,
          onboardingCompleted: onboarding
        });
      }
    } catch (e) {
      console.error('Failed to initialize auth from storage:', e);
      set({ isLoading: false });
    }
  },

  setSession: async (user: StoredUser, accessToken: string, refreshToken: string) => {
    await secureSession.saveTokens(accessToken, refreshToken);
    await secureSession.saveUserSession(user);

    const isOfficer = user.role === 'field_officer';
    const biometricsEnabled = await secureSession.getBiometricsEnabled();

    set({
      user,
      role: user.role,
      accessToken,
      accountStatus: (user.account_status as any) || 'active',
      isLoading: false,
      biometricsLocked: isOfficer && biometricsEnabled,
    });
  },

  setRole: (role) => set({ role }),

  setAccountDisabled: () => {
    set({ accountStatus: 'disabled' });
  },

  unlockBiometrics: () => {
    set({ biometricsLocked: false });
  },

  setOnboardingCompleted: async (completed: boolean) => {
    await secureSession.setOnboardingCompleted(completed);
    set({ onboardingCompleted: completed });
  },

  signOut: async () => {
    await secureSession.clearSession();
    set({
      user: null,
      role: 'citizen',
      accessToken: null,
      accountStatus: 'active',
      isLoading: false,
      biometricsLocked: false,
    });
  },
}));
