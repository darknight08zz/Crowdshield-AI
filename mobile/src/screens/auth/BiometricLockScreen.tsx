import React, { useEffect, useState } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Fingerprint, Shield, LogOut } from 'lucide-react-native';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuthStore } from '../../store/useAuthStore';

export const BiometricLockScreen: React.FC = () => {
  const unlockBiometrics = useAuthStore((s) => s.unlockBiometrics);
  const signOut = useAuthStore((s) => s.signOut);
  const user = useAuthStore((s) => s.user);
  const [authenticating, setAuthenticating] = useState(false);

  const triggerBiometricAuth = async () => {
    try {
      setAuthenticating(true);
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();

      if (!hasHardware || !isEnrolled) {
        // Fallback unlock if hardware/enrolled biometrics unavailable on test device
        unlockBiometrics();
        return;
      }

      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Unlock CrowdShield Officer Terminal',
        fallbackLabel: 'Use Device Passcode',
        disableDeviceFallback: false,
      });

      if (result.success) {
        unlockBiometrics();
      } else {
        Alert.alert('Authentication Failed', 'Biometric verification was not successful.');
      }
    } catch (e: any) {
      console.error('Biometric error:', e);
      unlockBiometrics(); // Fallback unlock
    } finally {
      setAuthenticating(false);
    }
  };

  useEffect(() => {
    triggerBiometricAuth();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.badge}>
          <Shield size={44} color="#38BDF8" />
        </View>

        <Text style={styles.title}>Officer Terminal Locked</Text>
        <Text style={styles.subtitle}>
          Welcome back, {user?.name || 'Officer'}. Scan your Face ID / Fingerprint to resume active shift.
        </Text>

        <TouchableOpacity
          style={styles.biometricBtn}
          onPress={triggerBiometricAuth}
          disabled={authenticating}
          activeOpacity={0.85}
        >
          {authenticating ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <>
              <Fingerprint size={32} color="#38BDF8" style={{ marginBottom: 8 }} />
              <Text style={styles.biometricBtnText}>Tap to Scan Biometrics</Text>
            </>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.logoutBtn} onPress={signOut} activeOpacity={0.85}>
          <LogOut size={18} color="#94A3B8" style={{ marginRight: 8 }} />
          <Text style={styles.logoutBtnText}>Sign Out of Shift</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
    justifyContent: 'center',
    padding: 20,
  },
  content: {
    alignItems: 'center',
  },
  badge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.3)',
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    color: '#F8FAFC',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 32,
    paddingHorizontal: 20,
  },
  biometricBtn: {
    width: '100%',
    backgroundColor: '#1E293B',
    borderRadius: 16,
    paddingVertical: 28,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#38BDF8',
    marginBottom: 24,
  },
  biometricBtnText: {
    color: '#F8FAFC',
    fontSize: 15,
    fontWeight: '700',
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  logoutBtnText: {
    color: '#94A3B8',
    fontSize: 15,
    fontWeight: '600',
  },
});
