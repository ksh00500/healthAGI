import { Redirect } from 'expo-router';
import { useAuth } from '@/features/auth/store';

export default function Index() {
  const status = useAuth((s) => s.status);
  if (status === 'authed') return <Redirect href="/(tabs)/timers" />;
  return <Redirect href="/(auth)/login" />;
}
