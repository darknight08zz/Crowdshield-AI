import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, ScrollView, Image, Alert, TouchableOpacity } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { useTranslation } from 'react-i18next';
import { HighContrastButton } from '../../components/UI/HighContrastButton';
import { api } from '../../services/api';
import { useOfflineStore } from '../../store/useOfflineStore';
import { theme } from '../../config/theme';

export const ReportIncidentScreen: React.FC<any> = ({ navigation }) => {
  const { t } = useTranslation();
  const [type, setType] = useState<'surge' | 'medical' | 'blocked_path' | 'other'>('surge');
  const [description, setDescription] = useState('');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const enqueueIncident = useOfflineStore((s) => s.enqueueIncident);

  const pickImage = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permission Required', 'Camera roll access is needed to attach proof photos.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });
    if (!result.canceled && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
    }
  };

  const handleReport = async () => {
    if (!description.trim()) {
      Alert.alert(t('common.error'), t('citizen.desc_placeholder'));
      return;
    }

    setSubmitting(true);
    let lat = 12.9716;
    let lng = 77.5946;

    try {
      const loc = await Location.getCurrentPositionAsync({});
      lat = loc.coords.latitude;
      lng = loc.coords.longitude;
    } catch (e) {
      console.warn('Using default venue GPS coordinates.');
    }

    const reportData = {
      type,
      description,
      lat,
      lng,
      image_uri: imageUri || undefined,
    };

    try {
      await api.submitIncident(reportData);
      Alert.alert(t('citizen.report_success_title'), t('citizen.report_success_msg'), [
        { text: 'OK', onPress: () => navigation.navigate('Home') },
      ]);
    } catch (err) {
      await enqueueIncident(reportData);
      Alert.alert(
        'Network Saved to Queue',
        'Weak connectivity detected. Your report has been saved to your local offline queue and will auto-submit when connectivity restores!',
        [{ text: 'OK', onPress: () => navigation.navigate('Home') }]
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>📢 {t('citizen.report_incident_title').toUpperCase()}</Text>
      <Text style={styles.subtitle}>{t('citizen.report_incident_sub')}</Text>

      <Text style={styles.label}>{t('citizen.incident_type')}</Text>
      <View style={styles.typeGrid}>
        {[
          { key: 'surge', label: `🔥 ${t('citizen.type_surge')}` },
          { key: 'medical', label: `🚑 ${t('citizen.type_medical')}` },
          { key: 'blocked_path', label: `🚧 ${t('citizen.type_bottleneck')}` },
          { key: 'other', label: `⚠️ ${t('citizen.type_other')}` },
        ].map((item) => (
          <TouchableOpacity
            key={item.key}
            style={[styles.typeBtn, type === item.key && styles.activeTypeBtn]}
            onPress={() => setType(item.key as any)}
            activeOpacity={0.8}
          >
            <Text style={[styles.typeText, type === item.key && styles.activeTypeText]}>
              {item.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>{t('citizen.description')}</Text>
      <TextInput
        style={[styles.input, styles.textArea]}
        placeholder={t('citizen.desc_placeholder')}
        placeholderTextColor={theme.colors.neutral.textMuted}
        multiline
        numberOfLines={4}
        value={description}
        onChangeText={setDescription}
      />

      <Text style={styles.label}>{t('citizen.attach_photo')}</Text>
      <TouchableOpacity style={styles.photoPicker} onPress={pickImage} activeOpacity={0.8}>
        <Text style={styles.photoPickerText}>{imageUri ? t('citizen.photo_attached') : t('citizen.attach_photo')}</Text>
      </TouchableOpacity>
      {imageUri && <Image source={{ uri: imageUri }} style={styles.previewImage} />}

      <HighContrastButton
        title={submitting ? t('citizen.submitting_report') : t('citizen.submit_report')}
        variant="danger"
        onPress={handleReport}
        loading={submitting}
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.spacious.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1 },
  title: { color: theme.colors.risk.CRITICAL.hex, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  subtitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, marginTop: 4, marginBottom: 16 },
  label: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800', marginBottom: 8, marginTop: 12 },
  typeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  typeBtn: {
    width: '48%',
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.neutral.borderSubtle,
    borderWidth: 1,
    paddingVertical: 14,
    paddingHorizontal: 8,
    borderRadius: theme.spacing.compact.radius,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  activeTypeBtn: { backgroundColor: theme.colors.risk.CRITICAL.bg, borderColor: theme.colors.risk.CRITICAL.hex },
  typeText: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800' },
  activeTypeText: { color: theme.colors.neutral.textHeading },
  input: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.neutral.borderStrong,
    borderWidth: 1,
    borderRadius: theme.spacing.compact.radius,
    padding: 12,
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.body,
  },
  textArea: { height: 100, textAlignVertical: 'top' },
  photoPicker: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderColor: theme.colors.brand.primary,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderRadius: theme.spacing.compact.radius,
    padding: 14,
    alignItems: 'center',
    marginBottom: 12,
    minHeight: 48,
    justifyContent: 'center',
  },
  photoPickerText: { color: theme.colors.brand.primary, fontWeight: '800', fontSize: theme.typography.sizes.body },
  previewImage: { width: '100%', height: 160, borderRadius: 8, marginBottom: 16 },
});
