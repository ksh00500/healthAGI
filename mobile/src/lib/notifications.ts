import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

let configured = false;

export async function ensureNotificationSetup(): Promise<void> {
  if (configured) return;
  configured = true;

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
}

export interface ScheduleArgs {
  muscleNameKo: string;
  endTime: Date;
}

export async function scheduleRecoveryEnd(args: ScheduleArgs): Promise<string | null> {
  await ensureNotificationSetup();
  if (args.endTime.getTime() <= Date.now()) return null;
  return Notifications.scheduleNotificationAsync({
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
}

export async function cancelScheduled(id: string): Promise<void> {
  try {
    await Notifications.cancelScheduledNotificationAsync(id);
  } catch {
    // already fired or missing — ignore
  }
}
