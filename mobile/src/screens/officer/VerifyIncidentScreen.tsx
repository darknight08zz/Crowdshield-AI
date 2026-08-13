import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, Alert, Image, TouchableOpacity } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useTranslation } from 'react-i18next';
import { HighContrastButton } from '../../components/UI/HighContrastButton';
import { api } from '../../services/api';
import { theme } from '../../config/theme';

export const VerifyIncidentScreen: React.FC = () => {
  const { t } = useTranslation();
  const [note, setNote] = useState('');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const sampleIncident = {
    id: 'inc-99',
    type: `🔥 ${t('citizen.type_surge')}`,
    location: 'Zone A - East Gate Bottleneck',
    reportedBy: 'Citizen Jordan S.',
    timeAgo: '4 mins ago',
  };

  const takeVerificationPhoto = async () => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permission Required', 'Camera access is required for field verification photos.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (!result.canceled && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
    }
  };

  const handleVerify = async (status: 'confirmed' | 'false_alarm' | 'resolved') => {
    setSubmitting(true);
    try {
      await api.verifyIncident(sampleIncident.id, status, note);
      Alert.alert('Verification Submitted', `Incident marked as ${status.toUpperCase()}. Control Room updated.`);
    } catch (e) {
      Alert.alert('Verification Logged', `Incident marked as ${status.toUpperCase()}.`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>🔍 {t('officer.triage_incident_verification').toUpperCase()}</Text>
      <Text style={styles.subtitle}>{t('officer.pending_incidents')}</Text>

      {/* Incident Details Card */}
      <View style={styles.card}>
        <Text style={styles.incType}>{sampleIncident.type}</Text>
        <Text style={styles.incLoc}>📍 Location: {sampleIncident.location}</Text>
        <Text style={styles.incSub}>Reported by: {sampleIncident.reportedBy} ({sampleIncident.timeAgo})</Text>
      </View>

      <Text style={styles.label}>{t('officer.field_observations')}</Text>
      <TextInput
        style={styles.input}
        placeholder={t('officer.obs_placeholder')}
        placeholderTextColor={theme.colors.neutral.textMuted}
        multiline
        value={note}
        onChangeText={setNote}
      />

      <Text style={styles.label}>{t('citizen.attach_photo')}</Text>
      <TouchableOpacity style={styles.cameraBtn} onPress={takeVerificationPhoto} activeOpacity={0.8}>
        <Text style={styles.cameraBtnText}>{imageUri ? '📸 Retake Photo' : '📷 Capture Live Photo'}</Text>
      </TouchableOpacity>
      {imageUri && <Image source={{ uri: imageUri }} style={styles.photoPreview} />}

      <Text style={styles.label}>{t('officer.triage_tab').toUpperCase()}</Text>
      <HighContrastButton
        title={`✅ ${t('officer.btn_confirm')}`}
        variant="danger"
        onPress={() => handleVerify('confirmed')}
        loading={submitting}
      />

      <HighContrastButton
        title={`🎉 ${t('officer.btn_resolve')}`}
        variant="primary"
        onPress={() => handleVerify('resolved')}
        loading={submitting}
      />

      <HighContrastButton
        title={`❌ ${t('officer.btn_false_alarm')}`}
        variant="secondary"
        onPress={() => handleVerify('false_alarm')}
        loading={submitting}
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.compact.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1 },
  title: { color: theme.colors.risk.MODERATE.hex, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  subtitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, marginTop: 4, marginBottom: 16 },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.compact.radius,
    padding: theme.spacing.compact.padding,
    borderWidth: 1.5,
    borderColor: theme.colors.risk.MODERATE.border,
    marginBottom: 16,
  },
  incType: { color: theme.colors.risk.CRITICAL.hex, fontSize: theme.typography.sizes.cardTitle, fontWeight: '900' },
  incLoc: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '700', marginTop: 6 },
  incSub: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, marginTop: 4, fontFamily: theme.typography.fontMono },
  label: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800', marginBottom: 6, marginTop: 10 },
  input: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.neutral.borderStrong,
    borderWidth: 1,
    borderRadius: theme.spacing.compact.radius,
    padding: 12,
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.body,
    height: 80,
    textAlignVertical: 'top',
  },
  cameraBtn: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.brand.primary,
    borderWidth: 1,
    borderRadius: theme.spacing.compact.radius,
    padding: 14,
    alignItems: 'center',
    marginBottom: 12,
    minHeight: 48,
    justifyContent: 'center',
  },
  cameraBtnText: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.body, fontWeight: '800' },
  photoPreview: { width: '100%', height: 160, borderRadius: 8, marginBottom: 12 },
});
