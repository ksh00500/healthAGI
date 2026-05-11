import { hydrateTokens } from '@/api/client';
import { API_BASE_URL } from '@/lib/config';
import { loadTokens } from '@/lib/storage';
import type { VoiceTurnResponse } from '@/api/types';

/**
 * Upload a recorded audio file to /voice/turn as multipart and return the
 * full turn (transcript + reply text + base64 TTS audio).
 */
export async function uploadVoiceTurn(args: {
  audioUri: string;
  audioMime: string;
  fileName?: string;
  conversationId?: string;
}): Promise<VoiceTurnResponse> {
  await hydrateTokens();
  const tok = await loadTokens();
  if (!tok) throw new Error('not authenticated');

  const form = new FormData();
  form.append('audio', {
    // RN's FormData accepts this shape for file uploads.
    uri: args.audioUri,
    name: args.fileName ?? 'audio.m4a',
    type: args.audioMime,
  } as unknown as Blob);
  if (args.conversationId) form.append('conversation_id', args.conversationId);

  const res = await fetch(`${API_BASE_URL}/voice/turn`, {
    method: 'POST',
    headers: { authorization: `Bearer ${tok.access}` },
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`voice/turn ${res.status}: ${text.slice(0, 200)}`);
  }
  return (await res.json()) as VoiceTurnResponse;
}
