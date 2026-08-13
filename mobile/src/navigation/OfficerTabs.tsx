import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { useTranslation } from 'react-i18next';
import { MyZoneScreen } from '../screens/officer/MyZoneScreen';
import { TasksScreen } from '../screens/officer/TasksScreen';
import { VerifyIncidentScreen } from '../screens/officer/VerifyIncidentScreen';
import { OfficerReportScreen } from '../screens/officer/OfficerReportScreen';
import { SettingsScreen } from '../screens/settings/SettingsScreen';

const Tab = createBottomTabNavigator();

export const OfficerTabs: React.FC = () => {
  const { t } = useTranslation();

  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: '#0f172a' },
        headerTitleStyle: { color: '#f8fafc', fontWeight: '800' },
        tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#0284c7', height: 60, paddingBottom: 8 },
        tabBarActiveTintColor: '#38bdf8',
        tabBarInactiveTintColor: '#64748b',
        tabBarLabelStyle: { fontWeight: '700', fontSize: 10 },
      }}
    >
      <Tab.Screen
        name="MyZone"
        component={MyZoneScreen}
        options={{
          title: t('officer.my_zone_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>👮</Text>,
        }}
      />
      <Tab.Screen
        name="Tasks"
        component={TasksScreen}
        options={{
          title: t('officer.tasks_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>📋</Text>,
        }}
      />
      <Tab.Screen
        name="Verify"
        component={VerifyIncidentScreen}
        options={{
          title: t('officer.triage_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>🔍</Text>,
        }}
      />
      <Tab.Screen
        name="OfficerReport"
        component={OfficerReportScreen}
        options={{
          title: t('officer.report_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>📡</Text>,
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: t('common.settings'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>⚙️</Text>,
        }}
      />
    </Tab.Navigator>
  );
};
