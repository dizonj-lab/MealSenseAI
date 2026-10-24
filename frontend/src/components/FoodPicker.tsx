import { useEffect, useState } from 'react'
import { Plus, Search, X } from 'lucide-react'
import { api } from '../lib/api'
import { InfoTip } from './ui'
import type { FoodRef } from '../lib/types'

export default function FoodPicker({ title, onPick, onClose, initial = '' }: { title: string; onPick: (f: FoodRef, grams: number | null) => void; onClose: () => void; initial?: string }) {
  const [q, setQ] = useState(initial)
  const [list, setList] = useState<FoodRef[]>([])
  const [sel, setSel] = useState<FoodRef | null>(null)
  const [grams, setGrams] = useState('')
  const [creating, setCreating] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => api<FoodRef[]>(`/foods/search?q=${encodeURIComponent(q)}`).then(setList).catch(() => {}), 150)
    return () => clearTimeout(t)
  }, [q])
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div className="relative w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl max-h-[85vh] flex flex-col pb-safe">
        <div className="flex items-center justify-between p-4 pb-2"><h3 className="font-semibold">{title}</h3><button onClick={onClose} className="p-1"><X className="size-5" /></button></div>
        {creating ? <CustomFoodForm name={q} onCancel={() => setCreating(false)} onCreated={(f, g) => onPick(f, g)} /> : <>
        <div className="px-4 relative"><Search className="size-4 absolute left-7 top-3.5 text-slate-400" />
          <input autoFocus className="input pl-9" placeholder="Search e.g. chicken rice, laksa, apple" value={q} onChange={e => { setQ(e.target.value); setSel(null) }} /></div>
        <div className="px-4 pt-2 pb-1 border-b border-slate-100 flex items-center gap-1">
          <button onClick={() => setCreating(true)} className="flex-1 min-w-0 text-left rounded-xl px-3 py-2.5 flex items-center gap-2 text-brand-700 font-semibold bg-brand-50 hover:bg-brand-100">
            <Plus className="size-4 shrink-0" /><span className="truncate">Can't find it? Create “{q.trim() || 'a new food'}”</span></button>
          <InfoTip label="Create your own food" align="right" text="Not in the list? Add it with your usual portion and the nutrients you know (blank = unknown). It is saved to your foods, and this photo region is remembered so it is recognised next time." />
        </div>
        <ul className="overflow-y-auto px-2 py-2 flex-1">
          {list.map(f => (
            <li key={f.key}><button onClick={() => { setSel(f); setGrams(String(f.default_serving_g)) }}
              className={`w-full text-left rounded-xl px-3 py-2.5 flex justify-between gap-2 ${sel?.key === f.key ? 'bg-brand-50 ring-1 ring-brand-200' : 'hover:bg-slate-50'}`}>
              <span><span className="font-medium text-slate-800">{f.name}</span>{f.region === 'sg' && <span className="chip bg-sky-50 text-sky-700 ml-2">SG</span>}
                {f.custom && <span className="chip bg-violet-50 text-violet-700 ml-2">Yours</span>}</span>
              <span className="text-xs text-slate-400 shrink-0">{f.serving_desc} · {f.default_serving_g} g</span></button></li>))}
        </ul>
        {sel && <div className="border-t border-slate-100 p-4 flex gap-2 items-end">
          <label className="block flex-1"><span className="label">Portion (grams)</span><input className="input" type="number" inputMode="decimal" value={grams} onChange={e => setGrams(e.target.value)} /></label>
          <button className="btn-primary" onClick={() => onPick(sel, grams ? Number(grams) : null)}>Use {sel.name.split(' ')[0]}</button>
        </div>}</>}
      </div>
    </div>
  )
}

const FIELDS: [string, string, string][] = [['calories_kcal', 'Calories', 'kcal'], ['carbs_g', 'Carbohydrate', 'g'], ['sugar_g', 'of which sugar', 'g'],
  ['fiber_g', 'Fibre', 'g'], ['protein_g', 'Protein', 'g'], ['fat_g', 'Fat', 'g'], ['sat_fat_g', 'of which saturated', 'g'], ['sodium_mg', 'Sodium', 'mg']]

/** Define a food that is not in the reference table. Blank values are stored as unknown, never filled in. */
function CustomFoodForm({ name, onCancel, onCreated }: { name: string; onCancel: () => void; onCreated: (f: FoodRef, grams: number) => void }) {
  const [f, setF] = useState({ name: name.trim(), serving_desc: '1 serving', serving_g: '', gi: '' })
  const [basis, setBasis] = useState<'serving' | '100g'>('serving')
  const [vals, setVals] = useState<Record<string, string>>({})
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const g = Number(f.serving_g)
  const save = async () => {
    setErr(null); setBusy(true)
    const scale = basis === 'serving' ? 100 / g : 1
    const per_100g = Object.fromEntries(FIELDS.map(([k]) => [k, vals[k] === undefined || vals[k] === '' ? null : Math.round(Number(vals[k]) * scale * 100) / 100]))
    try {
      const r = await api<any>('/foods/custom', { method: 'POST', json: { name: f.name, serving_g: g, serving_desc: f.serving_desc || '1 serving', per_100g, glycemic_index: f.gi ? Number(f.gi) : null } })
      onCreated({ key: r.key, name: r.name, category: 'custom', region: 'custom', default_serving_g: r.default_serving_g, serving_desc: r.serving_desc, custom: true }, g)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="overflow-y-auto px-4 pb-4 space-y-3">
      <p className="text-xs text-slate-500">Saved to <b>your foods</b> so you can pick it again. Leave a value blank if you don't know it; it stays unknown rather than guessed. A food label or the vendor's information is the best source.</p>
      <label className="block"><span className="label">Food name</span><input className="input" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></label>
      <div className="grid grid-cols-2 gap-2">
        <label className="block"><span className="label">Usual portion (g)</span><input className="input" type="number" inputMode="decimal" value={f.serving_g} onChange={e => setF({ ...f, serving_g: e.target.value })} /></label>
        <label className="block"><span className="label">Described as</span><input className="input" value={f.serving_desc} onChange={e => setF({ ...f, serving_desc: e.target.value })} placeholder="1 bowl" /></label>
      </div>
      <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-slate-700">Nutrients</span>
        <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-xs font-semibold" role="group" aria-label="Values are per">
          {([['serving', 'per portion'], ['100g', 'per 100 g']] as const).map(([v, l]) => <button key={v} type="button" aria-pressed={basis === v} onClick={() => setBasis(v)}
            className={`rounded-md px-2.5 py-1 ${basis === v ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}>{l}</button>)}</div></div>
      <div className="grid grid-cols-2 gap-2">{FIELDS.map(([k, l, u]) => (
        <label key={k} className="block"><span className="text-xs text-slate-500">{l} ({u})</span>
          <input className="input py-2" type="number" inputMode="decimal" min={0} placeholder="unknown" value={vals[k] ?? ''} onChange={e => setVals({ ...vals, [k]: e.target.value })} /></label>))}</div>
      <label className="block"><span className="label">Glycaemic index <span className="font-normal text-slate-400">(optional, 0–110)</span></span>
        <input className="input" type="number" inputMode="decimal" placeholder="unknown" value={f.gi} onChange={e => setF({ ...f, gi: e.target.value })} /></label>
      {err && <p className="text-sm text-rose-600">{err}</p>}
      <div className="flex gap-2 pt-1">
        <button className="btn-ghost flex-1" onClick={onCancel}>Back</button>
        <button className="btn-primary flex-1" disabled={busy || !f.name.trim() || !(g > 0)} onClick={save}>Save & use</button>
      </div>
    </div>
  )
}
