// Tiny fetch wrapper: same-origin /api, JSON in/out, typed errors (FastAPI `{detail}` shape).
import { DICT, type Key } from '@/i18n';

export class ApiError extends Error {
  status: number;
  code?: string;
  extra?: Record<string, unknown>;
  constructor(status: number, message: string, code?: string, extra?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `HTTP ${res.status}`;
  let code: string | undefined;
  let extra: Record<string, unknown> | undefined;
  try {
    const json = await res.json();
    const detail = json?.detail;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      code = 'validation_failed';
      message = code;
    } else if (detail && typeof detail === 'object') {
      const { code: c, ...rest } = detail as Record<string, unknown>;
      if (typeof c === 'string') {
        code = c;
        message = c;
      }
      extra = rest;
    }
  } catch {
    /* keep default */
  }
  return new ApiError(res.status, message, code, extra);
}

export type TFn = (key: Key, vars?: Record<string, string | number>) => string;

/** Prefer a translated `api.<code>` message; fall back to the raw error text. */
export function apiMessage(t: TFn, err: unknown): string {
  if (err instanceof ApiError && err.code) {
    const key = `api.${err.code}` as Key;
    if (Object.prototype.hasOwnProperty.call(DICT.en, key)) return t(key);
  }
  if (err instanceof Error) return err.message;
  return String(err);
}

export async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (init.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) throw await parseError(res);
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return fetchJson<T>(path, { method: 'POST', body: JSON.stringify(body) });
}
