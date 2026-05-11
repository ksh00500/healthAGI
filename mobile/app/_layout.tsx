import { Stack, useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { useAuth } from '@/features/auth/store';
import { ensureNotificationSetup } from '@/lib/notifications';

export default function RootLayout() {
  const bootstrap = useAuth((s) => s.bootstrap);
  const status = useAuth((s) => s.status);
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    bootstrap();
    ensureNotificationSetup();
  }, [bootstrap]);

  useEffect(() => {
    if (status === 'idle' || status === 'loading') return;
    const inAuthGroup = segments[0] === '(auth)';
    if (status === 'unauthed' && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (status === 'authed' && inAuthGroup) {
      router.replace('/(tabs)/timers');
    }
  }, [status, segments, router]);

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </SafeAreaProvider>
  );
}
