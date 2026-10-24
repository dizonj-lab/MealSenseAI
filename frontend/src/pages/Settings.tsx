import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, FileCode2, LogOut, ShieldAlert, Trash2, Utensils } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Card, InfoTip } from '../components/ui'
import { useTheme, type ThemePref } from '../lib/theme'

export default function Settings() {
  const { user, logout, setUser } = useAuth()
  const { pref, setPref } = useTheme()
  const [mine, setMine] = useState<any[]>([])
  useEffect(() => { api<any[]>('/foods/custom').then(setMine).catch(() => {}) }, [])
  const consent = async (v: boolean) => setUser(await api('/users/me/training-consent', { method: 'PUT', json: { consent: v } }))
  const nav = useNavigate()
  const del = async () => {
    if (!confirm('Delete your account, profile and all meals? This cannot be undone.')) return
    await api('/users/me', { method: 'DELETE' }); logout(); nav('/register')
  }
  return (
    <div className="space-y-4 max-w-2xl">
      <Card title="Account">
        <div className="text-sm"><div className="font-medium">{user?.name || '—'}</div><div className="text-slate-500">{user?.email}</div>
          <div className="text-xs text-slate-400 mt-1">Member since {user && new Date(user.created_at).toLocaleDateString()}</div></div>
        <button className="btn-ghost mt-4" onClick={() => { logout(); nav('/login') }}><LogOut className="size-4" />Log out</button>
      </Card>
      <Card title="Developer"><a className="btn-ghost" href="/docs" target="_blank" rel="noreferrer"><FileCode2 className="size-4" />OpenAPI docs</a></Card>
      <Card title="About & safety" icon={<ShieldAlert className="size-5 text-amber-500" />}>
        <p className="text-sm text-slate-600">MealSenseAI provides general, educational nutrition information estimated from photos and reference food-composition data. It does not predict your personal glucose response, set clinical targets or advise on medication. Talk to your healthcare team about your care.</p>
      </Card>
      <Card title="Appearance">
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-xl bg-slate-100 p-1 text-sm font-semibold" role="group" aria-label="Theme">
            {([['system', 'System'], ['light', 'Light'], ['dark', 'Dark']] as [ThemePref, string][]).map(([v, l]) => <button key={v} onClick={() => setPref(v)} aria-pressed={pref === v}
              className={`rounded-lg px-4 py-2 ${pref === v ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}>{l}</button>)}</div>
          <InfoTip label="Theme" text="System follows your phone's light/dark setting. The sun/moon icon in the header switches it too. Saved on this device." />
        </div>
      </Card>
      <Card title="Your foods" icon={<Utensils className="size-5 text-violet-600" />}>
        {mine.length ? <ul className="divide-y divide-slate-100 text-sm">{mine.map(f => <li key={f.id} className="py-2 flex justify-between gap-2">
          <span className="font-medium text-slate-800">{f.name}</span>
          <span className="text-xs text-slate-500 text-right">{f.serving_desc} · {f.default_serving_g} g · {f.per_100g.calories_kcal ?? '?'} kcal/100 g</span></li>)}</ul>
          : <p className="text-sm text-slate-500">Foods you create while naming an item appear here.</p>}
      </Card>
      <Card title="Learning from your corrections" icon={<Brain className="size-5 text-brand-600" />}>
        <p className="text-sm text-slate-600">When you name or correct a food in a photo, MealSenseAI remembers it and recognises it next time, for your account only.</p>
        <label className="mt-3 flex items-start gap-3 rounded-xl bg-slate-50 p-3 cursor-pointer">
          <input type="checkbox" className="mt-1 size-4 accent-teal-600" checked={!!user?.training_consent} onChange={e => consent(e.target.checked)} />
          <span className="text-sm"><span className="font-semibold text-slate-800">Use my corrected photos to improve the model</span>
            <span className="block text-slate-500">The cropped food region and your label may be exported (without your name or email) as training data for the next model version. You can switch this off at any time; exports made before then are not recalled.</span></span>
        </label>
      </Card>
      <Card title="Privacy">
        <p className="text-sm text-slate-600 mb-3">All data and AI inference stay on this self-hosted server. Health details are stored only with consent.</p>
        <button className="btn-ghost text-rose-600" onClick={del}><Trash2 className="size-4" />Delete account & data</button>
      </Card>
    </div>
  )
}
