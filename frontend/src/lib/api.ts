// Tiny fetch wrapper: same-origin /api, JSON in/out, typed errors (FastAPI `{detail}` shape).

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `HTTP ${res.status}`;
  try {
    const json = await res.json();
    if (typeof json?.detail === 'string') message = json.detail;
  } catch {
    /* keep default */
  }
  return new ApiError(res.status, message);
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
