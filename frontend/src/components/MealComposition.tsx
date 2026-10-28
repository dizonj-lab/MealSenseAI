import { useState } from 'react'
import { fmt } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { Food, Meal } from '../lib/types'
import { InfoTip, Section, Tag } from './ui'

// One hue (the brand teal) in tints, like the glucose chart; amber only when a meal goes past its share of a limit.
const TEAL = { 700: '#0f766e', 600: '#0d9488', 400: '#2dd4bf', 300: '#5eead4', 200: '#99f6e4' }
const FIBRE = '#a3e635'
const MEAL_SHARE = 1 / 3   // one of three main meals: the tick on each bar
const SODIUM_LIMIT_MG = 2000     // WHO adult upper limit
const FIBRE_GUIDE_G = 25         // common general guideline (25–30 g/day)

type Meter = { key: string; label: string; value: number | null; unit: string; ref: number | null; refNote: string; limit: boolean; missing?: boolean; d: number }

function MeterRow({ m }: { m: Meter }) {
  if (m.missing) return (
    <div><div className="flex justify-between text-sm"><span className="font-semibold text-slate-800">{m.label}</span><span className="text-xs text-slate-400">not in the food table for this meal</span></div>
      <div className="mt-1.5 h-2.5 rounded-full" style={{ background: 'repeating-linear-gradient(45deg, var(--color-slate-100) 0 6px, transparent 6px 12px)' }} /></div>)
  const pct = m.ref && m.value != null ? (100 * m.value) / m.ref : null
  const over = m.limit && pct != null && pct > MEAL_SHARE * 100
  return (
    <div>
      <div className="flex justify-between gap-2 text-sm"><span className="font-semibold text-slate-800">{m.label}</span>
        <span className="text-xs text-slate-500 tabular-nums text-right">{fmt(m.value, m.d)} {pct != null ? <>of {fmt(m.ref, 0)} {m.unit} · {fmt(pct, 0)}%</> : m.unit}</span></div>
      {pct != null ? <div className="relative mt-1.5 h-2.5 rounded-full bg-slate-100" role="img" aria-label={`${m.label}: ${fmt(pct, 0)}% of ${m.refNote}`}>
        <div className="h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%`, background: over ? 'linear-gradient(90deg,#fcd34d,#d97706)' : `linear-gradient(90deg,${TEAL[300]},${TEAL[600]})` }} />
        <i className="absolute -top-[3px] h-4 w-0.5 rounded bg-slate-400" style={{ left: `${MEAL_SHARE * 100}%` }} title="One meal's share of the day" /></div>
        : <div className="mt-1.5 h-2.5 rounded-full bg-slate-100" />}
      <div className={`mt-1 text-[11px] ${over ? 'text-amber-700' : 'text-slate-400'}`}>{over ? `More than one meal's share of ${m.refNote}` : m.refNote}</div>
    </div>
  )
}

/** Meal composition: what the meal amounts to, where its energy comes from, how it compares with the day, what its
 *  carbohydrate is made of and, for meals with several foods, which food contributes what. Values come only from
 *  mapped nutrition records; missing values are shown as missing, never filled in. */
export default function MealComposition({ meal, items, colors }: { meal: Meal; items: { f: Food; n: number }[]; colors: string[] }) {
  const { user } = useAuth()
  const [metric, setMetric] = useState<'carbs' | 'kcal' | 'sodium'>('carbs')
  const t = meal.totals
  const mapped = items.filter(({ f }) => f.nutrition_key)
  if (!mapped.length) return null
  const g = user?.profile ?? null
  const col = (n: number) => colors[(n - 1) % colors.length]
  const missing = new Set((['sat_fat_g', 'sugar_g', 'fiber_g', 'sodium_mg'] as const).filter(k => mapped.some(({ f }) => f.nutrients[k] == null)))

  // energy split (Atwater 4/4/9)
  const kc = [['Carbs', (t.carbs_g ?? 0) * 4, TEAL[700], '#fff'], ['Protein', (t.protein_g ?? 0) * 4, TEAL[400], '#134e4a'], ['Fat', (t.fat_g ?? 0) * 9, TEAL[200], '#134e4a']] as const
  const kcSum = kc.reduce((s, x) => s + x[1], 0)
  // carbohydrate anatomy: sugar and fibre are parts of total carbohydrate
  const carbs = t.carbs_g ?? 0, sugar = Math.min(t.sugar_g ?? 0, carbs), fibre = Math.min(t.fiber_g ?? 0, carbs - sugar)
  const starch = Math.max(carbs - sugar - fibre, 0)
  const rows = mapped.map(({ f, n }) => {
    const c = f.nutrients.carbs_g ?? 0, fb = f.nutrients.fiber_g ?? 0, gi = f.nutrition_source?.glycemic_index ?? null
    return { n, label: f.label, carbs: c, kcal: f.nutrients.calories_kcal ?? 0, sodium: f.nutrients.sodium_mg ?? null,
      gl: gi == null ? null : Math.round(gi * (c - fb) / 10) / 10 }
  })
  const gl = rows.filter(r => r.gl != null)
  const calGoal = g?.calorie_goal ?? null
  const satRef = ((calGoal ?? 2000) * 0.10) / 9   // under 10% of energy
  const meters: Meter[] = [
    { key: 'carbs', label: 'Carbohydrate', value: t.carbs_g, unit: 'g', ref: g?.carb_goal_g ?? null, refNote: g?.carb_goal_g ? 'your daily goal' : 'no daily goal set (Health Profile)', limit: true, d: 1 },
    { key: 'sodium', label: 'Sodium', value: t.sodium_mg, unit: 'mg', ref: SODIUM_LIMIT_MG, refNote: 'the WHO daily limit', limit: true, missing: missing.has('sodium_mg') && t.sodium_mg == null, d: 0 },
    { key: 'protein', label: 'Protein', value: t.protein_g, unit: 'g', ref: g?.protein_goal_g ?? null, refNote: g?.protein_goal_g ? 'your daily goal' : 'no daily goal set (Health Profile)', limit: false, d: 1 },
    { key: 'fibre', label: 'Fibre', value: t.fiber_g, unit: 'g', ref: FIBRE_GUIDE_G, refNote: 'a common daily guideline (25–30 g)', limit: false, missing: missing.has('fiber_g') && t.fiber_g == null, d: 1 },
    { key: 'sat', label: 'Saturated fat', value: t.sat_fat_g ?? null, unit: 'g', ref: Math.round(satRef), refNote: `under 10% of ${calGoal ? 'your' : 'a 2,000 kcal'} day's energy`, limit: true, missing: missing.has('sat_fat_g'), d: 1 },
  ]
  const metricOf = (r: typeof rows[number]) => (metric === 'carbs' ? r.carbs : metric === 'kcal' ? r.kcal : r.sodium ?? 0)
  const top = Math.max(1, ...rows.map(metricOf))
  const unit = metric === 'carbs' ? 'g carbs' : metric === 'kcal' ? 'kcal' : 'mg sodium'

  return (
    <Section title="Meal composition" tag={<Tag kind="estimate" />} summary={`${fmt(t.calories_kcal)} kcal · ${fmt(t.carbs_g)} g carbs`}>
      <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
        <div><div className="leading-none"><span className="text-4xl font-bold tracking-tight text-slate-900 tabular-nums">{fmt(t.calories_kcal)}</span>
          <span className="ml-1 text-slate-500">kcal</span></div>
          {calGoal && t.calories_kcal != null && <div className="mt-1 text-xs text-slate-500">{fmt((100 * t.calories_kcal) / calGoal, 0)}% of your {fmt(calGoal)} kcal day</div>}</div>
        <dl className="flex flex-wrap gap-x-6 gap-y-2 sm:ml-auto">{([['carbs', t.carbs_g, 'g', 1], ['protein', t.protein_g, 'g', 1], ['fat', t.fat_g, 'g', 1], ['fibre', t.fiber_g, 'g', 1], ['sodium', t.sodium_mg, 'mg', 0]] as const).map(([l, v, u, d]) => (
          <div key={l} className="text-right"><dd className="text-lg font-semibold text-slate-800 tabular-nums">{fmt(v, d)}<span className="text-xs font-normal text-slate-400"> {u}</span></dd><dt className="text-xs text-slate-500">{l}</dt></div>))}</dl>
      </div>
      {(missing.size > 0 || t.unmapped_items?.length > 0) && <p className="mt-2 text-xs text-amber-700">
        {missing.size > 0 && <>Some foods have no value for {[...missing].map(k => ({ sat_fat_g: 'saturated fat', sugar_g: 'sugar', fiber_g: 'fibre', sodium_mg: 'sodium' })[k]).join(', ')}; totals count only the foods that do. </>}
        {t.unmapped_items?.length > 0 && <>Not counted: {t.unmapped_items.join(', ')}.</>}</p>}

      <h4 className="mt-5 mb-2 text-sm font-semibold text-slate-700 flex items-center gap-1">Where the energy comes from
        <InfoTip label="Energy split" text="Energy from each macronutrient, with Atwater factors: 4 kcal per g of carbohydrate and protein, 9 per g of fat." /></h4>
      {kcSum > 0 ? <div className="flex h-9 rounded-xl overflow-hidden text-xs font-semibold" role="img" aria-label={kc.map(([l, v]) => `${l} ${Math.round((100 * v) / kcSum)}%`).join(', ')}>
        {kc.map(([l, v, bg, fg]) => { const p = (100 * v) / kcSum; return p > 0 && (
          <div key={l} className="flex items-center px-3 whitespace-nowrap overflow-hidden" style={{ width: `${p}%`, background: bg, color: fg }} title={`${l} ${Math.round(p)}%`}>
            <span className="hidden sm:inline">{p >= 14 ? `${l} ${Math.round(p)}%` : p >= 6 ? `${Math.round(p)}%` : ''}</span>
            <span className="sm:hidden">{p >= 24 ? `${l} ${Math.round(p)}%` : p >= 9 ? `${Math.round(p)}%` : ''}</span></div>) })}</div>
        : <p className="text-sm text-slate-500">No macronutrient data.</p>}
      {kcSum > 0 && <div className="mt-1.5 flex flex-wrap gap-x-4 text-xs text-slate-500">{kc.map(([l, v, bg]) => <span key={l}>
        <i className="inline-block size-2.5 rounded-full mr-1.5 align-[-1px]" style={{ background: bg }} />{l} {Math.round((100 * v) / kcSum)}% · {Math.round(v)} kcal</span>)}</div>}

      <h4 className="mt-5 mb-2 text-sm font-semibold text-slate-700 flex items-center gap-1">This meal against your day
        <InfoTip label="Against your day" text="Each bar is this meal's share of a daily amount: your own goals from the Health Profile, the WHO sodium limit, a general fibre guideline, and under 10% of energy from saturated fat. The tick marks one meal's share (a third of the day). Amber means the meal alone goes past that share of a limit." /></h4>
      <div className="grid sm:grid-cols-2 gap-x-8 gap-y-3.5">{meters.map(m => <MeterRow key={m.key} m={m} />)}</div>

      {carbs > 0 && <>
        <h4 className="mt-5 mb-2 text-sm font-semibold text-slate-700">Inside the carbohydrate</h4>
        <div className="flex h-3.5 rounded-full overflow-hidden" role="img" aria-label={`Sugar ${fmt(sugar, 1)} g, starch ${fmt(starch, 1)} g, fibre ${fmt(fibre, 1)} g`}>
          <div style={{ width: `${(100 * sugar) / carbs}%`, background: TEAL[300] }} /><div style={{ width: `${(100 * starch) / carbs}%`, background: TEAL[700] }} />
          <div style={{ width: `${(100 * fibre) / carbs}%`, background: FIBRE }} /></div>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          {[['Sugar', sugar, TEAL[300]], ['Starch', starch, TEAL[700]], ['Fibre', fibre, FIBRE]].map(([l, v, c]) => <span key={l as string}>
            <i className="inline-block size-2.5 rounded-full mr-1.5 align-[-1px]" style={{ background: c as string }} />{l} {fmt(v as number, 1)} g</span>)}
          <span className="text-slate-400">· Glycaemic load {gl.length ? gl.map(r => `${r.label} ${r.gl}`).join(', ') : `not available (no GI value in the table for ${rows.map(r => r.label).join(', ')})`}</span></div>
      </>}

      {rows.length > 1 && <>
        <div className="mt-5 mb-2 flex flex-wrap items-center gap-2"><h4 className="text-sm font-semibold text-slate-700">Food by food</h4>
          <div className="ml-auto inline-flex rounded-lg bg-slate-100 p-0.5 text-xs font-semibold" role="group" aria-label="Compare by">
            {([['carbs', 'Carbs'], ['kcal', 'kcal'], ['sodium', 'Sodium']] as const).map(([k, l]) => <button key={k} onClick={() => setMetric(k)} aria-pressed={metric === k}
              className={`rounded-md px-2.5 py-1 ${metric === k ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}>{l}</button>)}</div></div>
        <ul className="space-y-2">{rows.map(r => (
          <li key={r.n} className="grid grid-cols-[minmax(0,9rem)_1fr_auto] sm:grid-cols-[minmax(0,12rem)_1fr_auto] items-center gap-3 text-sm">
            <span className="truncate"><i className="inline-block size-2.5 rounded-full mr-2 align-[-1px]" style={{ background: col(r.n) }} />{r.n}. {r.label}</span>
            <div className="h-3 rounded-full bg-slate-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${(100 * metricOf(r)) / top}%`, background: col(r.n) }} /></div>
            <span className="tabular-nums text-slate-600 text-right">{metric === 'sodium' && r.sodium == null ? '—' : fmt(metricOf(r), metric === 'carbs' ? 1 : 0)} <span className="text-xs text-slate-400">{unit}</span></span></li>))}</ul>
        <p className="mt-1 text-[11px] text-slate-400">Colours match the boxes on the photo.</p>
      </>}
    </Section>
  )
}
