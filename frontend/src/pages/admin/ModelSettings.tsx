import { useEffect, useState } from 'react'
import { RotateCcw, Save, SlidersHorizontal } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { Card, ErrorNote, Spinner } from '../../components/ui'

type S = { key: string; group: string; label: string; help: string; kind: string; min: number | null; max: number | null; unit: string
  nullable: boolean; default: any; value: any; overridden: boolean; updated_at: string | null }
const show = (v: any, unit = '') => (v === null || v === undefined || v === '' ? 'automatic' : typeof v === 'boolean' ? (v ? 'on' : 'off') : `${v}${unit ? ` ${unit}` : ''}`)

function Row({ s, models, onSaved }: { s: S; models: string[]; onSaved: (n: S) => void }) {
  const [v, setV] = useState<any>(s.value ?? '')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => setV(s.value ?? ''), [s.value])
  const changed = (v === '' ? null : s.kind === 'float' || s.kind === 'int' ? Number(v) : v) !== s.value
  const call = async (method: 'PUT' | 'DELETE') => {
    setBusy(true); setErr(null)
    try { onSaved(await api<S>(`/admin/settings/${s.key}`, method === 'PUT' ? { method, json: { value: v === '' ? null : s.kind === 'bool' || s.kind === 'str' ? v : Number(v) } } : { method })) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const input = s.kind === 'bool'
    ? <button type="button" role="switch" aria-checked={!!v} aria-label={s.label} onClick={() => setV(!v)} className={`w-11 h-6 rounded-full relative transition ${v ? 'bg-brand-600' : 'bg-slate-200'}`}>
        <span className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-all ${v ? 'left-[22px]' : 'left-0.5'}`} /></button>
    : s.key === 'slm.model'
      ? <select className="input py-1.5 w-56" value={v ?? ''} onChange={e => setV(e.target.value)} aria-label={s.label}><option value="">Automatic</option>
          {models.map(m => <option key={m} value={m}>{m}</option>)}{v && !models.includes(v) && <option value={v}>{v} (not installed)</option>}</select>
      : <div className="flex items-center gap-1.5"><input className="input py-1.5 w-28 text-right tabular-nums" type="number" aria-label={s.label}
          step={s.kind === 'int' ? 1 : 0.01} min={s.min ?? undefined} max={s.max ?? undefined} value={v ?? ''} placeholder={s.nullable ? 'auto' : ''} onChange={e => setV(e.target.value)} />
          {s.unit && <span className="text-xs text-slate-500 w-6">{s.unit}</span>}</div>
  return (
    <li className="py-3 grid sm:grid-cols-[1fr_auto] gap-x-6 gap-y-2 items-start">
      <div className="min-w-0"><div className="font-medium text-slate-800 flex items-center gap-2">{s.label}
        {s.overridden && <span className="chip bg-brand-50 text-brand-700 text-[10px]">changed</span>}</div>
        <p className="text-xs text-slate-500 mt-0.5">{s.help}</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Default {show(s.default, s.unit)}{s.min != null && s.kind !== 'bool' ? ` · range ${s.min}–${s.max}` : ''} · <code>{s.key}</code></p>
        <ErrorNote msg={err} /></div>
      <div className="flex items-center gap-2 sm:justify-end">{input}
        <button className="btn-primary px-3 py-1.5 text-xs" disabled={!changed || busy} onClick={() => call('PUT')}>{busy ? <Spinner className="size-3.5 text-white" /> : <Save className="size-3.5" />}Save</button>
        {s.overridden && <button className="btn-ghost px-2.5 py-1.5 text-xs" disabled={busy} onClick={() => call('DELETE')} title="Back to the default"><RotateCcw className="size-3.5" /></button>}</div>
    </li>
  )
}

/** Tunable thresholds and limits. A change applies within seconds, without a restart, and is audited. */
export default function ModelSettings() {
  const { data, setData } = useApi<{ settings: S[]; slm_models: string[] }>('/admin/settings')
  if (!data) return <div className="py-16 grid place-items-center"><Spinner /></div>
  const groups = [...new Set(data.settings.map(s => s.group))]
  const saved = (n: S) => setData({ ...data, settings: data.settings.map(s => (s.key === n.key ? n : s)) })
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500 flex items-center gap-2"><SlidersHorizontal className="size-4" />Changes apply within ten seconds, for every user, and are recorded in the audit log. Reset returns a setting to its default.</p>
      {groups.map(g => <Card key={g} title={g}><ul className="divide-y divide-slate-100">
        {data.settings.filter(s => s.group === g).map(s => <Row key={s.key} s={s} models={data.slm_models} onSaved={saved} />)}</ul></Card>)}
    </div>
  )
}
