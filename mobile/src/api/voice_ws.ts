import { hydrateTokens } from '@/api/client';
import { API_BASE_URL } from '@/lib/config';
import { loadTokens } from '@/lib/storage';

export type VoiceServerEvent =
  | { type: 'ready'; conversation_id: string | null; sample_rate: number }
  | { type: 'stt_final'; text: string; user_message_id: string; conversation_id: string }
  | { type: 'llm_token'; text: string }
  | { type: 'llm_done'; reply_text: string; assistant_message_id: string }
  | {
      type: 'tts_chunk';
      seq: number;
      audio_b64: string;
      mime: string;
      sample_rate: number;
      text: string;
    }
  | { type: 'tts_done'; interrupted?: boolean }
  | { type: 'error'; message: string };

export interface VoiceWSHandlers {
  onEvent: (evt: VoiceServerEvent) => void;
  onClose?: (code: number, reason: string) => void;
}

/**
 * One PTT turn over the /ws/voice protocol:
 *  start -> audio_file -> end_of_speech -> ...stream of events... -> close
 *
 * Returns a handle that can `interrupt()` or `close()` mid-turn.
 */
export async function openVoiceTurn(args: {
  audioB64: string;
  audioMime: string;
  conversationId?: string;
  handlers: VoiceWSHandlers;
}): Promise<{ interrupt: () => void; close: () => void }> {
  await hydrateTokens();
  const tok = await loadTokens();
  if (!tok) throw new Error('not authenticated');

  // API_BASE_URL is `http(s)://host/v1` — flip the scheme to ws(s).
  const wsBase = API_BASE_URL.replace(/^http/, 'ws');
  const url = `${wsBase}/ws/voice?token=${encodeURIComponent(tok.access)}`;
  const ws = new WebSocket(url);

  let opened = false;

  ws.onopen = () => {
    opened = true;
    ws.send(
      JSON.stringify({
        type: 'start',
        conversation_id: args.conversationId ?? null,
        sample_rate: 16000,
      }),
    );
  };

  ws.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data as string) as VoiceServerEvent;
      if (parsed.type === 'ready') {
        ws.send(
          JSON.stringify({
            type: 'audio_file',
            b64: args.audioB64,
            mime: args.audioMime,
          }),
        );
        ws.send(JSON.stringify({ type: 'end_of_speech' }));
      }
      args.handlers.onEvent(parsed);
      if (parsed.type === 'tts_done') {
        // Server-initiated end of turn — close cleanly.
        try {
          ws.send(JSON.stringify({ type: 'close' }));
        } catch {
          /* ignore */
        }
        ws.close();
      }
    } catch (e) {
      args.handlers.onEvent({
        type: 'error',
        message: `parse error: ${String(e)}`,
      });
    }
  };

  ws.onerror = () => {
    if (!opened) {
      args.handlers.onEvent({ type: 'error', message: 'WebSocket open failed' });
    }
  };

  ws.onclose = (evt) => {
    args.handlers.onClose?.(evt.code, evt.reason ?? '');
  };

  return {
    interrupt() {
      try {
        ws.send(JSON.stringify({ type: 'interrupt' }));
      } catch {
        /* ignore */
      }
    },
    close() {
      try {
        ws.send(JSON.stringify({ type: 'close' }));
      } catch {
        /* ignore */
      }
      ws.close();
    },
  };
}
