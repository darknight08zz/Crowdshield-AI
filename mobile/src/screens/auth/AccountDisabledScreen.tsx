import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ShieldAlert, LogOut, Mail, HelpCircle } from 'lucide-react-native';
import { useAuthStore } from '../../store/useAuthStore';

export const AccountDisabledScreen: React.FC = () => {
  const signOut = useAuthStore((s) => s.signOut);
  const user = useAuthStore((s) => s.user);

  const handleContactSupport = () => {
    Linking.openURL('mailto:admin@crowdshield.gov?subject=Account%20Access%20Inquiry');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.badge}>
          <ShieldAlert size={48} color="#EF4444" />
        </View>

        <Text style={styles.title}>Account Access Disabled</Text>
        <Text style={styles.subtitle}>
          Your account ({user?.email || user?.name || 'Staff User'}) has been temporarily suspended or disabled by a System Administrator.
        </Text>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <HelpCircle size={20} color="#F59E0B" style={{ marginRight: 8 }} />
            <Text style={styles.cardHeaderTitle}>What should I do?</Text>
          </View>
          <Text style={styles.cardText}>
            If you believe this is in error or require immediate operational access restoration, please contact your Command Room Administrator or Event Manager.
          </Text>

          <TouchableOpacity style={styles.contactBtn} onPress={handleContactSupport} activeOpacity={0.85}>
            <Mail size={18} color="#FFFFFF" style={{ marginRight: 8 }} />
            <Text style={styles.contactBtnText}>Contact Administrator</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.logoutBtn} onPress={signOut} activeOpacity={0.85}>
          <LogOut size={18} color="#94A3B8" style={{ marginRight: 8 }} />
          <Text style={styles.logoutBtnText}>Return to Sign In</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
    justifyContent: 'center',
    padding: 20,
  },
  content: {
    alignItems: 'center',
  },
  badge: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.3)',
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    color: '#F8FAFC',
    marginBottom: 10,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
    paddingHorizontal: 12,
  },
  card: {
    width: '100%',
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 24,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardHeaderTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#F8FAFC',
  },
  cardText: {
    fontSize: 13,
    color: '#CBD5E1',
    lineHeight: 20,
    marginBottom: 16,
  },
  contactBtn: {
    backgroundColor: '#334155',
    borderRadius: 12,
    height: 46,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  contactBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  logoutBtnText: {
    color: '#94A3B8',
    fontSize: 15,
    fontWeight: '600',
  },
});
