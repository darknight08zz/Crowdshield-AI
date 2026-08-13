import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Shield, AlertTriangle, Lock, Mail, ArrowRight } from 'lucide-react-native';
import { API_BASE_URL } from '../../config/constants';
import { theme } from '../../config/theme';
import { useAuthStore } from '../../store/useAuthStore';

interface LoginScreenProps {
  onNavigateSignup: () => void;
  onNavigateForgotPassword: () => void;
  onEmergencyBypass: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  onNavigateSignup,
  onNavigateForgotPassword,
  onEmergencyBypass,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const setSession = useAuthStore((s) => s.setSession);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Missing Credentials', 'Please enter both email/phone and password.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password: password.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed. Please check credentials.');
      }

      await setSession(
        {
          id: data.user.id,
          name: data.user.name,
          email: data.user.email,
          role: data.user.role,
          account_status: data.user.account_status,
        },
        data.access_token,
        data.refresh_token
      );
    } catch (err: any) {
      Alert.alert('Login Error', err.message || 'An error occurred during authentication.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Emergency SOS Access Button */}
          <TouchableOpacity style={styles.sosButton} onPress={onEmergencyBypass} activeOpacity={0.85}>
            <AlertTriangle size={20} color={theme.colors.neutral.textHeading} style={{ marginRight: 8 }} />
            <Text style={styles.sosButtonText}>Emergency Mode / SOS Help (No Login Required)</Text>
          </TouchableOpacity>

          {/* Logo & Title Header */}
          <View style={styles.header}>
            <View style={styles.logoBadge}>
              <Shield size={44} color={theme.colors.brand.primary} />
            </View>
            <Text style={styles.title}>CrowdShield Login</Text>
            <Text style={styles.subtitle}>
              Log in to access Citizen incident reporting or Field Officer command dispatch.
            </Text>
          </View>

          {/* Login Form Card */}
          <View style={styles.card}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Email or Phone Number</Text>
              <View style={styles.inputWrapper}>
                <Mail size={20} color={theme.colors.neutral.textMuted} style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="user@example.com"
                  placeholderTextColor={theme.colors.neutral.textMuted}
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  keyboardType="email-address"
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <View style={styles.labelRow}>
                <Text style={styles.label}>Password</Text>
                <TouchableOpacity onPress={onNavigateForgotPassword}>
                  <Text style={styles.forgotText}>Forgot password?</Text>
                </TouchableOpacity>
              </View>
              <View style={styles.inputWrapper}>
                <Lock size={20} color={theme.colors.neutral.textMuted} style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="••••••••"
                  placeholderTextColor={theme.colors.neutral.textMuted}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                />
              </View>
            </View>

            <TouchableOpacity
              style={styles.loginBtn}
              onPress={handleLogin}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color={theme.colors.neutral.textHeading} />
              ) : (
                <>
                  <Text style={styles.loginBtnText}>Sign In</Text>
                  <ArrowRight size={20} color={theme.colors.neutral.textHeading} style={{ marginLeft: 6 }} />
                </>
              )}
            </TouchableOpacity>
          </View>

          {/* Citizen Signup Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>New to CrowdShield?</Text>
            <TouchableOpacity onPress={onNavigateSignup}>
              <Text style={styles.signupText}>Create Citizen Account</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.neutral.bgPage,
  },
  scrollContent: {
    padding: theme.spacing.spacious.padding,
    paddingBottom: 40,
  },
  sosButton: {
    backgroundColor: theme.colors.risk.CRITICAL.border,
    borderRadius: theme.spacing.spacious.radius,
    minHeight: 48,
    paddingVertical: 12,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  sosButtonText: {
    color: theme.colors.neutral.textHeading,
    fontWeight: '700',
    fontSize: theme.typography.sizes.caption + 1,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoBadge: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: theme.colors.brand.glow,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: theme.colors.brand.primary,
  },
  title: {
    fontSize: theme.typography.sizes.pageTitle,
    fontWeight: '800',
    color: theme.colors.neutral.textHeading,
    marginBottom: 6,
  },
  subtitle: {
    fontSize: theme.typography.sizes.body,
    color: theme.colors.neutral.textMuted,
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: 12,
  },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    marginBottom: 24,
  },
  inputGroup: {
    marginBottom: 18,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    fontSize: theme.typography.sizes.body,
    fontWeight: '600',
    color: theme.colors.neutral.textBody,
    marginBottom: 6,
  },
  forgotText: {
    fontSize: theme.typography.sizes.caption + 1,
    color: theme.colors.brand.primary,
    fontWeight: '600',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.neutral.bgPage,
    borderRadius: theme.spacing.compact.radius,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    paddingHorizontal: 12,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    height: 48,
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.body,
  },
  loginBtn: {
    backgroundColor: theme.colors.brand.primary,
    borderRadius: theme.spacing.spacious.radius,
    minHeight: 50,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  loginBtnText: {
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.cardTitle,
    fontWeight: '700',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  footerText: {
    color: theme.colors.neutral.textMuted,
    fontSize: theme.typography.sizes.body,
  },
  signupText: {
    color: theme.colors.brand.primary,
    fontSize: theme.typography.sizes.body,
    fontWeight: '700',
  },
});
