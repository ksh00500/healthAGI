import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioRecorder,
} from 'expo-audio';
import * as FileSystem from 'expo-file-system/legacy';
import { useCallback, useEffect, useRef, useState } from 'react';

export interface RecordingResult {
  uri: string;
  mime: string;
  fileName: string;
  durationMs: number;
}

let configured = false;

async function ensureRecordingMode(): Promise<void> {
  if (configured) return;
  const perm = await AudioModule.requestRecordingPermissionsAsync();
  if (!perm.granted) {
    throw new Error('마이크 권한이 거부되어 음성 모드를 사용할 수 없어요.');
  }
  await setAudioModeAsync({
    allowsRecording: true,
    playsInSilentMode: true,
    shouldPlayInBackground: false,
  });
  configured = true;
}

export function useVoiceRecorder() {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const startedAt = useRef<number | null>(null);
  const [recording, setRecording] = useState(false);

  const start = useCallback(async () => {
    await ensureRecordingMode();
    await recorder.prepareToRecordAsync();
    recorder.record();
    startedAt.current = Date.now();
    setRecording(true);
  }, [recorder]);

  const stop = useCallback(async (): Promise<RecordingResult | null> => {
    if (!recording) return null;
    await recorder.stop();
    setRecording(false);
    const uri = recorder.uri;
    if (!uri) return null;
    const durationMs = startedAt.current ? Date.now() - startedAt.current : 0;
    startedAt.current = null;
    // expo-audio HIGH_QUALITY preset writes m4a/aac on iOS, m4a/aac on Android.
    return { uri, mime: 'audio/m4a', fileName: 'turn.m4a', durationMs };
  }, [recorder, recording]);

  const cancel = useCallback(async () => {
    if (!recording) return;
    try {
      await recorder.stop();
    } catch {
      /* ignore */
    }
    setRecording(false);
    startedAt.current = null;
    if (recorder.uri) {
      FileSystem.deleteAsync(recorder.uri, { idempotent: true }).catch(() => undefined);
    }
  }, [recorder, recording]);

  return { recording, start, stop, cancel };
}

/**
 * Decode a base64 audio blob, write to a temp file, and play it.
 * Returns when playback ends.
 */
export function useTTSPlayer() {
  const [src, setSrc] = useState<string | null>(null);
  const player = useAudioPlayer(src);
  const resolveRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!src) return;
    const sub = player.addListener('playbackStatusUpdate', (status) => {
      if (status.didJustFinish) {
        resolveRef.current?.();
        resolveRef.current = null;
      }
    });
    player.play();
    return () => sub.remove();
  }, [src, player]);

  const play = useCallback(async (audioB64: string, ext = 'wav') => {
    const path = `${FileSystem.cacheDirectory}tts-${Date.now()}.${ext}`;
    await FileSystem.writeAsStringAsync(path, audioB64, {
      encoding: FileSystem.EncodingType.Base64,
    });
    return new Promise<void>((resolve) => {
      resolveRef.current = resolve;
      setSrc(path);
    });
  }, []);

  return { play };
}
