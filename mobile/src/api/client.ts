import { API_BASE_URL } from '@/lib/config';
import { clearTokens, loadTokens, saveTokens } from '@/lib/storage';

class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

let inMemoryAccess: string | null = null;
let inMemoryRefresh: string | null = null;
let refreshPromise: Promise<void> | null = null;

export async function hydrateTokens(): Promise<boolean> {
  const tok = await loadTokens();
  if (!tok) return false;
  inMemoryAccess = tok.access;
  inMemoryRefresh = tok.refresh;
  return true;
}

export async function setTokens(access: string, refresh: string): Promise<void> {
  inMemoryAccess = access;
  inMemoryRefresh = refresh;
  await saveTokens(access, refresh);
}

export async function logout(): Promise<void> {
  inMemoryAccess = null;
  inMemoryRefresh = null;
  await clearTokens();
}

async function tryRefresh(): Promise<void> {
  if (!inMemoryRefresh) throw new ApiError(401, 'no refresh token');
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const r = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ refresh_token: inMemoryRefresh }),
    });
    if (!r.ok) {
      await logout();
      throw new ApiError(r.status, 'refresh failed');
    }
    const data = (await r.json()) as { access_token: string; refresh_token: string };
    await setTokens(data.access_token, data.refresh_token);
  })().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  query?: Record<string, string | number | boolean | undefined>;
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, query } = opts;
  const headers: Record<string, string> = { 'content-type': 'application/json' };

  const doFetch = async (): Promise<Response> => {
    if (auth && inMemoryAccess) headers.authorization = `Bearer ${inMemoryAccess}`;
    return fetch(buildUrl(path, query), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();
  if (res.status === 401 && auth && inMemoryRefresh) {
    try {
      await tryRefresh();
      res = await doFetch();
    } catch {
      throw new ApiError(401, 'unauthorized');
    }
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const parsed = text ? safeJson(text) : undefined;
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`, parsed);
  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export { ApiError };
