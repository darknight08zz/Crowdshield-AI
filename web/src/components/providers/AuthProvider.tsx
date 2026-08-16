'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export interface UserSession {
  id: string;
  name: string;
  email: string;
  role: 'citizen' | 'field_officer' | 'operator' | 'event_admin' | 'system_admin';
  account_status: string;
}

interface AuthContextType {
  user: UserSession | null;
  role: string | null;
  accessToken: string | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: null,
  accessToken: null,
  isLoading: true,
  logout: async () => {},
  refreshSession: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserSession | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchSession = async () => {
    try {
      const sessionRes = await fetch('/api/auth/session');
      if (sessionRes.ok) {
        const data = await sessionRes.json();
        if (data.authenticated && data.user) {
          setUser(data.user);
        } else {
          setUser(null);
        }
      } else {
        setUser(null);
      }

      const tokenRes = await fetch('/api/auth/token');
      if (tokenRes.ok) {
        const tokenData = await tokenRes.json();
        const tok = tokenData.token || null;
        setAccessToken(tok);
        if (tok && typeof window !== 'undefined') {
          localStorage.setItem('token', tok);
        }
      } else {
        setAccessToken(null);
      }
    } catch (e) {
      console.error('Error loading session:', e);
      setUser(null);
      setAccessToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSession();

    // Silent background token refresh ping every 10 minutes to prevent mid-shift expiry
    const refreshInterval = setInterval(() => {
      fetchSession();
    }, 10 * 60 * 1000);

    return () => clearInterval(refreshInterval);
  }, []);

  const logout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      setUser(null);
      setAccessToken(null);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
      }
      router.push('/auth/login');
      router.refresh();
    } catch (e) {
      console.error('Logout error:', e);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || null,
        accessToken,
        isLoading,
        logout,
        refreshSession: fetchSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
