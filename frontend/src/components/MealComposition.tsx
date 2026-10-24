import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt } from '../lib/api'
import type { Food, Meal } from '../lib/types'
import { Section, Tag } from './ui'

const TIP = { fontSize: 11, whiteSpace: 'normal' as const }
const TIP_WRAP = { maxWidth: '65%', zIndex: 5 }
const N: [keyof Food['nutrients'], string, string][] = [
  ['calories_kcal', 'Calories', 'kcal'], ['carbs_g', 'Carbs', 'g'], ['sugar_g', 'Sugar', 'g'], ['protein_g', 'Protein', 'g'],
  ['fat_g', 'Fat', 'g'], ['sat_fat_g', 'Sat. fat', 'g'], ['fiber_g', 'Fibre', 'g'], ['sodium_mg', 'Sodium', 'mg']]

/** Meal composition dashboard. Values come only from mapped nutrition records; missing values are shown as missing. */
export default function MealComposition({ meal, items, colors }: { meal: Meal; items: { f: Food; n: number }[]; colors: string[] }) {
  const t = meal.totals
  const mapped = items.filter(({ f }) => f.nutrition_key)
  if (!mapped.length) return null
  const name = (f: Food, n: number) => `${n}. ${f.label}`.slice(0, 22)
  const col = (n: number) => colors[(n - 1) % colors.length]
  // one row per food; carbs split into sugar / fibre / other carbs (sugar & fibre are subsets of total carbohydrate)
  const rows = mapped.map(({ f, n }) => {
    const c = f.nutrients.carbs_g ?? 0, s = f.nutrients.sugar_g ?? 0, fb = f.nutrients.fiber_g ?? 0
    return { name: name(f, n), n, sugar: s, fibre: fb, other: Math.max(c - s - fb, 0), kcal: f.nutrients.calories_kcal ?? 0,
      carbs: c, protein: f.nutrients.protein_g ?? 0, fat: f.nutrients.fat_g ?? 0,
      gi: f.nutrition_source?.glycemic_index ?? null as number | null }
  }).map(r => ({ ...r, gl: r.gi == null ? null : Math.round(r.gi * (r.carbs - r.fibre) / 10) / 10 }))
  const glRows = rows.filter(r => r.gl != null)
  const noGi = rows.filter(r => r.gi == null && r.carbs >= 5).map(r => r.name)
  const kc = { carbs: (t.carbs_g ?? 0) * 4, protein: (t.protein_g ?? 0) * 4, fat: (t.fat_g ?? 0) * 9 }
  const kcSum = kc.carbs + kc.protein + kc.fat
  const macro = [['Carbs', kc.carbs, '#0ea5e9'], ['Protein', kc.protein, '#10b981'], ['Fat', kc.fat, '#f59e0b']].map(([k, v, c]) => ({ k, v: Math.round(v as number), c }))
  const kcalPie = rows.filter(r => r.kcal > 0)
  const h = Math.max(140, rows.length * 34 + 40)
  // a nutrient is incomplete only when a matched food lacks it (unnamed items are reported separately)
  const missing = new Set(N.map(x => x[0]).filter(k => mapped.some(({ f }) => f.nutrients[k] == null)))
  return (
    <Section title="Meal composition" tag={<Tag kind="estimate" />} summary={`${fmt(t.calories_kcal)} kcal · ${fmt(t.carbs_g)} g carbs · charts by food`}>
      <div className="grid grid-cols-4 sm:grid-cols-8 gap-2 text-center">
        {N.map(([k, l, u]) => <div key={k} className="rounded-xl bg-slate-50 py-2">
          <div className="text-[10px] text-slate-500">{l}</div>
          <div className="font-bold text-slate-900">{t[k] == null ? '—' : fmt(t[k] as number, u === 'g' ? 1 : 0)}<span className="text-[10px] font-normal text-slate-400"> {u}</span></div>
          {missing.has(k) && t[k] != null && <div className="text-[9px] text-amber-700">incomplete</div>}
        </div>)}
      </div>
      {(missing.size > 0 || t.unmapped_items?.length > 0) && <p className="mt-2 text-xs text-amber-700">
        {missing.size > 0 && <>Missing values are not filled in: {[...missing].map(k => N.find(x => x[0] === k)?.[1] ?? k).join(', ')} {missing.size > 1 ? 'are sums' : 'is the sum'} over only the foods that have a value.  </>}
        {t.unmapped_items?.length > 0 && <>Not counted: {t.unmapped_items.join(', ')}.</>}</p>}
      <div className="mt-4 grid md:grid-cols-2 gap-5">
        <div><h4 className="text-sm font-semibold text-slate-700 mb-1">Carbohydrate contribution by food (g)</h4>
          <ResponsiveContainer width="100%" height={h}><BarChart data={rows} layout="vertical" margin={{ left: 4, right: 12 }}>
            <CartesianGrid horizontal={false} stroke="#e2e8f0" /><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="name" width={110} fontSize={11} />
            <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: number) => `${v.toFixed(1)} g`} /><Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="sugar" stackId="c" name="Sugar" fill="#f43f5e" /><Bar dataKey="other" stackId="c" name="Other carbs (starch)" fill="#0ea5e9" />
            <Bar dataKey="fibre" stackId="c" name="Fibre" fill="#84cc16" radius={[0, 4, 4, 0]} />
          </BarChart></ResponsiveContainer></div>
        <div><h4 className="text-sm font-semibold text-slate-700 mb-1">Calorie contribution by food</h4>
          <ResponsiveContainer width="100%" height={220}><PieChart>
            <Pie data={kcalPie} dataKey="kcal" nameKey="name" innerRadius={45} outerRadius={80} label={({ percent }) => `${Math.round(percent * 100)}%`} fontSize={11}>
              {kcalPie.map(r => <Cell key={r.n} fill={col(r.n)} />)}</Pie>
            <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: number) => `${Math.round(v)} kcal`} /><Legend wrapperStyle={{ fontSize: 11 }} />
          </PieChart></ResponsiveContainer></div>
        <div><h4 className="text-sm font-semibold text-slate-700 mb-1">Macronutrient energy distribution</h4>
          {kcSum > 0 ? <ResponsiveContainer width="100%" height={200}><PieChart>
            <Pie data={macro} dataKey="v" nameKey="k" outerRadius={75} label={({ percent }) => `${Math.round(percent * 100)}%`} fontSize={11}>
              {macro.map(m => <Cell key={m.k as string} fill={m.c as string} />)}</Pie>
            <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: number) => `${v} kcal`} /><Legend wrapperStyle={{ fontSize: 11 }} />
          </PieChart></ResponsiveContainer> : <p className="text-sm text-slate-500">No macronutrient data.</p>}
          <p className="text-[11px] text-slate-400">Atwater factors 4/4/9 kcal per g.</p></div>
        <div><h4 className="text-sm font-semibold text-slate-700 mb-1">Food-by-food comparison (g)</h4>
          <ResponsiveContainer width="100%" height={h}><BarChart data={rows} layout="vertical" margin={{ left: 4, right: 12 }}>
            <CartesianGrid horizontal={false} stroke="#e2e8f0" /><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="name" width={110} fontSize={11} />
            <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: number) => `${v.toFixed(1)} g`} /><Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="carbs" name="Carbs" fill="#0ea5e9" /><Bar dataKey="protein" name="Protein" fill="#10b981" /><Bar dataKey="fat" name="Fat" fill="#f59e0b" />
          </BarChart></ResponsiveContainer></div>
        <div className="md:col-span-2"><h4 className="text-sm font-semibold text-slate-700 mb-1">Glycaemic load by food</h4>
          {glRows.length ? <ResponsiveContainer width="100%" height={Math.max(110, glRows.length * 30 + 40)}><BarChart data={glRows} layout="vertical" margin={{ left: 4, right: 12 }}>
            <CartesianGrid horizontal={false} stroke="#e2e8f0" /><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="name" width={110} fontSize={11} />
            <Tooltip wrapperStyle={TIP_WRAP} contentStyle={TIP} formatter={(v: number, _n, p: any) => [`GL ${v} (GI ${p.payload.gi})`, 'Glycaemic load']} />
            <Bar dataKey="gl" name="Glycaemic load" radius={[0, 4, 4, 0]}>{glRows.map(r => <Cell key={r.n} fill={col(r.n)} />)}</Bar>
          </BarChart></ResponsiveContainer> : <p className="text-sm text-slate-500">No food in this meal has a GI value in the table.</p>}
          <p className="text-[11px] text-slate-400">GL = GI × available carbohydrate (carbs − fibre) ÷ 100; meal GL ≤10 low, 11–19 medium, ≥20 high (Atkinson et al. 2021).
            {noGi.length > 0 && ` No GI value, so not included: ${noGi.join(', ')}.`}</p></div>
      </div>
    </Section>
  )
}
