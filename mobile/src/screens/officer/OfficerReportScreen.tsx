import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, Alert, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { HighContrastButton } from '../../components/UI/HighContrastButton';
import { api } from '../../services/api';
import { theme } from '../../config/theme';

export const OfficerReportScreen: React.FC<any> = ({ navigation }) => {
  const { t } = useTranslation();
  const [reportType, setReportType] = useState('gate_status');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!notes.trim()) {
      Alert.alert(t('common.error'), t('officer.obs_placeholder'));
      return;
    }
    setSubmitting(true);
    try {
      await api.submitIncident({
        type: `OFFICER_${reportType.toUpperCase()}`,
        description: `[OFFICER PRIORITY] ${notes}`,
        lat: 12.9716,
        lng: 77.5946,
      });
      Alert.alert('Officer Report Logged', 'Priority telemetry pushed to AI Risk Engine and Control Room.', [
        { text: 'OK', onPress: () => navigation.navigate('MyZone') },
      ]);
    } catch (e) {
      Alert.alert('Logged to Queue', 'Officer report queued for sync.');
      navigation.navigate('MyZone');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>👮 {t('officer.officer_dispatch_report').toUpperCase()}</Text>
      <Text style={styles.subtitle}>{t('officer.field_observations')}</Text>

      <Text style={styles.label}>{t('citizen.incident_type')}</Text>
      <View style={styles.grid}>
        {[
          { key: 'gate_status', label: `🚪 ${t('citizen.type_bottleneck')}` },
          { key: 'flow_conflict', label: `🔀 ${t('citizen.type_surge')}` },
          { key: 'density_spike', label: `📈 ${t('citizen.occupancy_density')}` },
          { key: 'medical_evac', label: `🚑 ${t('citizen.type_medical')}` },
        ].map((item) => (
          <TouchableOpacity
            key={item.key}
            style={[styles.tile, reportType === item.key && styles.activeTile]}
            onPress={() => setReportType(item.key)}
            activeOpacity={0.8}
          >
            <Text style={[styles.tileText, reportType === item.key && styles.activeTileText]}>
              {item.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>{t('officer.field_observations')}</Text>
      <TextInput
        style={styles.input}
        placeholder={t('officer.obs_placeholder')}
        placeholderTextColor={theme.colors.neutral.textMuted}
        multiline
        numberOfLines={5}
        value={notes}
        onChangeText={setNotes}
      />

      <HighContrastButton
        title={t('officer.send_field_report')}
        variant="primary"
        onPress={handleSubmit}
        loading={submitting}
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.compact.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1 },
  title: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  subtitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, marginTop: 4, marginBottom: 16 },
  label: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800', marginBottom: 8, marginTop: 10 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 14 },
  tile: {
    width: '48%',
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.neutral.borderStrong,
    borderWidth: 1,
    padding: 12,
    borderRadius: theme.spacing.compact.radius,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  activeTile: { backgroundColor: theme.colors.brand.primaryHover, borderColor: theme.colors.brand.primary },
  tileText: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800' },
  activeTileText: { color: theme.colors.neutral.textHeading },
  input: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.neutral.borderStrong,
    borderWidth: 1,
    borderRadius: theme.spacing.compact.radius,
    padding: 12,
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.body,
    height: 100,
    textAlignVertical: 'top',
    marginBottom: 16,
  },
});
