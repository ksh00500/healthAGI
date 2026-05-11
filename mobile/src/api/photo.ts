import { hydrateTokens } from '@/api/client';
import { API_BASE_URL } from '@/lib/config';
import { loadTokens } from '@/lib/storage';
import type { PhotoAnalyzeResponse } from '@/api/types';

/**
 * Upload a meal photo to /meals/photo/analyze via multipart and return the
 * proposed items + storage_key. Client should let the user edit items, then
 * POST /meals with `photo_storage_key` set to attach the photo to the meal.
 */
export async function analyzePhoto(args: {
  uri: string;
  mime: string;
  fileName?: string;
}): Promise<PhotoAnalyzeResponse> {
  await hydrateTokens();
  const tok = await loadTokens();
  if (!tok) throw new Error('not authenticated');

  const form = new FormData();
  form.append('photo', {
    uri: args.uri,
    name: args.fileName ?? 'meal.jpg',
    type: args.mime,
  } as unknown as Blob);

  const res = await fetch(`${API_BASE_URL}/meals/photo/analyze`, {
    method: 'POST',
    headers: { authorization: `Bearer ${tok.access}` },
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`photo/analyze ${res.status}: ${text.slice(0, 200)}`);
  }
  return (await res.json()) as PhotoAnalyzeResponse;
}
