import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { KeyRound, ArrowLeft, CheckCircle2 } from 'lucide-react-native';
import { API_BASE_URL } from '../../config/constants';
import { useAuthStore } from '../../store/useAuthStore';

interface OtpProps {
  email: string;
  onNavigateLogin: () => void;
}

export const OtpVerificationScreen: React.FC<OtpProps> = ({ email, onNavigateLogin }) => {
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const setSession = useAuthStore((s) => s.setSession);

  const handleVerify = async () => {
    if (!otp.trim() || otp.trim().length < 6) {
      Alert.alert('Invalid Code', 'Please enter the 6-digit verification code.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), otp: otp.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'OTP verification failed. Check code and try again.');
      }

      Alert.alert('Verification Successful', 'Your account is now verified! Logging you in...', [
        {
          text: 'Continue',
          onPress: async () => {
            if (data.access_token && data.user) {
              await setSession(data.user, data.access_token, data.refresh_token);
            } else {
              onNavigateLogin();
            }
          },
        },
      ]);
    } catch (e: any) {
      Alert.alert('Verification Error', e.message || 'Verification failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <TouchableOpacity style={styles.backBtn} onPress={onNavigateLogin}>
        <ArrowLeft size={20} color="#94A3B8" />
        <Text style={styles.backBtnText}>Cancel & Sign In</Text>
      </TouchableOpacity>

      <View style={styles.content}>
        <View style={styles.logoBadge}>
          <KeyRound size={40} color="#38BDF8" />
        </View>

        <Text style={styles.title}>Account Verification</Text>
        <Text style={styles.subtitle}>
          Enter the 6-digit confirmation code sent to{' '}
          <Text style={{ color: '#F8FAFC', fontWeight: '600' }}>{email || 'your email'}</Text>.
        </Text>
        <Text style={styles.devNote}>(Development default OTP: 123456)</Text>

        <View style={styles.card}>
          <Text style={styles.label}>Verification Code</Text>
          <TextInput
            style={styles.otpInput}
            placeholder="123456"
            placeholderTextColor="#64748B"
            value={otp}
            onChangeText={setOtp}
            keyboardType="number-pad"
            maxLength={6}
          />

          <TouchableOpacity
            style={styles.verifyBtn}
            onPress={handleVerify}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <CheckCircle2 size={20} color="#FFFFFF" style={{ marginRight: 8 }} />
                <Text style={styles.verifyBtnText}>Confirm Code</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
    padding: 20,
  },
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  backBtnText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  content: {
    alignItems: 'center',
  },
  logoBadge: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.3)',
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    color: '#F8FAFC',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 4,
  },
  devNote: {
    fontSize: 12,
    color: '#38BDF8',
    marginBottom: 24,
  },
  card: {
    width: '100%',
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#CBD5E1',
    marginBottom: 8,
  },
  otpInput: {
    backgroundColor: '#0F172A',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
    height: 52,
    color: '#F8FAFC',
    fontSize: 20,
    fontWeight: '800',
    textAlign: 'center',
    letterSpacing: 8,
    marginBottom: 16,
  },
  verifyBtn: {
    backgroundColor: '#0284C7',
    borderRadius: 12,
    height: 50,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  verifyBtnText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
