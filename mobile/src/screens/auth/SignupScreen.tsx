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
import { User, Mail, Lock, Phone, ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-react-native';
import { API_BASE_URL } from '../../config/constants';
import { theme } from '../../config/theme';

interface SignupScreenProps {
  onNavigateLogin: () => void;
  onNavigateOtp: (email: string) => void;
}

export const SignupScreen: React.FC<SignupScreenProps> = ({
  onNavigateLogin,
  onNavigateOtp,
}) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignup = async () => {
    if (!name.trim() || !email.trim() || !password.trim()) {
      Alert.alert('Missing Details', 'Please enter your full name, email, and password.');
      return;
    }

    if (password.length < 8) {
      Alert.alert('Weak Password', 'Password must be at least 8 characters long.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          phone: phone.trim() || undefined,
          password: password.trim(),
          role: 'citizen',
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed. Please try again.');
      }

      Alert.alert(
        'Account Created',
        'Verification code sent! Please verify your email to activate full citizen incident reporting.',
        [
          {
            text: 'Verify OTP',
            onPress: () => onNavigateOtp(email.trim()),
          },
        ]
      );
    } catch (err: any) {
      Alert.alert('Registration Error', err.message || 'Failed to create account.');
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
          {/* Back to Login Header Button */}
          <TouchableOpacity style={styles.backBtn} onPress={onNavigateLogin}>
            <ArrowLeft size={20} color={theme.colors.neutral.textMuted} />
            <Text style={styles.backBtnText}>Back to Sign In</Text>
          </TouchableOpacity>

          {/* Title Header */}
          <View style={styles.header}>
            <View style={styles.logoBadge}>
              <ShieldCheck size={36} color={theme.colors.brand.primary} />
            </View>
            <Text style={styles.title}>Citizen Registration</Text>
            <Text style={styles.subtitle}>
              Create your free account to receive live crowd heatmaps and report safety incidents.
            </Text>
          </View>

          {/* Registration Form Card */}
          <View style={styles.card}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Full Name</Text>
              <View style={styles.inputWrapper}>
                <User size={20} color={theme.colors.neutral.textMuted} style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="John Doe"
                  placeholderTextColor={theme.colors.neutral.textMuted}
                  value={name}
                  onChangeText={setName}
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Email Address</Text>
              <View style={styles.inputWrapper}>
                <Mail size={20} color={theme.colors.neutral.textMuted} style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="citizen@example.com"
                  placeholderTextColor={theme.colors.neutral.textMuted}
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  keyboardType="email-address"
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Phone Number (Optional)</Text>
              <View style={styles.inputWrapper}>
                <Phone size={20} color={theme.colors.neutral.textMuted} style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="+1 555 019 2831"
                  placeholderTextColor={theme.colors.neutral.textMuted}
                  value={phone}
                  onChangeText={setPhone}
                  keyboardType="phone-pad"
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Password</Text>
              <View style={styles.inputWrapper}>
                <Lock size={20} color={theme.colors.neutral.textMuted} style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="At least 8 characters"
                  placeholderTextColor={theme.colors.neutral.textMuted}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                />
              </View>
            </View>

            <TouchableOpacity
              style={styles.signupBtn}
              onPress={handleSignup}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color={theme.colors.neutral.textHeading} />
              ) : (
                <>
                  <Text style={styles.signupBtnText}>Create Account</Text>
                  <ArrowRight size={20} color={theme.colors.neutral.textHeading} style={{ marginLeft: 6 }} />
                </>
              )}
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
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    minHeight: 44,
  },
  backBtnText: {
    color: theme.colors.neutral.textMuted,
    fontSize: theme.typography.sizes.body,
    fontWeight: '600',
    marginLeft: 6,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoBadge: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: theme.colors.brand.glow,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 14,
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
  },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: theme.typography.sizes.body,
    fontWeight: '600',
    color: theme.colors.neutral.textBody,
    marginBottom: 6,
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
  signupBtn: {
    backgroundColor: theme.colors.brand.primary,
    borderRadius: theme.spacing.spacious.radius,
    minHeight: 50,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  signupBtnText: {
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.cardTitle,
    fontWeight: '700',
  },
});
