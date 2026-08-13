import React from 'react';
import { View, Text, StyleSheet, ScrollView, Linking, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { HighContrastButton } from '../../components/UI/HighContrastButton';
import { ArrowLeft } from 'lucide-react-native';
import { theme } from '../../config/theme';

interface EmergencyScreenProps {
  onBack?: () => void;
}

export const EmergencyScreen: React.FC<EmergencyScreenProps> = ({ onBack }) => {
  const { t } = useTranslation();

  const makeCall = (phoneNumber: string) => {
    Linking.openURL(`tel:${phoneNumber}`);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {onBack && (
        <TouchableOpacity style={styles.exitBtn} onPress={onBack} activeOpacity={0.8}>
          <ArrowLeft size={18} color={theme.colors.neutral.textMuted} />
          <Text style={styles.exitBtnText}>Exit Emergency Mode to Sign In</Text>
        </TouchableOpacity>
      )}

      <Text style={styles.title}>🆘 {t('citizen.emergency_sos_title')}</Text>
      <Text style={styles.subtitle}>{t('citizen.sos_warning')}</Text>

      {/* Primary Hotline Big Action */}
      <View style={styles.alertBox}>
        <Text style={styles.alertTitle}>{t('citizen.emergency_sos_title')}</Text>
        <Text style={styles.alertSub}>{t('citizen.sos_warning')}</Text>
        <HighContrastButton
          title={t('citizen.sos_call_btn')}
          variant="danger"
          onPress={() => makeCall('112')}
        />
      </View>

      {/* Nearest Help Points */}
      <Text style={styles.sectionHeader}>{t('citizen.nearest_help_points')}</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📍 {t('citizen.first_aid_station')}</Text>
        <Text style={styles.cardSub}>{t('citizen.first_aid_dist')}</Text>
        <Text style={styles.cardDetail}>Staffed by: 4 Medical Responders + 2 Police Officers</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📍 {t('citizen.police_booth')}</Text>
        <Text style={styles.cardSub}>{t('citizen.police_dist')}</Text>
        <Text style={styles.cardDetail}>Status: Unlocked & Wide Open for Evacuation</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📍 {t('citizen.fire_station')}</Text>
        <Text style={styles.cardSub}>{t('citizen.fire_dist')}</Text>
        <Text style={styles.cardDetail}>Status: Active Disaster Response Hub</Text>
      </View>

      {/* Contacts List */}
      <Text style={styles.sectionHeader}>ON-SITE DIRECTORY</Text>
      {[
        { name: t('citizen.first_aid_station'), number: '+15550199' },
        { name: t('citizen.police_booth'), number: '+15550188' },
        { name: t('citizen.fire_station'), number: '+15550177' },
      ].map((item, idx) => (
        <TouchableOpacity key={idx} style={styles.contactRow} onPress={() => makeCall(item.number)} activeOpacity={0.8}>
          <View>
            <Text style={styles.contactName}>{item.name}</Text>
            <Text style={styles.contactNumber}>{item.number}</Text>
          </View>
          <Text style={styles.callBadge}>CALL</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.spacious.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1, paddingTop: 40 },
  exitBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    minHeight: 44,
  },
  exitBtnText: {
    color: theme.colors.neutral.textMuted,
    fontSize: theme.typography.sizes.body,
    fontWeight: '600',
    marginLeft: 6,
  },
  title: { color: theme.colors.risk.CRITICAL.hex, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  subtitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, marginTop: 4, marginBottom: 16 },
  alertBox: {
    backgroundColor: theme.colors.risk.CRITICAL.bg,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 2,
    borderColor: theme.colors.risk.CRITICAL.border,
    marginBottom: 20,
  },
  alertTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.cardTitle, fontWeight: '900', textAlign: 'center' },
  alertSub: { color: theme.colors.risk.CRITICAL.hex, fontSize: theme.typography.sizes.caption, textAlign: 'center', marginBottom: 12, marginTop: 2 },
  sectionHeader: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.body, fontWeight: '800', marginBottom: 10, marginTop: 10 },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    marginBottom: 10,
  },
  cardTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.cardTitle, fontWeight: '800' },
  cardSub: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.body, marginTop: 4, fontWeight: '600' },
  cardDetail: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, marginTop: 4 },
  contactRow: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
    minHeight: 52,
  },
  contactName: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '700' },
  contactNumber: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, marginTop: 2, fontFamily: theme.typography.fontMono },
  callBadge: { color: theme.colors.brand.primary, fontWeight: '900', fontSize: theme.typography.sizes.body },
});
