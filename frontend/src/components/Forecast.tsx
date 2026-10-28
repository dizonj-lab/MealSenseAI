import { useEffect, useMemo, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Activity, AlertTriangle, BookOpen, CheckCircle2, Info, Plus, ShieldAlert, Sigma, Trash2, TrendingDown } from 'lucide-react'
import { api, fmt } from '../lib/api'
import { GlucoseEstimateNote, glucoseAxis, yDomain } from '../lib/glucose'
import { Card, Section, Spinner, Tag, Toggle } from './ui'

type Scenario = { activity: string; intensity: 'moderate' | 'high'; start_min: number; duration_min: number }
const COLORS = ['#0d9488', '#6366f1', '#f59e0b']
const PRESETS: { label: string; s: Scenario }[] = [
  { label: 'Walk 15 min, 30 min after', s: { activity: 'brisk_walk', intensity: 'moderate', start_min: 30, duration_min: 15 } },
  { label: 'Cycle 30 min, 45 min after', s: { activity: 'cycling', intensity: 'moderate', start_min: 45, duration_min: 30 } },
  { label: 'Run hard right after', s: { activity: 'running', intensity: 'high', start_min: 5, duration_min: 30 } },
  { label: 'Row 20 min, 2 h after', s: { activity: 'rowing', intensity: 'high', start_min: 120, duration_min: 20 } },
]
const LEVEL: Record<string, [string, JSX.Element]> = {
  warning: ['bg-rose-50 text-rose-800 ring-rose-200', <AlertTriangle key="w" className="size-4 shrink-0 mt-0.5" />],
  caution: ['bg-amber-50 text-amber-800 ring-amber-200', <ShieldAlert key="c" className="size-4 shrink-0 mt-0.5" />],
  info: ['bg-slate-50 text-slate-700 ring-slate-200', <Info key="i" className="size-4 shrink-0 mt-0.5" />],
  good: ['bg-emerald-50 text-emerald-800 ring-emerald-200', <CheckCircle2 key="g" className="size-4 shrink-0 mt-0.5" />],
}
const RATING: Record<string, [string, string]> = {
  balanced: ['Balanced', 'bg-emerald-50 text-emerald-700 ring-emerald-200'],
  needs_attention: ['Needs attention', 'bg-amber-50 text-amber-700 ring-amber-200'],
  unhealthy: ['Unhealthy', 'bg-rose-50 text-rose-700 ring-rose-200'],
}
const hm = (m: number) => `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`

function Cite({ keys, num }: { keys: string[]; num: (k: string) => number }) {
  if (!keys?.length) return null
  return <sup className="ml-0.5 text-brand-700 font-semibold">[{keys.map(num).join(',')}]</sup>
}

function ScenarioRow({ s, i, acts, onChange, onRemove }: { s: Scenario; i: number; acts: any; onChange: (s: Scenario) => void; onRemove: () => void }) {
  const a = acts?.[s.activity]
  return (
    <div className="rounded-xl ring-1 ring-slate-200 p-3 space-y-3">
      <div className="flex items-center gap-2">
        <span className="size-3 rounded-full shrink-0" style={{ background: COLORS[i] }} />
        <select className="input py-2" value={s.activity} onChange={e => onChange({ ...s, activity: e.target.value })} aria-label="Activity">
          {acts && Object.entries(acts).map(([k, v]: any) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <button className="p-2 text-slate-400 hover:text-rose-600" onClick={onRemove} aria-label="Remove scenario"><Trash2 className="size-4" /></button>
      </div>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Toggle options={[['moderate', `Moderate${a ? ` · ${a.moderate_met} MET` : ''}`], ['high', `High${a ? ` · ${a.high_met} MET` : ''}`]]} value={s.intensity} onChange={v => v && onChange({ ...s, intensity: v })} />
      </div>
      <label className="block"><span className="label">Start <b>{s.start_min} min</b> after the meal</span>
        <input type="range" min={0} max={180} step={5} value={s.start_min} onChange={e => onChange({ ...s, start_min: +e.target.value })} className="w-full accent-teal-600" /></label>
      <label className="block"><span className="label">Duration <b>{s.duration_min} min</b></span>
        <input type="range" min={5} max={90} step={5} value={s.duration_min} onChange={e => onChange({ ...s, duration_min: +e.target.value })} className="w-full accent-teal-600" /></label>
    </div>
  )
}

export default function Forecast({ mealId, version }: { mealId: number; version: string }) {
  const [scen, setScen] = useState<Scenario[]>([PRESETS[0].s])
  const [d, setD] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setBusy(true)
      api(`/meals/${mealId}/forecast`, { method: 'POST', json: { scenarios: scen, horizon_min: 300 } })
        .then(r => { setD(r); setErr(null) }).catch(e => setErr(e.message)).finally(() => setBusy(false))
    }, 250)
    return () => clearTimeout(t)
  }, [mealId, version, JSON.stringify(scen)])

  // number citations in order of first appearance
  const order = useMemo(() => {
    if (!d) return [] as string[]
    const keys: string[] = []
    const add = (k: string) => { if (d.references[k] && !keys.includes(k)) keys.push(k) }
    d.advisory.flags.forEach((f: any) => f.refs.forEach(add))
    d.scenarios.forEach((s: any) => s.cautions.forEach((c: any) => c.refs.forEach(add)))
    d.equations.forEach((e: string) => (e.match(/\[([^\]]+)\]/)?.[1] ?? '').split(',').map(x => x.trim()).forEach(add))
    Object.keys(d.references).forEach(add)
    return keys
  }, [d])
  const num = (k: string) => order.indexOf(k) + 1

  if (err) return <Card title="Forecast & what-if"><p className="text-sm text-rose-600">{err}</p></Card>
  if (!d) return <Card title="Forecast & what-if"><div className="py-8 grid place-items-center"><Spinner /></div></Card>

  const ax = glucoseAxis(d.glucose_scale)
  const series = d.time_min.map((t: number, i: number) => {
    const b = d.baseline.glucose_index[i]
    const row: any = { t, base: ax.value(b), band: [ax.low(b), ax.high(b)], baseE: d.baseline.energy_cum_kcal[i] }
    d.scenarios.forEach((s: any, j: number) => { row[`s${j}`] = ax.value(s.glucose_index[i]); row[`e${j}`] = s.energy_cum_kcal[i] })
    return row
  })
  const adv = d.advisory
  const [rLabel, rCls] = RATING[adv.rating]
  const eqText = (e: string) => e.replace(/\s*\[([^\]]+)\]/, (_m, ks) => ` [${ks.split(',').map((k: string) => num(k.trim())).join(',')}]`)

  return (
    <div className="space-y-2.5">
      <Section title="Meal advisory" icon={<ShieldAlert className="size-5 text-amber-500" />} summary={<span className={`chip ring-1 ${rCls}`}>{rLabel}</span>}>
        {adv.flags.length === 0 ? <p className="text-sm text-slate-600">No public-health reference points exceeded for this meal.</p> :
          <ul className="space-y-2">{adv.flags.map((f: any, i: number) => (
            <li key={i} className="flex gap-2 text-sm"><AlertTriangle className={`size-4 mt-0.5 shrink-0 ${f.severity > 1 ? 'text-rose-500' : 'text-amber-500'}`} />
              <span>{f.text}<Cite keys={f.refs} num={num} /></span></li>))}</ul>}
        {adv.tips.length > 0 && <div className="mt-3 rounded-xl bg-emerald-50/60 p-3 text-sm text-emerald-900">
          <div className="font-semibold mb-1">Healthier next time</div><ul className="list-disc pl-5 space-y-0.5">{adv.tips.map((t: string) => <li key={t}>{t}</li>)}</ul></div>}
      </Section>

      <Section title="Forecast & what-if" icon={<Activity className="size-5 text-brand-600" />} tag={busy ? <Spinner className="size-4" /> : <Tag kind="guidance" />} summary="Energy & glucose after the meal, with activity scenarios">
        <p className="text-xs rounded-xl bg-slate-50 ring-1 ring-slate-200 p-3 text-slate-600 flex gap-2"><Info className="size-4 shrink-0" />{d.disclaimer}</p>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
          {[['Meal energy', `${fmt(d.energy.meal_kcal)} kcal`], ['Office desk work', `${fmt(d.energy.sitting_kcal_per_hour)} kcal/h`],
            ['Desk hours to use meal', `${fmt(d.energy.hours_sitting_to_use_meal_energy, 1)} h`], ['Glucose peak (no workout)', `~${d.baseline.peak_time_min} min`]].map(([l, v]) => (
            <div key={l} className="rounded-xl bg-slate-50 py-2.5 px-1"><div className="text-[11px] text-slate-500">{l}</div><div className="font-semibold text-slate-800">{v}</div></div>))}
        </div>
        <p className="mt-2 text-[11px] text-slate-400">Body mass {d.inputs.body_mass_kg} kg ({d.inputs.body_mass_source}) · glycaemic carbohydrate {d.inputs.glycemic_carbs_g} g · {d.inputs.clearance}
          {d.inputs.gi_assumed_for.length > 0 && ` · GI 60 assumed for: ${d.inputs.gi_assumed_for.join(', ')}`}</p>

        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-slate-700">What if I exercise?</h3>
            {scen.length < 3 && <button className="btn-ghost py-1.5 text-xs" onClick={() => setScen([...scen, { activity: 'cycling', intensity: 'moderate', start_min: 30, duration_min: 20 }])}><Plus className="size-3.5" />Add scenario</button>}</div>
          <div className="flex flex-wrap gap-1.5">{PRESETS.map(p => (
            <button key={p.label} className="chip bg-white ring-1 ring-slate-200 text-slate-600 hover:ring-brand-500" onClick={() => setScen(scen.length < 3 ? [...scen, p.s] : [...scen.slice(0, 2), p.s])}>{p.label}</button>))}</div>
          <div className="grid md:grid-cols-3 gap-3">{scen.map((s, i) => (
            <ScenarioRow key={i} s={s} i={i} acts={d.activities} onChange={n => setScen(scen.map((x, j) => (j === i ? n : x)))} onRemove={() => setScen(scen.filter((_, j) => j !== i))} />))}</div>
        </div>

        <h3 className="mt-5 text-sm font-semibold text-slate-700">{ax.title}</h3>
        <GlucoseEstimateNote gs={d.glucose_scale} />
        <div className="h-64 mt-2"><ResponsiveContainer><ComposedChart data={series} margin={{ left: -12, right: 8, top: 8 }}>
          <CartesianGrid stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey="t" tickFormatter={hm} ticks={[0, 60, 120, 180, 240, 300]} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} domain={yDomain(series.flatMap((r: any) => [...r.band, ...d.scenarios.map((_: any, j: number) => r[`s${j}`])]), ax.known, ax.unit)} allowDecimals={ax.unit !== 'mg/dL'} />
          <Tooltip labelFormatter={(t: number) => `${hm(t)} after meal`} formatter={(v: any, n: string) => [Array.isArray(v) ? `${v[0]}–${v[1]} ${ax.unit}` : `${v} ${ax.unit} (estimate)`, n]} />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 11 }} />
          {d.scenarios.map((s: any, j: number) => <ReferenceArea key={j} x1={s.start_min} x2={Math.min(s.start_min + s.duration_min, 300)} fill={COLORS[j]} fillOpacity={0.08} />)}
          <Area dataKey="band" name="Uncertainty range" fill="#94a3b8" fillOpacity={0.15} stroke="none" isAnimationActive={false} />
          <Line dataKey="base" name="Office day (no workout)" stroke="#94a3b8" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          {d.scenarios.map((s: any, j: number) => <Line key={j} dataKey={`s${j}`} name={`Scenario ${j + 1}`} stroke={COLORS[j]} strokeWidth={2.5} dot={false} isAnimationActive={false} />)}
        </ComposedChart></ResponsiveContainer></div>

        <h3 className="mt-4 text-sm font-semibold text-slate-700">Energy used vs meal energy <span className="font-normal text-slate-400">(cumulative kcal)</span></h3>
        <div className="h-52 mt-1"><ResponsiveContainer><LineChart data={series} margin={{ left: -10, right: 8, top: 8 }}>
          <CartesianGrid stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey="t" tickFormatter={hm} ticks={[0, 60, 120, 180, 240, 300]} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={(t: number) => `${hm(t)} after meal`} formatter={(v: number, n: string) => [`${v.toFixed(0)} kcal`, n]} />
          <ReferenceLine y={d.energy.meal_kcal} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: `Meal ${fmt(d.energy.meal_kcal)} kcal`, fontSize: 10, fill: '#e11d48', position: 'insideTopLeft' }} />
          <Line dataKey="baseE" name="Office day" stroke="#94a3b8" strokeDasharray="5 4" strokeWidth={2} dot={false} isAnimationActive={false} />
          {d.scenarios.map((s: any, j: number) => <Line key={j} dataKey={`e${j}`} name={`Scenario ${j + 1}`} stroke={COLORS[j]} strokeWidth={2.5} dot={false} isAnimationActive={false} />)}
        </LineChart></ResponsiveContainer></div>

        <div className="mt-4 space-y-3">{d.scenarios.map((s: any, j: number) => (
          <div key={j} className="rounded-2xl ring-1 ring-slate-200 p-3.5">
            <div className="flex items-center gap-2 font-semibold text-sm text-slate-800"><span className="size-3 rounded-full" style={{ background: COLORS[j] }} />Scenario {j + 1}: {s.name}</div>
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              {[['Peak glucose', `${s.peak_change_pct > 0 ? '+' : ''}${s.peak_change_pct}%`], ['Total excursion (iAUC)', `${s.auc_change_pct > 0 ? '+' : ''}${s.auc_change_pct}%`],
                ['Energy burned', `${fmt(s.exercise_kcal)} kcal`], ['Extra vs desk work', `${fmt(s.net_extra_kcal)} kcal · ${s.share_of_meal_energy_pct ?? '—'}% of meal`]].map(([l, v]) => (
                <div key={l} className="rounded-xl bg-slate-50 py-2 px-1"><div className="text-[11px] text-slate-500">{l}</div><div className="text-sm font-semibold text-slate-800">{v}</div></div>))}
            </div>
            <p className="mt-2 text-xs text-slate-500 flex gap-1"><TrendingDown className="size-3.5 shrink-0 mt-0.5" />Carbohydrate oxidised ≈ {s.cho_oxidised_g} g, of which ≈ {s.meal_glucose_taken_up_g} g is meal glucose cleared by working muscle (the rest from muscle glycogen and liver).</p>
            <ul className="mt-2 space-y-1.5">{s.cautions.map((c: any, i: number) => { const [cls, icon] = LEVEL[c.level] ?? LEVEL.info; return (
              <li key={i} className={`rounded-lg ring-1 px-2.5 py-1.5 text-xs flex gap-2 ${cls}`}>{icon}<span>{c.text}<Cite keys={c.refs} num={num} /></span></li>) })}</ul>
          </div>))}
          {d.scenarios.length === 0 && <p className="text-sm text-slate-500">Add a scenario to compare it with an office day without exercise.</p>}
        </div>

        <div className="mt-4">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Minutes of moderate activity to offset this meal (extra over desk work)</div>
          <div className="flex flex-wrap gap-1.5">{Object.entries(d.energy.minutes_moderate_activity_to_offset_meal).map(([k, v]: any) => (
            <span key={k} className="chip bg-slate-100 text-slate-700">{d.activities[k].label.split(' (')[0]}: <b>{v} min</b></span>))}</div>
        </div>

        <details className="mt-4 rounded-xl bg-slate-50 p-3 text-sm">
          <summary className="cursor-pointer font-semibold text-slate-700 flex items-center gap-2"><Sigma className="size-4" />How it's calculated (physics & physiology)</summary>
          <ul className="mt-2 space-y-1 text-slate-600">{d.equations.map((e: string) => <li key={e} className="font-mono text-[12px]">{eqText(e)}</li>)}</ul>
          <div className="mt-3 font-semibold text-slate-700 text-xs uppercase tracking-wide">Model assumptions</div>
          <ul className="mt-1 list-disc pl-5 space-y-1 text-xs text-slate-600">{d.assumptions.map((a: string) => <li key={a}>{a}</li>)}</ul>
        </details>
        <details className="mt-2 rounded-xl bg-slate-50 p-3 text-sm">
          <summary className="cursor-pointer font-semibold text-slate-700 flex items-center gap-2"><BookOpen className="size-4" />References ({order.length})</summary>
          <ol className="mt-2 space-y-1.5 text-xs text-slate-600 list-decimal pl-5">{order.map(k => { const r = d.references[k]; const href = r.doi ? `https://doi.org/${r.doi}` : r.url; return (
            <li key={k}>{r.cite}{href && <> <a className="text-brand-700 underline break-all" href={href} target="_blank" rel="noreferrer">{r.doi ? `doi:${r.doi}` : 'link'}</a></>}</li>) })}</ol>
        </details>
      </Section>
    </div>
  )
}
