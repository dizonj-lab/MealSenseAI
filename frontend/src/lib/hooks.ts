import { useEffect, useState } from 'react'
import { api, tokenStore } from './api'

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!!path)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    if (!path) return
    let live = true
    setLoading(true)
    api<T>(path).then(d => live && (setData(d), setError(null))).catch(e => live && setError(e.message)).finally(() => live && setLoading(false))
    return () => { live = false }
  }, [path, tick, ...deps])
  return { data, error, loading, reload: () => setTick(t => t + 1), setData }
}

/** Images are owner-protected, so fetch them with the bearer token and use an object URL. */
export function useAuthImage(src: string | null) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!src) return
    let obj: string | null = null
    fetch(src, { headers: { Authorization: `Bearer ${tokenStore.get()}` } })
      .then(r => (r.ok ? r.blob() : null)).then(b => { if (b) { obj = URL.createObjectURL(b); setUrl(obj) } })
    return () => { if (obj) URL.revokeObjectURL(obj) }
  }, [src])
  return url
}
