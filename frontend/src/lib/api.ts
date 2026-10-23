const TOKEN_KEY = 'msai_token'
export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t: string | null) => { try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ } },
}

export class ApiError extends Error { constructor(public status: number, msg: string) { super(msg) } }

export async function api<T = any>(path: string, opts: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string>) }
  const t = tokenStore.get()
  if (t) headers.Authorization = `Bearer ${t}`
  let body = opts.body
  if (opts.json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(opts.json) }
  const r = await fetch(`/api/v1${path}`, { ...opts, headers, body })
  if (r.status === 401 && t) { tokenStore.set(null); window.location.assign('/login') }
  if (!r.ok) {
    if (r.status === 504 || r.status === 502) throw new ApiError(r.status, 'The server took too long or is restarting. Please try again in a moment; if it keeps happening, check `docker compose logs backend`.')
    let msg = r.statusText
    try {
      const j = await r.json()
      msg = typeof j.detail === 'string' ? j.detail : (j.detail || []).map((d: any) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join('; ')
    } catch { /* not json */ }
    throw new ApiError(r.status, msg)
  }
  return r.status === 204 ? (undefined as T) : r.json()
}

export const tzOffset = () => -new Date().getTimezoneOffset()

export const fmt = (v: number | null | undefined, d = 0) => (v === null || v === undefined ? '—' : Number(v).toFixed(d))
