import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import * as Location from 'expo-location';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import { RiskBadge } from '../../components/UI/RiskBadge';
import { OfflineBanner } from '../../components/UI/OfflineBanner';
import { theme } from '../../config/theme';
import { useAuthStore } from '../../store/useAuthStore';

export const HomeScreen: React.FC<any> = ({ navigation }) => {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [userZone, setUserZone] = useState<any>(null);
  const user = useAuthStore((s) => s.user);
  const userName = user?.name || 'User';

  const loadData = async () => {
    const res = await api.fetchZones(i18n.language);
    setData(res);
    if (res?.zones && res.zones.length > 0) {
      setUserZone(res.zones[0]);
    }
  };

  useEffect(() => {
    loadData();
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const loc = await Location.getCurrentPositionAsync({});
        console.log('[GPS Location Granted]', loc.coords.latitude, loc.coords.longitude);
      }
    })();
  }, [i18n.language]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const highestRisk = data?.zones?.reduce((max: number, z: any) => Math.max(max, z.risk_score), 0) ?? null;

  return (
    <View style={styles.flex}>
      <OfflineBanner />
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.brand.primary} />}
      >
        <View style={styles.welcomeCard}>
          <Text style={styles.greeting}>{t('common.welcome')}, {userName}</Text>
          {data?.event?.name ? (
            <Text style={styles.eventTitle}>{data.event.name}</Text>
          ) : (
            <Text style={styles.eventTitleMuted}>No active event</Text>
          )}
        </View>

        {/* Overall Venue Safety Banner */}
        <View style={styles.statusCard}>
          <Text style={styles.sectionLabel}>{t('citizen.overall_safety_status')}</Text>
          {highestRisk !== null ? (
            <>
              <RiskBadge score={highestRisk} size="large" />
              <Text style={styles.statusDesc}>
                {highestRisk > 75
                  ? t('citizen.high_density_alert')
                  : t('citizen.normal_flow_status')}
              </Text>
            </>
          ) : (
            <Text style={styles.statusDesc}>No live telemetry data available yet.</Text>
          )}
        </View>

        {/* Current Zone Risk */}
        {userZone && (
          <View style={styles.zoneCard}>
            <View style={styles.rowBetween}>
              <Text style={styles.zoneName}>{t('citizen.current_zone', { zoneName: userZone.name })}</Text>
              <RiskBadge score={userZone.risk_score} size="small" />
            </View>
            <Text style={styles.metricText}>
              {t('citizen.occupancy_density')} <Text style={styles.bold}>{(userZone.current_density * 100).toFixed(0)}%</Text>
            </Text>
            <Text style={styles.metricText}>
              {t('citizen.max_capacity')} <Text style={styles.bold}>{userZone.capacity} {t('common.persons')}</Text>
            </Text>
          </View>
        )}

        {/* Quick Shortcut Tiles */}
        <Text style={styles.sectionHeader}>{t('citizen.safety_action_center')}</Text>
        <View style={styles.grid}>
          <TouchableOpacity style={styles.gridBtn} onPress={() => navigation.navigate('LiveMap')} activeOpacity={0.8}>
            <Text style={styles.gridIcon}>🗺️</Text>
            <Text style={styles.gridTitle}>{t('citizen.live_risk_map')}</Text>
            <Text style={styles.gridSub}>{t('citizen.live_risk_map_sub')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.gridBtn} onPress={() => navigation.navigate('SafeRoute')} activeOpacity={0.8}>
            <Text style={styles.gridIcon}>🧭</Text>
            <Text style={styles.gridTitle}>{t('citizen.find_safe_route')}</Text>
            <Text style={styles.gridSub}>{t('citizen.find_safe_route_sub')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.gridBtn} onPress={() => navigation.navigate('Report')} activeOpacity={0.8}>
            <Text style={styles.gridIcon}>📢</Text>
            <Text style={styles.gridTitle}>{t('citizen.report_incident')}</Text>
            <Text style={styles.gridSub}>{t('citizen.report_incident_sub')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.gridBtn} onPress={() => navigation.navigate('Emergency')} activeOpacity={0.8}>
            <Text style={styles.gridIcon}>🆘</Text>
            <Text style={styles.gridTitle}>{t('citizen.emergency_help')}</Text>
            <Text style={styles.gridSub}>{t('citizen.emergency_help_sub')}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: theme.colors.neutral.bgPage },
  container: { padding: theme.spacing.spacious.padding, paddingBottom: 40 },
  welcomeCard: { marginBottom: 16 },
  greeting: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.body, fontWeight: '600' },
  eventTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.display - 8, fontWeight: '900', marginTop: 2 },
  eventTitleMuted: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.cardTitle, fontWeight: '600', marginTop: 4 },
  statusCard: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    marginBottom: 16,
  },
  sectionLabel: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, fontWeight: '800', letterSpacing: 1, marginBottom: 8 },
  statusDesc: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.body, marginTop: 10, lineHeight: 20 },
  zoneCard: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.brand.primary,
    marginBottom: 20,
  },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  zoneName: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.cardTitle, fontWeight: '800' },
  metricText: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.body, marginTop: 4 },
  bold: { color: theme.colors.neutral.textHeading, fontWeight: '700', fontFamily: theme.typography.fontMono },
  sectionHeader: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '800', marginBottom: 12 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  gridBtn: {
    width: '48%',
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    minHeight: 110,
  },
  gridIcon: { fontSize: 26, marginBottom: 8 },
  gridTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.cardTitle, fontWeight: '800' },
  gridSub: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, marginTop: 4 },
});
