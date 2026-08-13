import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuthStore } from '../store/useAuthStore';
import { OnboardingScreen } from '../screens/auth/OnboardingScreen';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { SignupScreen } from '../screens/auth/SignupScreen';
import { OtpVerificationScreen } from '../screens/auth/OtpVerificationScreen';
import { ForgotPasswordScreen } from '../screens/auth/ForgotPasswordScreen';
import { AccountDisabledScreen } from '../screens/auth/AccountDisabledScreen';
import { BiometricLockScreen } from '../screens/auth/BiometricLockScreen';
import { EmergencyScreen } from '../screens/citizen/EmergencyScreen';
import { CitizenTabs } from './CitizenTabs';
import { OfficerTabs } from './OfficerTabs';

const Stack = createNativeStackNavigator();

export const RootNavigator: React.FC = () => {
  const {
    user,
    role,
    accessToken,
    accountStatus,
    isLoading,
    biometricsLocked,
    onboardingCompleted,
    initializeAuth,
  } = useAuthStore();

  const [authScreen, setAuthScreen] = useState<'login' | 'signup' | 'otp' | 'forgot'>('login');
  const [targetOtpEmail, setTargetOtpEmail] = useState('');
  const [emergencyBypassActive, setEmergencyBypassActive] = useState(false);

  useEffect(() => {
    initializeAuth();
  }, []);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#38BDF8" />
      </View>
    );
  }

  // Emergency Bypass Override: Emergency screen accessible directly without auth/signup
  if (emergencyBypassActive) {
    return (
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="EmergencyBypass">
          {(props) => (
            <EmergencyScreen
              {...props}
              onBack={() => setEmergencyBypassActive(false)}
            />
          )}
        </Stack.Screen>
      </Stack.Navigator>
    );
  }

  // Account Disabled Enforcement
  if (accountStatus === 'disabled') {
    return <AccountDisabledScreen />;
  }

  // Biometric Unlock Enforcement (Field Officers)
  if (biometricsLocked) {
    return <BiometricLockScreen />;
  }

  const isAuthenticated = !!(user && accessToken);

  // Authenticated App Routing
  if (isAuthenticated) {
    return (
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {role === 'field_officer' ? (
          <Stack.Screen name="OfficerApp" component={OfficerTabs} />
        ) : (
          <Stack.Screen name="CitizenApp" component={CitizenTabs} />
        )}
      </Stack.Navigator>
    );
  }

  // Unauthenticated Flow: Onboarding -> Auth Screens (with direct Emergency SOS option)
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!onboardingCompleted ? (
        <Stack.Screen name="Onboarding">
          {() => (
            <OnboardingScreen
              onFinish={() => setAuthScreen('login')}
              onEmergencyBypass={() => setEmergencyBypassActive(true)}
            />
          )}
        </Stack.Screen>
      ) : authScreen === 'signup' ? (
        <Stack.Screen name="Signup">
          {() => (
            <SignupScreen
              onNavigateLogin={() => setAuthScreen('login')}
              onNavigateOtp={(email) => {
                setTargetOtpEmail(email);
                setAuthScreen('otp');
              }}
            />
          )}
        </Stack.Screen>
      ) : authScreen === 'otp' ? (
        <Stack.Screen name="OtpVerification">
          {() => (
            <OtpVerificationScreen
              email={targetOtpEmail}
              onNavigateLogin={() => setAuthScreen('login')}
            />
          )}
        </Stack.Screen>
      ) : authScreen === 'forgot' ? (
        <Stack.Screen name="ForgotPassword">
          {() => (
            <ForgotPasswordScreen onNavigateLogin={() => setAuthScreen('login')} />
          )}
        </Stack.Screen>
      ) : (
        <Stack.Screen name="Login">
          {() => (
            <LoginScreen
              onNavigateSignup={() => setAuthScreen('signup')}
              onNavigateForgotPassword={() => setAuthScreen('forgot')}
              onEmergencyBypass={() => setEmergencyBypassActive(true)}
            />
          )}
        </Stack.Screen>
      )}
    </Stack.Navigator>
  );
};

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: '#0F172A',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
