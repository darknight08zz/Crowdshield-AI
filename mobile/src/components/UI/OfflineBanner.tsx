import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useOfflineStore } from '../../store/useOfflineStore';
import { flushOfflineQueue } from '../../services/offlineQueue';

export const OfflineBanner: React.FC = () => {
  const queuedIncidents = useOfflineStore((state) => state.queuedIncidents);

  if (queuedIncidents.length === 0) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.text}>
        ⚠️ {queuedIncidents.length} offline incident report(s) pending sync.
      </Text>
      <TouchableOpacity style={styles.button} onPress={flushOfflineQueue}>
        <Text style={styles.btnText}>SYNC NOW</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#b45309',
    paddingHorizontal: 16,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  text: {
    color: '#fef3c7',
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
  },
  button: {
    backgroundColor: '#78350f',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
  },
  btnText: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '800',
  },
});
