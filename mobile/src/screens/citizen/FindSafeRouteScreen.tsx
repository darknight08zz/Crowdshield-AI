import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, ScrollView } from 'react-native';
import { useTranslation } from 'react-i18next';
import { HighContrastButton } from '../../components/UI/HighContrastButton';
import { theme } from '../../config/theme';

export const FindSafeRouteScreen: React.FC = () => {
  const { t } = useTranslation();
  const [startPoint, setStartPoint] = useState('Main Stage Arena (Current GPS)');
  const [destination, setDestination] = useState('North Exit Promenade');
  const [calculating, setCalculating] = useState(false);
  const [route, setRoute] = useState<any>(null);

  const calculateSafeRoute = () => {
    setCalculating(true);
    setTimeout(() => {
      setRoute({
        distance: '450 meters',
        estimatedTime: '6 minutes',
        safetyScore: '96% SAFE',
        avoidedZones: ['Main Stage Bottleneck (Risk: 82%)', 'East Gate Turnstiles (Risk: 74%)'],
        steps: [
          '1. Exit Main Stage Arena via West Corridor 2 (Avoid East Gate choke-point).',
          '2. Proceed north along Food Courtyard Promenade.',
          '3. Arrive at North Exit Promenade (Gate 1 - Fully Open).',
        ],
      });
      setCalculating(false);
    }, 800);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>🧭 {t('citizen.find_safe_route_title').toUpperCase()}</Text>
      <Text style={styles.subtitle}>
        {t('citizen.find_safe_route_sub')}
      </Text>

      <View style={styles.card}>
        <Text style={styles.label}>START LOCATION</Text>
        <TextInput style={styles.input} value={startPoint} onChangeText={setStartPoint} placeholderTextColor={theme.colors.neutral.textMuted} />

        <Text style={styles.label}>{t('citizen.select_destination')}</Text>
        <TextInput style={styles.input} value={destination} onChangeText={setDestination} placeholderTextColor={theme.colors.neutral.textMuted} />

        <HighContrastButton
          title={calculating ? t('citizen.calculating_route') : t('citizen.calculate_route')}
          onPress={calculateSafeRoute}
          loading={calculating}
        />
      </View>

      {route && (
        <View style={styles.resultCard}>
          <View style={styles.resultHeader}>
            <Text style={styles.resultSafety}>✅ {route.safetyScore}</Text>
            <Text style={styles.resultTime}>⏱️ {route.estimatedTime} ({route.distance})</Text>
          </View>

          <Text style={styles.sectionHeader}>{t('citizen.avoided_bottlenecks')}</Text>
          {route.avoidedZones.map((z: string, idx: number) => (
            <Text key={idx} style={styles.avoidedText}>
              🚫 {z}
            </Text>
          ))}

          <Text style={[styles.sectionHeader, { marginTop: 14 }]}>{t('citizen.step_by_step_instructions')}</Text>
          {route.steps.map((step: string, idx: number) => (
            <View key={idx} style={styles.stepBox}>
              <Text style={styles.stepText}>{step}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.spacious.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1 },
  title: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  subtitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, marginTop: 4, marginBottom: 16 },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
  },
  label: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800', marginBottom: 6 },
  input: {
    backgroundColor: theme.colors.neutral.bgPage,
    borderColor: theme.colors.neutral.borderStrong,
    borderWidth: 1,
    borderRadius: theme.spacing.compact.radius,
    padding: 12,
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.body,
    marginBottom: 14,
    minHeight: 48,
  },
  resultCard: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1.5,
    borderColor: theme.colors.risk.LOW.border,
    marginTop: 20,
  },
  resultHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  resultSafety: { color: theme.colors.risk.LOW.hex, fontSize: theme.typography.sizes.cardTitle, fontWeight: '900' },
  resultTime: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '700', fontFamily: theme.typography.fontMono },
  sectionHeader: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, fontWeight: '800', marginBottom: 6 },
  avoidedText: { color: theme.colors.risk.CRITICAL.hex, fontSize: theme.typography.sizes.caption + 1, fontWeight: '600', marginBottom: 4 },
  stepBox: { backgroundColor: theme.colors.neutral.bgPage, padding: 12, borderRadius: 8, marginBottom: 8 },
  stepText: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, lineHeight: 20 },
});
