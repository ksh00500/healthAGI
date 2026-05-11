import { API_BASE_URL } from '@/lib/config';
import { hydrateTokens } from '@/api/client';
import { loadTokens } from '@/lib/storage';

export interface SSEEvent {
  event: string;
  data: string;
}

/**
 * POST with an authorized bearer token and stream `text/event-stream` events.
 * Yields decoded {event, data} objects. Handles partial chunks across reads.
 */
export async function* postSSE(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent, void, unknown> {
  await hydrateTokens(); // ensure in-memory token from secure store
  const tok = await loadTokens();
  if (!tok) throw new Error('not authenticated');

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'text/event-stream',
      authorization: `Bearer ${tok.access}`,
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '');
    throw new Error(`SSE ${res.status}: ${text.slice(0, 200)}`);
  }

  const reader = (res.body as unknown as { getReader: () => ReadableStreamDefaultReader<Uint8Array> }).getReader();
  const decoder = new TextDecoder('utf-8');
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      const parsed = parseEvent(raw);
      if (parsed) yield parsed;
    }
  }
  if (buf.trim()) {
    const parsed = parseEvent(buf);
    if (parsed) yield parsed;
  }
}

function parseEvent(raw: string): SSEEvent | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of raw.split('\n')) {
    if (!line || line.startsWith(':')) continue;
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join('\n') };
}
