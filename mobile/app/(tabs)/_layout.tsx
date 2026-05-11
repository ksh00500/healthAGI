import { Tabs } from 'expo-router';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: '#0b0d10' },
        headerTitleStyle: { color: '#fff' },
        tabBarStyle: { backgroundColor: '#0b0d10', borderTopColor: '#16191e' },
        tabBarActiveTintColor: '#3b82f6',
        tabBarInactiveTintColor: '#6b7280',
      }}
    >
      <Tabs.Screen name="timers" options={{ title: '타이머' }} />
      <Tabs.Screen name="profile" options={{ title: '프로필' }} />
    </Tabs>
  );
}
