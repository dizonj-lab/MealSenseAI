import { useEffect, useMemo, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { Check, RotateCcw, SlidersHorizontal, Trash2 } from 'lucide-react'
import { api, fmt } from '../lib/api'
import type { Meal } from '../lib/types'
import { Card, ErrorNote, Spinner, Tag } from './ui'

type Reading = { id: number; measured_at: string; value_mmol: number; entered_unit: string; context: string; source: string }
const TIP = { fontSize: 11, whiteSpace: 'normal' as const }
const TIP_WRAP = { maxWidth: '65%', zIndex: 5 }
const ROWS: [string, string, number][] = [['grams', 'Portion (g)', 0], ['calories_kcal', 'Calories (kcal)', 0], ['carbs_g', 'Carbs (g)', 1],
  ['sugar_g', 'Sugar (g)', 1], ['protein_g', 'Protein (g)', 1], ['fat_g', 'Fat (g)', 1], ['sat_fat_g', 'Sat. fat (g)', 1], ['fiber_g', 'Fibre (g)', 1],
  ['sodium_mg', 'Sodium (mg)', 0], ['glycemic_load', 'Glycaemic load', 1], ['peak_index', 'Simulated peak (index)', 0], ['auc_index', 'Simulated area (index·h)', 1]]

/** Portion what-if: nothing is saved until the user presses "Apply". Simulated curves (relative index) are kept
 *  apart from measured readings (mmol/L) so the two are never confused. */
export default function PortionSimulator({ meal, onChange, readOnly }: { meal: Meal; onChange: (m: Meal) => void; readOnly: boolean }) {
  const foods = useMemo(() => meal.foods.filter(f => !f.removed && f.nutrition_key), [meal])
  const [grams, setGrams] = useState<Record<number, number>>({})
  const [sim, setSim] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [readings, setReadings] = useState<Reading[]>([])
  const [rv, setRv] = useState(''); const [ru, setRu] = useState('mmol/L'); const [rt, setRt] = useState(''); const [rc, setRc] = useState('after_meal')
  const changed = foods.filter(f => grams[f.id] !== undefined && grams[f.id] !== f.grams)
  const key = JSON.stringify(grams) + (meal.insights?.generated_at ?? '')

  useEffect(() => { setGrams({}) }, [meal.insights?.generated_at])
  useEffect(() => {
    if (!foods.length) return
    const t = setTimeout(() => api(`/meals/${meal.id}/simulate`, { method: 'POST', json: { portions: grams } }).then(setSim).catch(e => setErr(e.message)), 250)
    return () => clearTimeout(t)
  }, [key])  // eslint-disable-line react-hooks/exhaustive-deps
  const loadReadings = () => api<Reading[]>(`/glucose?meal_id=${meal.id}`).then(setReadings).catch(() => {})
  useEffect(() => { loadReadings() }, [meal.id])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!foods.length) return null

  const apply = async () => {
    setBusy(true); setErr(null)
    try { let m = meal; for (const f of changed) m = await api<Meal>(`/meals/${meal.id}/foods/${f.id}`, { method: 'PUT', json: { grams: Math.max(1, Math.round(grams[f.id])) } }); onChange(m) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const addReading = async () => {
    setErr(null)
    try {
      await api('/glucose', { method: 'POST', json: { value: Number(rv), unit: ru, context: rc, meal_id: meal.id, measured_at: new Date(rt || Date.now()).toISOString() } })
      setRv(''); loadReadings()
    } catch (e: any) { setErr(e.message) }
  }
  const eaten = new Date(meal.eaten_at).getTime()
  const pts = readings.map(r => ({ ...r, min: Math.round((new Date(r.measured_at).getTime() - eaten) / 60000) }))
  const data = sim ? sim.time_min.map((t: number, i: number) => ({ t, original: sim.curves.original[i], modified: sim.curves.modified[i],
    band: [sim.curves.modified_low[i], sim.curves.modified_high[i]] })) : []
  const T = sim?.totals

  return (
    <Card title="Portion simulator" icon={<SlidersHorizontal className="size-5 text-teal-600" />} action={<Tag kind="estimate" />}>
      <p className="text-xs text-slate-500 mb-3">Change portions to compare the original and a modified meal. Nothing is saved until you press <b>Apply</b>.</p>
      <div className="space-y-2.5">{foods.map(f => {
        const g = grams[f.id] ?? f.grams
        return <div key={f.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3">
          <div className="text-sm text-slate-700 truncate">{f.label} <span className="text-slate-400">· was {fmt(f.grams)} g</span></div>
          <div className="text-sm font-semibold tabular-nums">{fmt(g)} g <span className="text-xs font-normal text-slate-400">({fmt(f.grams ? g / f.grams * 100 : 0)}%)</span></div>
          <input aria-label={`${f.label} portion`} type="range" min={0} max={Math.max(f.grams * 2, 50)} step={Math.max(1, Math.round(f.grams / 20))} value={g}
            onChange={e => setGrams(s => ({ ...s, [f.id]: Number(e.target.value) }))} className="col-span-2 accent-teal-600" />
        </div> })}</div>
      {!sim ? <div className="py-6 grid place-items-center"><Spinner /></div> : <>
        <div className="mt-4 overflow-x-auto"><table className="w-full text-sm tabular-nums [&_th]:pl-3 [&_td]:pl-3">
          <thead><tr className="text-xs text-slate-500 text-right"><th className="text-left font-medium py-1">Meal total</th><th className="font-medium">Original</th><th className="font-medium">Modified</th><th className="font-medium">Change</th><th className="font-medium">%</th></tr></thead>
          <tbody>{ROWS.map(([k, l, d]) => { const df = T.diff[k] ?? {}; const neg = (df.abs ?? 0) < 0; return (
            <tr key={k} className="border-t border-slate-100 text-right">
              <td className="text-left py-1 text-slate-600">{l}</td><td>{fmt(T.original[k], d)}</td><td className="font-semibold">{fmt(T.modified[k], d)}</td>
              <td className={df.abs ? (neg ? 'text-emerald-700' : 'text-rose-700') : 'text-slate-400'}>{df.abs == null ? '—' : `${df.abs > 0 ? '+' : ''}${fmt(df.abs, d)}`}</td>
              <td className="text-slate-500">{df.pct == null ? '—' : `${df.pct > 0 ? '+' : ''}${fmt(df.pct, 0)}%`}</td></tr>) })}</tbody></table>
          <p className="mt-1 text-[11px] text-slate-400">GL: {T.modified.gl_coverage}. “—” means the value is not available in the nutrition table.</p></div>

        <h4 className="mt-4 text-sm font-semibold text-slate-700 flex items-center gap-2">Simulated glucose response <span className="chip bg-amber-50 text-amber-700">Simulated · relative index</span></h4>
        <ResponsiveContainer width="100%" height={220}><ComposedChart data={data} margin={{ left: -18, right: 8, top: 8 }}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="t" fontSize={11} unit=" min" /><YAxis fontSize={11} />
          <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: any, n: string) => Array.isArray(v) ? [`${v[0]}–${v[1]}`, n] : [v, n]} labelFormatter={t => `${t} min after eating`} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area dataKey="band" name="Modified: portion range" fill="#14b8a6" fillOpacity={0.15} stroke="none" />
          <Line dataKey="original" name="Original meal" stroke="#94a3b8" strokeDasharray="5 4" dot={false} strokeWidth={2} />
          <Line dataKey="modified" name="Modified meal" stroke="#0d9488" dot={false} strokeWidth={2.5} />
        </ComposedChart></ResponsiveContainer>
        <details className="text-[11px] text-slate-500"><summary className="cursor-pointer">Assumptions · {sim.simulation_version}</summary>
          <ul className="list-disc pl-4 mt-1">{sim.assumptions.map((a: string) => <li key={a}>{a}</li>)}<li>Shaded band: {sim.band}</li></ul></details>
        <p className="mt-1 text-[11px] text-slate-400">{sim.disclaimer}</p>
      </>}

      <h4 className="mt-5 text-sm font-semibold text-slate-700 flex items-center gap-2">Your measured readings <Tag kind="measured" /></h4>
      {pts.length ? <ResponsiveContainer width="100%" height={180}><ScatterChart margin={{ left: -18, right: 8, top: 8 }}>
        <CartesianGrid stroke="#e2e8f0" /><XAxis dataKey="min" type="number" name="Time" unit=" min" fontSize={11} domain={['dataMin - 15', 'dataMax + 15']} />
        <YAxis dataKey="value_mmol" type="number" name="Glucose" unit="" fontSize={11} domain={[0, (m: number) => Math.max(10, Math.ceil(m + 2))]} allowDecimals={false} /><ZAxis range={[60, 60]} />
        <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: any, n: string) => n === 'Glucose' ? `${v} mmol/L` : `${v} min after meal`} />
        <Scatter data={pts} name="Measured (mmol/L)" fill="#2563eb" line={{ stroke: '#93c5fd' }} />
      </ScatterChart></ResponsiveContainer> : <p className="text-xs text-slate-500">No readings for this meal. Readings are only shown when you enter them from your meter or CGM; the app never estimates them.</p>}
      {pts.length > 0 && <ul className="mt-1 text-xs text-slate-600 space-y-0.5">{pts.map(r => <li key={r.id} className="flex items-center gap-2">
        <b>{r.value_mmol.toFixed(1)} mmol/L</b><span className="text-slate-400">{r.min >= 0 ? `+${r.min}` : r.min} min · {r.context.replace('_', ' ')} · {r.source}</span>
        {!readOnly && <button aria-label="Delete reading" className="ml-auto text-slate-400 hover:text-rose-600" onClick={() => api(`/glucose/${r.id}`, { method: 'DELETE' }).then(loadReadings)}><Trash2 className="size-3.5" /></button>}</li>)}</ul>}
      {!readOnly && <div className="mt-2 grid grid-cols-2 sm:grid-cols-5 gap-2">
        <input className="input" type="number" inputMode="decimal" placeholder="Reading" aria-label="Glucose reading" value={rv} onChange={e => setRv(e.target.value)} />
        <select className="input" aria-label="Unit" value={ru} onChange={e => setRu(e.target.value)}><option>mmol/L</option><option>mg/dL</option></select>
        <input className="input col-span-2 sm:col-span-1" type="datetime-local" aria-label="Measured at" value={rt} onChange={e => setRt(e.target.value)} />
        <select className="input" aria-label="When" value={rc} onChange={e => setRc(e.target.value)}>
          {[['before_meal', 'Before meal'], ['after_meal', 'After meal'], ['fasting', 'Fasting'], ['other', 'Other']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        <button className="btn-ghost" disabled={!(Number(rv) > 0)} onClick={addReading}>Log reading</button>
      </div>}
      <ErrorNote msg={err} />
      {!readOnly && changed.length > 0 && <div className="mt-4 flex gap-2">
        <button className="btn-ghost flex-1" onClick={() => setGrams({})}><RotateCcw className="size-4" />Reset</button>
        <button className="btn-primary flex-1" disabled={busy} onClick={apply}>{busy ? <Spinner className="size-4 text-white" /> : <Check className="size-4" />}Apply {changed.length} portion change(s)</button>
      </div>}
    </Card>
  )
}
