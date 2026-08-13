import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Switch } from 'react-native';
import { useTranslation } from 'react-i18next';
import { setAppLanguage } from '../../services/i18n';
import { useAuthStore } from '../../store/useAuthStore';
import { secureSession } from '../../services/secureSession';
import { API_BASE_URL } from '../../config/constants';
import { theme } from '../../config/theme';
import { ShieldCheck, Fingerprint, LogOut, Globe } from 'lucide-react-native';

export const SettingsScreen: React.FC<any> = () => {
  const { t, i18n } = useTranslation();
  const [currentLang, setCurrentLang] = useState<string>(i18n.language || 'en');
  const [biometricsEnabled, setBiometricsEnabled] = useState<boolean>(false);
  const user = useAuthStore((s) => s.user);
  const role = useAuthStore((s) => s.role);
  const signOut = useAuthStore((s) => s.signOut);

  useEffect(() => {
    setCurrentLang(i18n.language || 'en');
    secureSession.getBiometricsEnabled().then(setBiometricsEnabled);
  }, [i18n.language]);

  const handleSelectLanguage = async (lang: 'en' | 'hi') => {
    setCurrentLang(lang);
    await setAppLanguage(lang);
  };

  const toggleBiometrics = async (value: boolean) => {
    setBiometricsEnabled(value);
    await secureSession.setBiometricsEnabled(value);
  };

  const handleLogout = async () => {
    try {
      const token = await secureSession.getAccessToken();
      if (token) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }).catch(() => {});
      }
    } catch {
      // Ignore network failures on logout
    } finally {
      await signOut();
    }
  };

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      {/* Account Profile Card */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <ShieldCheck size={20} color={theme.colors.brand.primary} style={{ marginRight: 6 }} />
          <Text style={styles.sectionHeader}>{t('settings.account_profile')}</Text>
        </View>

        <Text style={styles.infoLabel}>{t('settings.logged_in_as')}</Text>
        <Text style={styles.infoValue}>{user?.name || 'CrowdShield User'} ({user?.email || 'user@crowdshield.io'})</Text>

        <Text style={styles.infoLabel}>{t('settings.role')}</Text>
        <Text style={styles.roleBadge}>{(role || 'CITIZEN').toUpperCase()}</Text>

        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout} activeOpacity={0.85}>
          <LogOut size={16} color={theme.colors.neutral.textHeading} style={{ marginRight: 6 }} />
          <Text style={styles.logoutBtnText}>{t('common.logout')}</Text>
        </TouchableOpacity>
      </View>

      {/* Biometric Security Card (For Field Officers) */}
      {role === 'field_officer' && (
        <View style={styles.card}>
          <View style={styles.cardHeaderRow}>
            <Fingerprint size={20} color={theme.colors.brand.primary} style={{ marginRight: 6 }} />
            <Text style={styles.sectionHeader}>OFFICER TERMINAL SECURITY</Text>
          </View>
          <Text style={styles.sectionDesc}>
            Require Face ID or Touch ID authentication when unlocking the officer dispatch app.
          </Text>

          <View style={styles.switchRow}>
            <Text style={styles.switchLabel}>Biometric Unlock Enabled</Text>
            <Switch
              value={biometricsEnabled}
              onValueChange={toggleBiometrics}
              trackColor={{ false: theme.colors.neutral.borderStrong, true: theme.colors.brand.primaryHover }}
              thumbColor={biometricsEnabled ? theme.colors.brand.primary : theme.colors.neutral.textMuted}
            />
          </View>
        </View>
      )}

      {/* Language Selection Card */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <Globe size={20} color={theme.colors.brand.primary} style={{ marginRight: 6 }} />
          <Text style={styles.sectionHeader}>{t('settings.language_selection')}</Text>
        </View>
        <Text style={styles.sectionDesc}>{t('settings.select_language_desc')}</Text>

        <View style={styles.langOptionContainer}>
          <TouchableOpacity
            style={[styles.langOption, currentLang === 'en' && styles.selectedOption]}
            onPress={() => handleSelectLanguage('en')}
            activeOpacity={0.8}
          >
            <View style={styles.radioRow}>
              <View style={[styles.radioOuter, currentLang === 'en' && styles.radioOuterSelected]}>
                {currentLang === 'en' && <View style={styles.radioInner} />}
              </View>
              <Text style={[styles.langText, currentLang === 'en' && styles.selectedLangText]}>
                {t('settings.english')}
              </Text>
            </View>
            <Text style={styles.langSub}>Default (EN)</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.langOption, currentLang === 'hi' && styles.selectedOption]}
            onPress={() => handleSelectLanguage('hi')}
            activeOpacity={0.8}
          >
            <View style={styles.radioRow}>
              <View style={[styles.radioOuter, currentLang === 'hi' && styles.radioOuterSelected]}>
                {currentLang === 'hi' && <View style={styles.radioInner} />}
              </View>
              <Text style={[styles.langText, currentLang === 'hi' && styles.selectedLangText]}>
                {t('settings.hindi')}
              </Text>
            </View>
            <Text style={styles.langSub}>हिंदी (HI)</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: theme.colors.neutral.bgPage },
  container: { padding: theme.spacing.spacious.padding },
  card: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.spacious.radius,
    padding: theme.spacing.spacious.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    marginBottom: 16,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  sectionHeader: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.caption + 1, fontWeight: '800', letterSpacing: 1 },
  sectionDesc: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, marginBottom: 14, lineHeight: 16 },
  infoLabel: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, fontWeight: '700', marginTop: 8 },
  infoValue: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '600', marginTop: 2 },
  roleBadge: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.brand.primary,
    color: theme.colors.neutral.textHeading,
    fontSize: theme.typography.sizes.caption,
    fontWeight: '800',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    marginTop: 4,
  },
  logoutBtn: {
    backgroundColor: theme.colors.risk.CRITICAL.border,
    borderRadius: theme.spacing.compact.radius,
    minHeight: 48,
    paddingVertical: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 16,
  },
  logoutBtnText: { color: theme.colors.neutral.textHeading, fontWeight: '800', fontSize: theme.typography.sizes.body },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.neutral.bgPage,
    borderRadius: theme.spacing.compact.radius,
    padding: 14,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    minHeight: 52,
  },
  switchLabel: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '600' },
  langOptionContainer: { gap: 10 },
  langOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: theme.colors.neutral.bgPage,
    borderRadius: theme.spacing.compact.radius,
    padding: 14,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    minHeight: 52,
  },
  selectedOption: { borderColor: theme.colors.brand.primary, backgroundColor: theme.colors.brand.glow },
  radioRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  radioOuter: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: theme.colors.neutral.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioOuterSelected: { borderColor: theme.colors.brand.primary },
  radioInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: theme.colors.brand.primary },
  langText: { color: theme.colors.neutral.textBody, fontSize: theme.typography.sizes.body, fontWeight: '700' },
  selectedLangText: { color: theme.colors.neutral.textHeading },
  langSub: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption },
});
