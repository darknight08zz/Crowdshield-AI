import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import { RiskBadge } from '../../components/UI/RiskBadge';
import { HighContrastButton } from '../../components/UI/HighContrastButton';
import { theme } from '../../config/theme';

export const MyZoneScreen: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadZone = async () => {
    const res = await api.fetchZones(i18n.language);
    setData(res);
  };

  useEffect(() => {
    loadZone();
  }, [i18n.language]);

  const assignedZone = data?.zones?.[0] || {
    id: 'z-1',
    name: t('officer.zone_name'),
    capacity: 10000,
    current_density: 0.88,
    risk_score: 82.5,
    status: 'CRITICAL SURGE',
  };

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={loadZone} tintColor={theme.colors.brand.primary} />}
    >
      <View style={styles.headerRow}>
        <Text style={styles.badgeLabel}>👮 {t('officer.my_assigned_zone').toUpperCase()}</Text>
        <RiskBadge score={assignedZone.risk_score} size="large" />
      </View>

      <Text style={styles.zoneTitle}>{assignedZone.name}</Text>
      <Text style={styles.subText}>{t('officer.my_assigned_zone')}</Text>

      {/* Metrics Card */}
      <View style={styles.metricCard}>
        <View style={styles.row}>
          <Text style={styles.metricLabel}>{t('citizen.occupancy_density').toUpperCase()}</Text>
          <Text style={styles.metricVal}>{(assignedZone.current_density * 100).toFixed(0)}%</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.metricLabel}>{t('citizen.max_capacity').toUpperCase()}</Text>
          <Text style={styles.metricVal}>{assignedZone.capacity} / 10,000</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.metricLabel}>{t('officer.current_risk_score').toUpperCase()}</Text>
          <Text style={[styles.metricVal, { color: theme.colors.risk.CRITICAL.hex }]}>{assignedZone.risk_score.toFixed(1)} / 100</Text>
        </View>
      </View>

      {/* Control Room AI Directives */}
      <Text style={styles.sectionHeader}>{t('officer.officer_quick_actions')}</Text>
      <View style={styles.directiveBox}>
        <Text style={styles.directiveTitle}>⚡ DIRECTIVE: UNLOCK GATE 1 & RE-ROUTE FLOW</Text>
        <Text style={styles.directiveDesc}>
          AI Risk Engine detected counter-flow pressure. Manually open emergency gate 1 to bleed off 1,200 pedestrians towards North Promenade.
        </Text>
        <HighContrastButton title="CONFIRM DIRECTIVE EXECUTED" variant="primary" onPress={() => {}} />
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.compact.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  badgeLabel: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.caption + 1, fontWeight: '900', letterSpacing: 1 },
  zoneTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.pageTitle, fontWeight: '900', marginTop: 10 },
  subText: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.body, marginBottom: 16 },
  metricCard: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.compact.radius,
    padding: theme.spacing.compact.padding,
    borderWidth: 1.5,
    borderColor: theme.colors.brand.primary,
    marginBottom: 20,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginVertical: 6 },
  metricLabel: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, fontWeight: '700' },
  metricVal: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '800', fontFamily: theme.typography.fontMono },
  sectionHeader: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.cardTitle, fontWeight: '800', marginBottom: 10 },
  directiveBox: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.compact.radius,
    padding: theme.spacing.compact.padding,
    borderWidth: 1.5,
    borderColor: theme.colors.risk.MODERATE.hex,
  },
  directiveTitle: { color: theme.colors.risk.MODERATE.hex, fontSize: theme.typography.sizes.cardTitle, fontWeight: '900', marginBottom: 6 },
  directiveDesc: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, lineHeight: 20, marginBottom: 12 },
});
