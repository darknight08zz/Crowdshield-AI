import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Shield, MapPin, Bell, Camera, AlertTriangle, ArrowRight } from 'lucide-react-native';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as ImagePicker from 'expo-image-picker';
import { useAuthStore } from '../../store/useAuthStore';
import { theme } from '../../config/theme';

interface OnboardingProps {
  onFinish: () => void;
  onEmergencyBypass: () => void;
}

export const OnboardingScreen: React.FC<OnboardingProps> = ({ onFinish, onEmergencyBypass }) => {
  const setOnboardingCompleted = useAuthStore((s) => s.setOnboardingCompleted);
  const [permissionsGranted, setPermissionsGranted] = useState({
    location: false,
    notifications: false,
    camera: false,
  });

  const requestPermissions = async () => {
    try {
      const { status: locStatus } = await Location.requestForegroundPermissionsAsync();
      const locGranted = locStatus === 'granted';

      const { status: notifStatus } = await Notifications.requestPermissionsAsync();
      const notifGranted = notifStatus === 'granted';

      const { status: camStatus } = await ImagePicker.requestCameraPermissionsAsync();
      const camGranted = camStatus === 'granted';

      setPermissionsGranted({
        location: locGranted,
        notifications: notifGranted,
        camera: camGranted,
      });

      await setOnboardingCompleted(true);
      onFinish();
    } catch (e) {
      console.error('Error requesting permissions:', e);
      await setOnboardingCompleted(true);
      onFinish();
    }
  };

  const handleSkip = async () => {
    await setOnboardingCompleted(true);
    onFinish();
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Emergency Bypass Header Banner */}
        <TouchableOpacity style={styles.emergencyBanner} onPress={onEmergencyBypass} activeOpacity={0.85}>
          <View style={styles.emergencyBannerContent}>
            <AlertTriangle size={22} color={theme.colors.neutral.textHeading} style={{ marginRight: 8 }} />
            <Text style={styles.emergencyBannerText}>In an Active Emergency? Tap for Instant SOS</Text>
          </View>
        </TouchableOpacity>

        {/* Brand Header */}
        <View style={styles.header}>
          <View style={styles.logoBadge}>
            <Shield size={40} color={theme.colors.brand.primary} />
          </View>
          <Text style={styles.title}>Welcome to CrowdShield</Text>
          <Text style={styles.subtitle}>
            Real-time public safety, crowd surge tracking, and emergency response management.
          </Text>
        </View>

        {/* Permission Context List */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Why We Need Device Permissions</Text>

          <View style={styles.permRow}>
            <View style={[styles.iconContainer, { backgroundColor: theme.colors.brand.glow }]}>
              <MapPin size={22} color={theme.colors.brand.primary} />
            </View>
            <View style={styles.permTextGroup}>
              <Text style={styles.permTitle}>Location Services</Text>
              <Text style={styles.permDesc}>
                Displays crowd density heatmaps near you and routes you safely away from danger zones.
              </Text>
            </View>
          </View>

          <View style={styles.permRow}>
            <View style={[styles.iconContainer, { backgroundColor: theme.colors.risk.HIGH.bg }]}>
              <Bell size={22} color={theme.colors.risk.HIGH.hex} />
            </View>
            <View style={styles.permTextGroup}>
              <Text style={styles.permTitle}>Emergency Notifications</Text>
              <Text style={styles.permDesc}>
                Delivers immediate warnings for stampedes, gate closures, or evacuation alerts.
              </Text>
            </View>
          </View>

          <View style={styles.permRow}>
            <View style={[styles.iconContainer, { backgroundColor: 'rgba(168, 85, 247, 0.15)' }]}>
              <Camera size={22} color="#A855F7" />
            </View>
            <View style={styles.permTextGroup}>
              <Text style={styles.permTitle}>Camera Access</Text>
              <Text style={styles.permDesc}>
                Allows you to attach photo evidence when reporting safety hazards or crowd congestion.
              </Text>
            </View>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.actionsGroup}>
          <TouchableOpacity style={styles.primaryBtn} onPress={requestPermissions} activeOpacity={0.85}>
            <Text style={styles.primaryBtnText}>Enable Permissions & Continue</Text>
            <ArrowRight size={20} color={theme.colors.neutral.textHeading} style={{ marginLeft: 8 }} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryBtn} onPress={handleSkip} activeOpacity={0.7}>
            <Text style={styles.secondaryBtnText}>Skip Permissions for Now</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
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
  emergencyBanner: {
    backgroundColor: theme.colors.risk.CRITICAL.border,
    borderRadius: theme.spacing.spacious.radius,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 20,
    minHeight: 48,
    justifyContent: 'center',
  },
  emergencyBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  emergencyBannerText: {
    color: theme.colors.neutral.textHeading,
    fontWeight: '700',
    fontSize: theme.typography.sizes.body,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoBadge: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: theme.colors.brand.glow,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: theme.colors.brand.primary,
  },
  title: {
    fontSize: theme.typography.sizes.display - 4,
    fontWeight: '800',
    color: theme.colors.neutral.textHeading,
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: theme.typography.sizes.body,
    color: theme.colors.neutral.textMuted,
    textAlign: 'center',
    lineHeight: 22,
  },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
  },
  cardTitle: {
    fontSize: theme.typography.sizes.cardTitle,
    fontWeight: '700',
    color: theme.colors.neutral.textHeading,
    marginBottom: 18,
  },
  permRow: {
    flexDirection: 'row',
    marginBottom: 20,
    alignItems: 'flex-start',
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  permTextGroup: {
    flex: 1,
  },
  permTitle: {
    fontSize: theme.typography.sizes.cardTitle,
    fontWeight: '700',
    color: theme.colors.neutral.textHeading,
    marginBottom: 4,
  },
  permDesc: {
    fontSize: theme.typography.sizes.caption,
    color: theme.colors.neutral.textMuted,
    lineHeight: 18,
  },
  actionsGroup: {
    gap: theme.spacing.spacious.gap,
  },
  primaryBtn: {
    backgroundColor: theme.colors.brand.primary,
    borderRadius: theme.spacing.spacious.radius,
    minHeight: 50,
    paddingVertical: 14,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryBtnText: {
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.cardTitle,
    fontWeight: '700',
  },
  secondaryBtn: {
    minHeight: 48,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryBtnText: {
    color: theme.colors.neutral.textMuted,
    fontSize: theme.typography.sizes.body,
    fontWeight: '600',
  },
});
