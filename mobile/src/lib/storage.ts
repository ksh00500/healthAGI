import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

const isWeb = Platform.OS === 'web';

async function getItem(key: string): Promise<string | null> {
  if (isWeb) return localStorage.getItem(key);
  return SecureStore.getItemAsync(key);
}

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) { localStorage.setItem(key, value); return; }
  await SecureStore.setItemAsync(key, value);
}

async function deleteItem(key: string): Promise<void> {
  if (isWeb) { localStorage.removeItem(key); return; }
  await SecureStore.deleteItemAsync(key);
}

export async function saveTokens(access: string, refresh: string): Promise<void> {
  await setItem(ACCESS_KEY, access);
  await setItem(REFRESH_KEY, refresh);
}

export async function loadTokens(): Promise<{ access: string; refresh: string } | null> {
  const access = await getItem(ACCESS_KEY);
  const refresh = await getItem(REFRESH_KEY);
  if (!access || !refresh) return null;
  return { access, refresh };
}

export async function clearTokens(): Promise<void> {
  await deleteItem(ACCESS_KEY);
  await deleteItem(REFRESH_KEY);
}
