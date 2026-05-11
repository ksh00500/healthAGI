import Constants from 'expo-constants';

const extra = (Constants.expoConfig?.extra ?? {}) as { apiBaseUrl?: string };

export const API_BASE_URL: string = extra.apiBaseUrl ?? 'http://localhost:8000/v1';
