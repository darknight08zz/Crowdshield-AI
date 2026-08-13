import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import { RiskBadge } from '../../components/UI/RiskBadge';
import { supabase } from '../../services/supabase';
import { theme } from '../../config/theme';

export const LiveMapScreen: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [zones, setZones] = useState<any[]>([]);
  const [gates, setGates] = useState<any[]>([]);
  const [selectedZone, setSelectedZone] = useState<any>(null);

  const loadMapData = async () => {
    const data = await api.fetchZones(i18n.language);
    if (data?.zones) setZones(data.zones);
    if (data?.gates) setGates(data.gates);
  };

  useEffect(() => {
    loadMapData();

    const channel = supabase
      .channel('citizen-map-realtime')
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'zones' },
        (payload) => {
          console.log('[Supabase Realtime Pushed Zone Update]', payload.new);
          setZones((prev) =>
            prev.map((z) => (z.id === payload.new.id ? { ...z, ...payload.new } : z))
          );
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [i18n.language]);

  // Mini calibration status tag (no hardcoded scores)
  const renderCalibrationTag = (zone: any) => {
    const isCalibrated = zone.calibration_method === 'homography';
    if (!isCalibrated) {
      return (
        <Text style={{ color: '#fbbf24', fontSize: 10, fontWeight: '700', marginTop: 4 }}>
          ⚠️ Uncalibrated
        </Text>
      );
    }
    return (
      <Text style={{ color: '#10b981', fontSize: 10, fontWeight: '700', marginTop: 4 }}>
        ✓ Calibrated
      </Text>
    );
  };

  return (
    <View style={styles.container}>
      {/* Map Interactive Grid Canvas Overlay */}
      <View style={styles.mapCanvas}>
        <Text style={styles.canvasHeader}>🗺️ {t('citizen.live_risk_map').toUpperCase()}</Text>
        <Text style={styles.canvasSub}>Supabase Realtime Sub-Zone Continuous Stream</Text>

        {zones.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateIcon}>🗺️</Text>
            <Text style={styles.emptyStateTitle}>No Zone Data</Text>
            <Text style={styles.emptyStateSub}>Live zone telemetry will appear here once event data is ingested into the system.</Text>
          </View>
        ) : (
          <View style={styles.zonesGrid}>
            {zones.map((zone) => {
              const risk = zone.risk_score || 0;
              const riskToken = risk > 75
                ? theme.colors.risk.CRITICAL
                : risk > 50
                ? theme.colors.risk.HIGH
                : risk > 25
                ? theme.colors.risk.MODERATE
                : theme.colors.risk.LOW;

              return (
                <TouchableOpacity
                  key={zone.id}
                  style={[
                    styles.zoneTile,
                    { backgroundColor: riskToken.bg, borderColor: riskToken.border },
                    selectedZone?.id === zone.id && styles.selectedTile,
                  ]}
                  onPress={() => setSelectedZone(zone)}
                  activeOpacity={0.8}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.tileTitle}>{zone.name}</Text>
                    <Text style={styles.tileRisk}>{risk.toFixed(0)}% Risk</Text>
                    {renderCalibrationTag(zone)}
                  </View>
                  <Text style={styles.tileDensity}>
                    {(zone.current_density * 100).toFixed(0)}% Occupancy
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {/* Choke Point Gates — only render when data exists */}
        {gates.length > 0 && (
          <View style={styles.gatesRow}>
            <Text style={styles.gatesTitle}>{t('officer.gate_statuses')}</Text>
            {gates.map((gate) => (
              <View key={gate.id} style={styles.gateBadge}>
                <Text style={styles.gateText}>
                  🚪 {gate.name}: <Text style={{ color: gate.status === 'open' ? theme.colors.risk.LOW.hex : theme.colors.risk.CRITICAL.hex }}>{gate.status.toUpperCase()}</Text>
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Selected Zone Detail Drawer */}
      {selectedZone && (
        <View style={styles.drawer}>
          <View style={styles.drawerHeader}>
            <Text style={styles.drawerTitle}>{selectedZone.name}</Text>
            <RiskBadge score={selectedZone.risk_score} size="medium" />
          </View>

          <Text style={styles.drawerDetail}>
            {t('citizen.max_capacity')} {selectedZone.capacity} {t('common.persons')} | {t('citizen.occupancy_density')} {(selectedZone.current_density * 100).toFixed(0)}%
          </Text>
          <Text style={styles.drawerRecommendation}>
            {selectedZone.risk_score > 70
              ? t('citizen.high_density_alert')
              : t('citizen.normal_flow_status')}
          </Text>
        </View>
      )}
    </View>
  );
};


const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.neutral.bgPage },
  mapCanvas: { flex: 1, padding: theme.spacing.spacious.padding, backgroundColor: theme.colors.neutral.bgSurface },
  canvasHeader: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  canvasSub: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, marginBottom: 16 },
  zonesGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, flex: 1 },
  emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 60 },
  emptyStateIcon: { fontSize: 48, marginBottom: 16 },
  emptyStateTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '800', marginBottom: 8 },
  emptyStateSub: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.body, textAlign: 'center', lineHeight: 22, paddingHorizontal: 24 },
  zoneTile: {
    width: '48%',
    height: 120,
    borderRadius: theme.spacing.spacious.radius,
    borderWidth: 1.5,
    padding: theme.spacing.compact.padding,
    justifyContent: 'space-between',
  },
  selectedTile: {
    borderWidth: 3,
    borderColor: theme.colors.neutral.textHeading,
  },
  tileTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '800' },
  tileRisk: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', fontFamily: theme.typography.fontMono },
  miniGridContainer: { marginTop: 4, width: 44, height: 44, borderRadius: 4, overflow: 'hidden' },
  miniGridRow: { flex: 1, flexDirection: 'row' },
  miniGridCell: { flex: 1, margin: 0.5, borderRadius: 1 },
  tileDensity: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.caption, fontWeight: '600', fontFamily: theme.typography.fontMono },

  gatesRow: { marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: theme.colors.neutral.borderSubtle },
  gatesTitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, fontWeight: '800', marginBottom: 6 },
  gateBadge: { backgroundColor: theme.colors.neutral.bgPage, padding: 8, borderRadius: 6, marginBottom: 6, minHeight: 44, justifyContent: 'center' },
  gateText: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '600' },
  drawer: {
    backgroundColor: theme.colors.neutral.bgPage,
    padding: theme.spacing.spacious.padding,
    borderTopLeftRadius: theme.spacing.spacious.radius,
    borderTopRightRadius: theme.spacing.spacious.radius,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
  },
  drawerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  drawerTitle: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '800' },
  drawerDetail: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.body, marginTop: 6, fontFamily: theme.typography.fontMono },
  drawerRecommendation: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.body, marginTop: 8, lineHeight: 20, fontWeight: '600' },
});
