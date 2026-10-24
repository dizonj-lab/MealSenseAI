import { useEffect, useState } from 'react'

export type ThemePref = 'system' | 'light' | 'dark'
const KEY = 'mealsense.theme'
const mq = () => window.matchMedia('(prefers-color-scheme: dark)')

export function readPref(): ThemePref {
  try { return (localStorage.getItem(KEY) as ThemePref) || 'system' } catch { return 'system' }
}

export function applyTheme(pref: ThemePref) {
  const dark = pref === 'dark' || (pref === 'system' && mq().matches)
  document.documentElement.classList.toggle('dark', dark)
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0a111d' : '#0d9488')
}

/** Theme preference (system / light / dark), stored per device and applied to <html>. */
export function useTheme() {
  const [pref, setPref] = useState<ThemePref>(readPref)
  useEffect(() => {
    applyTheme(pref)
    try { localStorage.setItem(KEY, pref) } catch { /* private mode */ }
    if (pref !== 'system') return
    const m = mq(), on = () => applyTheme('system')
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [pref])
  return { pref, setPref, cycle: () => setPref(p => (p === 'system' ? 'light' : p === 'light' ? 'dark' : 'system')) }
}
