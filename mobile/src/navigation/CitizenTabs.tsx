import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { useTranslation } from 'react-i18next';
import { HomeScreen } from '../screens/citizen/HomeScreen';
import { LiveMapScreen } from '../screens/citizen/LiveMapScreen';
import { FindSafeRouteScreen } from '../screens/citizen/FindSafeRouteScreen';
import { ReportIncidentScreen } from '../screens/citizen/ReportIncidentScreen';
import { EmergencyScreen } from '../screens/citizen/EmergencyScreen';
import { SettingsScreen } from '../screens/settings/SettingsScreen';

const Tab = createBottomTabNavigator();

export const CitizenTabs: React.FC = () => {
  const { t } = useTranslation();

  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: '#0f172a' },
        headerTitleStyle: { color: '#f8fafc', fontWeight: '800' },
        tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#334155', height: 60, paddingBottom: 8 },
        tabBarActiveTintColor: '#38bdf8',
        tabBarInactiveTintColor: '#64748b',
        tabBarLabelStyle: { fontWeight: '700', fontSize: 10 },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: t('citizen.home_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>🏠</Text>,
        }}
      />
      <Tab.Screen
        name="LiveMap"
        component={LiveMapScreen}
        options={{
          title: t('citizen.live_map_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>🗺️</Text>,
        }}
      />
      <Tab.Screen
        name="SafeRoute"
        component={FindSafeRouteScreen}
        options={{
          title: t('citizen.safe_route_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>🧭</Text>,
        }}
      />
      <Tab.Screen
        name="Report"
        component={ReportIncidentScreen}
        options={{
          title: t('citizen.report_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>📢</Text>,
        }}
      />
      <Tab.Screen
        name="Emergency"
        component={EmergencyScreen}
        options={{
          title: t('citizen.emergency_tab'),
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 16 }}>🆘</Text>,
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
