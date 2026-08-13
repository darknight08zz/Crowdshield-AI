import React, { useEffect } from 'react';
import { LogBox } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './src/services/i18n'; // Initialize i18n
import { RootNavigator } from './src/navigation/RootNavigator';
import { useAuthStore } from './src/store/useAuthStore';
import { useOfflineStore } from './src/store/useOfflineStore';
import { supabase } from './src/services/supabase';
import { registerForPushNotificationsAsync } from './src/services/push';
import { flushOfflineQueue } from './src/services/offlineQueue';

// Ignore Expo Go Push Notification SDK 54 deprecation warning overlay
LogBox.ignoreLogs([
  'Android Push notifications (remote notifications) functionality',
  'expo-notifications',
]);

const queryClient = new QueryClient();

export default function App() {
  const setSession = useAuthStore((s) => s.setSession);
  const loadQueue = useOfflineStore((s) => s.loadQueue);

  useEffect(() => {
    // Load offline queue from SecureStore
    loadQueue();

    // Try flushing offline queue on startup
    flushOfflineQueue();

    // Listen to Supabase Auth state changes
    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setSession(
          {
            id: session.user.id,
            name: session.user.email || 'User',
            email: session.user.email,
            role: 'citizen',
            account_status: 'active',
          },
          session.access_token,
          session.refresh_token || ''
        );
        registerForPushNotificationsAsync();
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <NavigationContainer>
        <StatusBar style="light" />
        <RootNavigator />
      </NavigationContainer>
    </QueryClientProvider>
  );
}
