import Constants from 'expo-constants';
import { Platform } from 'react-native';

const isExpoGo = Constants.appOwnership === 'expo';

type NotificationsModule = typeof import('expo-notifications');

let _mod: NotificationsModule | null = null;
let configured = false;

function getModule(): NotificationsModule | null {
  if (_mod) return _mod;
  // In Expo Go SDK 53+ expo-notifications throws at module load time. Skip
  // touching it entirely there — local notifications need a dev build anyway.
  if (isExpoGo) return null;
  try {
    _mod = require('expo-notifications') as NotificationsModule;
  } catch {
    return null;
  }
  return _mod;
}

export async function ensureNotificationSetup(): Promise<void> {
  if (configured) return;
  configured = true;

  const Notifications = getModule();
  if (!Notifications) return;

  try {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      }),
    });

    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('recovery', {
        name: '회복 타이머',
        importance: Notifications.AndroidImportance.DEFAULT,
        vibrationPattern: [0, 250, 250, 250],
      });
    }

    const { status } = await Notifications.getPermissionsAsync();
    if (status !== 'granted') {
      await Notifications.requestPermissionsAsync();
    }
  } catch (e) {
    console.warn('notification setup skipped:', e);
  }
}

export interface ScheduleArgs {
  muscleNameKo: string;
  endTime: Date;
}

export async function scheduleRecoveryEnd(args: ScheduleArgs): Promise<string | null> {
  await ensureNotificationSetup();
  if (args.endTime.getTime() <= Date.now()) return null;

  const Notifications = getModule();
  if (!Notifications) return null;
  if (isExpoGo) {
    // Local notification scheduling still works on dev builds, but in Expo Go
    // SDK 53+ this whole module is unreliable — skip silently.
    return null;
  }

  try {
    return await Notifications.scheduleNotificationAsync({
      content: {
        title: '회복 완료',
        body: `${args.muscleNameKo} 회복 타이머가 종료되었어요. 운동 가능합니다.`,
        sound: true,
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: args.endTime,
        channelId: Platform.OS === 'android' ? 'recovery' : undefined,
      },
    });
  } catch (e) {
    console.warn('scheduleNotification failed:', e);
    return null;
  }
}

export async function cancelScheduled(id: string): Promise<void> {
  const Notifications = getModule();
  if (!Notifications) return;
  try {
    await Notifications.cancelScheduledNotificationAsync(id);
  } catch {
    // already fired or missing — ignore
  }
}
