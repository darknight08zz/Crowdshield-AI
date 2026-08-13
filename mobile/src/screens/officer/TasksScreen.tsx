import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl } from 'react-native';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import { theme } from '../../config/theme';

export const TasksScreen: React.FC = () => {
  const { t } = useTranslation();
  const [tasks, setTasks] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadTasks = async () => {
    const list = await api.fetchOfficerTasks();
    setTasks(list);
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const toggleTaskStatus = async (task: any) => {
    const nextStatus = task.status === 'completed' ? 'assigned' : task.status === 'in_progress' ? 'completed' : 'in_progress';
    try {
      await api.updateTaskStatus(task.id, nextStatus);
    } catch (e) {
      // Local state update fallback
    }
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, status: nextStatus } : t))
    );
  };

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={loadTasks} tintColor={theme.colors.brand.primary} />}
    >
      <Text style={styles.title}>📋 {t('officer.assigned_field_tasks').toUpperCase()}</Text>
      <Text style={styles.subtitle}>Tap task to update status.</Text>

      {tasks.map((item) => {
        const isCompleted = item.status === 'completed';
        const isInProgress = item.status === 'in_progress';
        const statusLabel = isCompleted
          ? t('officer.status_completed')
          : isInProgress
          ? t('officer.status_in_progress')
          : t('officer.status_assigned');

        return (
          <TouchableOpacity
            key={item.id}
            activeOpacity={0.8}
            style={[styles.taskCard, isCompleted && styles.completedCard]}
            onPress={() => toggleTaskStatus(item)}
          >
            <View style={styles.checkboxContainer}>
              <View style={[styles.checkbox, isCompleted && styles.checkedBox, isInProgress && styles.progressBox]}>
                <Text style={styles.checkText}>{isCompleted ? '✓' : isInProgress ? '⏳' : ''}</Text>
              </View>
            </View>

            <View style={styles.content}>
              <Text style={[styles.taskText, isCompleted && styles.completedText]}>
                {item.task_description}
              </Text>
              <Text style={styles.statusBadge}>
                {t('common.status').toUpperCase()}: <Text style={{ color: isCompleted ? theme.colors.risk.LOW.hex : isInProgress ? theme.colors.risk.MODERATE.hex : theme.colors.brand.primary }}>
                  {statusLabel}
                </Text>
              </Text>
            </View>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: theme.spacing.compact.padding, backgroundColor: theme.colors.neutral.bgPage, flexGrow: 1 },
  title: { color: theme.colors.brand.primary, fontSize: theme.typography.sizes.sectionHeader, fontWeight: '900', letterSpacing: 1 },
  subtitle: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption + 1, marginTop: 4, marginBottom: 16 },
  taskCard: {
    backgroundColor: theme.colors.neutral.bgSurface,
    borderRadius: theme.spacing.compact.radius,
    padding: theme.spacing.compact.padding,
    borderWidth: 1,
    borderColor: theme.colors.neutral.borderSubtle,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    minHeight: 56,
  },
  completedCard: { opacity: 0.6, backgroundColor: theme.colors.neutral.bgPage },
  checkboxContainer: { marginRight: 12 },
  checkbox: {
    width: 28,
    height: 28,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: theme.colors.neutral.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkedBox: { backgroundColor: theme.colors.risk.LOW.border, borderColor: theme.colors.risk.LOW.border },
  progressBox: { backgroundColor: theme.colors.risk.MODERATE.border, borderColor: theme.colors.risk.MODERATE.border },
  checkText: { color: theme.colors.neutral.textHeading, fontWeight: '900', fontSize: 14 },
  content: { flex: 1 },
  taskText: { color: theme.colors.neutral.textHeading, fontSize: theme.typography.sizes.body, fontWeight: '700' },
  completedText: { textDecorationLine: 'line-through', color: theme.colors.neutral.textMuted },
  statusBadge: { color: theme.colors.neutral.textMuted, fontSize: theme.typography.sizes.caption, fontWeight: '800', marginTop: 4 },
});
