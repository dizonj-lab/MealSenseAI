import { useState } from 'react'
import { AlertTriangle, Check, Droplet, Flame, Info, Lightbulb, Pencil, Plus, Scale, Sparkles, Trash2 } from 'lucide-react'
import { api, fmt } from '../lib/api'
import { useAuthImage } from '../lib/hooks'
import type { Food, Meal } from '../lib/types'
import FoodPicker from './FoodPicker'
import { Card, ErrorNote, LevelBadge, Progress, Spinner } from './ui'

const ORIGIN: Record<string, string> = { model: 'AI recognised', description: 'From description', manual: 'Added by you', slm: 'SLM suggestion' }
const MAPQ: Record<string, [string, string]> = {
  exact: ['Matched', 'bg-emerald-50 text-emerald-700'], fuzzy: ['Approximate match — please confirm', 'bg-amber-50 text-amber-700'],
  provisional: ['Unverified SLM suggestion — confirm', 'bg-amber-50 text-amber-700'], none: ['No nutrition match', 'bg-rose-50 text-rose-700'],
}
const UNC: Record<string, string> = { low: 'text-emerald-700', medium: 'text-amber-700', high: 'text-rose-700', unknown: 'text-slate-500' }

function MealImage({ mealId, view, hasOverlay }: { mealId: number; view: string; hasOverlay: boolean }) {
  const [showMasks, setShowMasks] = useState(hasOverlay)
  const url = useAuthImage(`/api/v1/meals/${mealId}/images/${view}${showMasks ? '_overlay' : ''}`)
  return (
    <figure className="relative rounded-xl overflow-hidden bg-slate-100">
      {url ? <img src={url} className="w-full h-auto block" alt={`${view} view`} /> : <div className="aspect-[4/3] grid place-items-center"><Spinner /></div>}
      <figcaption className="absolute bottom-2 left-2 chip bg-black/50 text-white capitalize">{view === 'top' ? 'Top view' : 'Side view'}</figcaption>
      {hasOverlay && <button onClick={() => setShowMasks(m => !m)} className="absolute bottom-2 right-2 chip bg-white/90 text-slate-700 shadow">{showMasks ? 'Hide' : 'Show'} detections</button>}
    </figure>
  )
}

function FoodCard({ f, meal, onChange, readOnly }: { f: Food; meal: Meal; onChange: (m: Meal) => void; readOnly: boolean }) {
  const [picker, setPicker] = useState(false)
  const [editG, setEditG] = useState(false)
  const [g, setG] = useState(String(f.grams))
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const call = async (p: Promise<Meal>) => { setBusy(true); setErr(null); try { onChange(await p) } catch (e: any) { setErr(e.message) } finally { setBusy(false) } }
  const put = (json: object) => call(api(`/meals/${meal.id}/foods/${f.id}`, { method: 'PUT', json }))
  const pred = f.original_prediction
  const [mq, mqc] = MAPQ[f.mapping_quality] ?? MAPQ.none
  const n = f.nutrients
  return (
    <div className={`card p-4 ${f.confirmed ? 'ring-1 ring-emerald-200' : ''}`}>
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="font-semibold text-slate-900">{f.label}</h3>
            {f.confirmed && <span className="chip bg-emerald-50 text-emerald-700"><Check className="size-3" />Confirmed</span>}
            {f.user_corrected && <span className="chip bg-sky-50 text-sky-700">Corrected</span>}
          </div>
          <div className="mt-1 flex flex-wrap gap-1.5 text-xs">
            <span className="chip bg-slate-100 text-slate-600">{ORIGIN[f.origin]}</span>
            <span className={`chip ${mqc}`}>{mq}</span>
          </div>
        </div>
        {busy && <Spinner className="size-4" />}
      </div>

      {pred?.model_label && <div className="mt-3 text-xs rounded-lg bg-slate-50 px-3 py-2 text-slate-600 space-y-0.5">
        <div><b>{pred.model_name}</b> predicted “{pred.model_label}” · {pred.score_band} signal (raw score {pred.score.toFixed(2)}, uncalibrated){pred.views?.length > 1 && ' · seen in both views'}</div>
        {pred.instance && <div className="text-slate-500">Instance: {pred.instance === 'scene' ? 'whole image' : `${pred.detector_label} (${pred.has_mask ? 'mask' : 'box'}, ${(pred.area_frac * 100).toFixed(0)}% of photo)`}{pred.instances > 1 && ` · ×${pred.instances}`}</div>}
        {pred.classifier_top?.length > 0 && <div className="text-slate-500">Classifier top-3: {pred.classifier_top.map((t: any) => `${t.label} ${t.score.toFixed(2)}`).join(', ')}</div>}
      </div>}
      {pred?.description_text && <div className="mt-3 text-xs rounded-lg bg-slate-50 px-3 py-2 text-slate-600">From your description: “{pred.description_text}” ({pred.parser})</div>}

      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        {[['Portion', `${fmt(f.grams)} g`], ['Calories', `${fmt(n.calories_kcal)}`], ['Carbs', `${fmt(n.carbs_g, 1)} g`], ['Protein', `${fmt(n.protein_g, 1)} g`]].map(([l, v]) => (
          <div key={l} className="rounded-xl bg-slate-50 py-2"><div className="text-[11px] text-slate-500">{l}</div><div className="font-semibold text-slate-800">{v}</div></div>))}
      </div>
      <div className="mt-2 text-xs text-slate-500 flex flex-wrap gap-x-3 gap-y-1">
        <span>Fat {fmt(n.fat_g, 1)} g</span><span>Sugar {fmt(n.sugar_g, 1)} g</span><span>Fibre {fmt(n.fiber_g, 1)} g</span><span>Sodium {fmt(n.sodium_mg)} mg</span>
      </div>
      <div className="mt-2 text-xs">
        <span className={`font-semibold ${UNC[f.portion.uncertainty] ?? ''}`}><Scale className="inline size-3.5 -mt-0.5" /> Portion uncertainty: {f.portion.uncertainty}{f.portion.relative_error && ` (${f.portion.relative_error})`}</span>
        {f.portion.range_g && <span className="text-slate-500"> · likely {f.portion.range_g[0]}–{f.portion.range_g[1]} g</span>}
        <details className="text-slate-500 mt-1"><summary className="cursor-pointer">How was this estimated?</summary>
          <ul className="list-disc pl-4 mt-1 space-y-0.5">{f.portion.notes.map((x, i) => <li key={i}>{x}</li>)}</ul>
          {f.nutrition_source && <p className="mt-1">Nutrition: {f.nutrition_source.source} — record “{f.nutrition_source.name}” ({f.nutrition_source.verification.replace('_', ' ')}).</p>}
        </details>
      </div>

      {editG && <div className="mt-3 flex gap-2">
        <input className="input" type="number" inputMode="decimal" value={g} onChange={e => setG(e.target.value)} autoFocus />
        <button className="btn-primary" onClick={() => { put({ grams: Number(g) }); setEditG(false) }} disabled={!(Number(g) > 0)}>Save</button>
        <button className="btn-ghost" onClick={() => setEditG(false)}>Cancel</button></div>}
      <ErrorNote msg={err} />

      {!readOnly && <div className="mt-3 grid grid-cols-4 gap-1.5">
        <button className="btn-ghost px-2 text-xs" disabled={f.confirmed || !f.nutrition_key} onClick={() => put({ confirmed: true })}><Check className="size-4" />Confirm</button>
        <button className="btn-ghost px-2 text-xs" onClick={() => setPicker(true)}><Pencil className="size-4" />Food</button>
        <button className="btn-ghost px-2 text-xs" disabled={!f.nutrition_key} onClick={() => { setG(String(f.grams)); setEditG(true) }}><Scale className="size-4" />Portion</button>
        <button className="btn-ghost px-2 text-xs text-rose-600" onClick={() => call(api(`/meals/${meal.id}/foods/${f.id}`, { method: 'DELETE' }))}><Trash2 className="size-4" />Remove</button>
      </div>}
      {picker && <FoodPicker title={`Correct “${f.label}”`} initial={f.nutrition_key ? '' : f.label} onClose={() => setPicker(false)}
        onPick={(ref, grams) => { setPicker(false); put({ nutrition_key: ref.key, ...(grams ? { grams } : {}) }) }} />}
    </div>
  )
}

export function InsightCards({ meal }: { meal: Meal }) {
  const ins = meal.insights
  if (!ins?.glucose) return null
  const g = ins.glucose, e = ins.energy
  return (
    <div className="space-y-4">
      {ins.allergy_warnings.length > 0 && <div className="rounded-2xl bg-rose-50 ring-1 ring-rose-200 p-4 text-sm text-rose-800">
        <div className="font-semibold flex items-center gap-2 mb-1"><AlertTriangle className="size-4" />Allergy check</div>
        <ul className="list-disc pl-5">{ins.allergy_warnings.map(w => <li key={w}>{w}</li>)}</ul></div>}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Potential Glucose Impact" icon={<Droplet className="size-5 text-sky-600" />} action={<LevelBadge level={g.level} />}>
          <div className="grid grid-cols-3 gap-2 text-center mb-3">
            {[['Carbs', g.carbs_g, 'g'], ['Sugar', g.sugar_g, 'g'], ['Fibre', g.fiber_g, 'g']].map(([l, v, u]) => (
              <div key={l as string} className="rounded-xl bg-sky-50/60 py-2"><div className="text-[11px] text-slate-500">{l}</div><div className="font-bold text-slate-800">{fmt(v as number, 1)}<span className="text-xs font-normal text-slate-400"> {u}</span></div></div>))}
          </div>
          <div className="text-sm text-slate-600 mb-2">Estimated glycemic load: <b>{g.glycemic_load ?? 'not estimated'}</b></div>
          <ul className="text-sm text-slate-600 space-y-1.5 list-disc pl-4">{g.reasoning.map((r, i) => <li key={i}>{r}</li>)}</ul>
          <p className="mt-3 text-[11px] text-slate-400 flex gap-1"><Info className="size-3.5 shrink-0" />{g.disclaimer}</p>
        </Card>
        <Card title="Energy & Nutrition" icon={<Flame className="size-5 text-amber-500" />}>
          <div className="text-3xl font-bold text-slate-900">{fmt(e.calories_kcal)}<span className="text-sm font-medium text-slate-400"> kcal</span></div>
          <div className="mt-3 flex h-3 rounded-full overflow-hidden bg-slate-100">
            <div className="bg-sky-500" style={{ width: `${e.macro_energy_pct.carbs ?? 0}%` }} />
            <div className="bg-emerald-500" style={{ width: `${e.macro_energy_pct.protein ?? 0}%` }} />
            <div className="bg-amber-400" style={{ width: `${e.macro_energy_pct.fat ?? 0}%` }} />
          </div>
          <div className="mt-2 grid grid-cols-3 text-xs text-slate-600">
            <span><i className="inline-block size-2 rounded-full bg-sky-500 mr-1" />Carbs {fmt(e.carbs_g)} g</span>
            <span><i className="inline-block size-2 rounded-full bg-emerald-500 mr-1" />Protein {fmt(e.protein_g)} g</span>
            <span><i className="inline-block size-2 rounded-full bg-amber-400 mr-1" />Fat {fmt(e.fat_g)} g</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">Fibre {fmt(e.fiber_g, 1)} g · Sodium {fmt(e.sodium_mg)} mg</div>
          {e.goal_progress.length > 0 && <div className="mt-4 space-y-2.5">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Share of your daily goals</div>
            {e.goal_progress.map(gp => <div key={gp.label}><div className="flex justify-between text-xs mb-1"><span>{gp.label}</span><span className="text-slate-500">{fmt(gp.value)} / {fmt(gp.goal)} {gp.unit} · {gp.pct}%</span></div><Progress pct={gp.pct} /></div>)}
          </div>}
          {e.notes.map(n => <p key={n} className="mt-3 text-xs text-slate-500">{n}</p>)}
        </Card>
        <Card title="Practical Recommendations" icon={<Lightbulb className="size-5 text-emerald-600" />}>
          <ul className="space-y-3">{ins.recommendations.map(r => (
            <li key={r.tag} className="flex gap-3"><span className="mt-0.5 size-6 shrink-0 rounded-lg bg-emerald-50 text-emerald-700 grid place-items-center"><Check className="size-3.5" /></span>
              <div><div className="text-sm font-semibold text-slate-800">{r.title}</div><div className="text-sm text-slate-600">{r.detail}</div></div></li>))}</ul>
          <p className="mt-3 text-[11px] text-slate-400">General educational guidance; not a treatment plan.</p>
        </Card>
      </div>
      <div className="card p-4 text-sm flex gap-3">
        <Sparkles className="size-5 text-brand-600 shrink-0" />
        {ins.explanation.text ? <div><p className="text-slate-700">{ins.explanation.text}</p><p className="text-[11px] text-slate-400 mt-1">Generated by local SLM ({ins.explanation.source.replace('slm:', '')}) from the numbers above.</p></div>
          : <p className="text-slate-500">Local SLM is offline — insights above come from the deterministic rule engine using food-composition data.</p>}
      </div>
    </div>
  )
}

export default function MealReview({ meal, onChange, onSaved, readOnly = false }: { meal: Meal; onChange: (m: Meal) => void; onSaved?: (m: Meal) => void; readOnly?: boolean }) {
  const [adding, setAdding] = useState(false)
  const [mealType, setMealType] = useState(meal.meal_type ?? guessMealType())
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const active = meal.foods.filter(f => !f.removed)
  const t = meal.totals
  const save = async () => {
    setSaving(true); setErr(null)
    try { const m = await api<Meal>(`/meals/${meal.id}/confirm`, { method: 'PUT', json: { meal_type: mealType } }); onChange(m); onSaved?.(m) } catch (e: any) { setErr(e.message) } finally { setSaving(false) }
  }
  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-4 items-start">
        <div className="space-y-3 lg:sticky lg:top-20">
          {meal.images.length > 0 ? <div className={`grid gap-3 ${meal.images.length > 1 ? 'grid-cols-2 lg:grid-cols-1' : ''}`}>
            {meal.images.map(im => <MealImage key={im.view} mealId={meal.id} view={im.view} hasOverlay={!!im.overlay_path} />)}</div>
            : <div className="card p-4 text-sm text-slate-500">No photo — analysed from description.</div>}
          <div className="card p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Meal total · {t.item_count} item(s) · ~{fmt(t.grams)} g</div>
            <div className="grid grid-cols-4 gap-2 text-center">
              {[['kcal', t.calories_kcal, 0], ['Carbs g', t.carbs_g, 1], ['Protein g', t.protein_g, 1], ['Fat g', t.fat_g, 1]].map(([l, v, d]) => (
                <div key={l as string}><div className="text-lg font-bold text-slate-900">{fmt(v as number, d as number)}</div><div className="text-[11px] text-slate-500">{l}</div></div>))}
            </div>
            {t.unmapped_items?.length > 0 && <p className="mt-2 text-xs text-rose-600">Not counted (no nutrition match): {t.unmapped_items.join(', ')}</p>}
          </div>
        </div>
        <div className="space-y-3">
          {active.length === 0 && <div className="card p-4 text-sm text-slate-600">No foods yet. Use <b>Add missing food</b> to enter what you ate.</div>}
          {active.map(f => <FoodCard key={f.id} f={f} meal={meal} onChange={onChange} readOnly={readOnly} />)}
          {!readOnly && <button className="btn-ghost w-full border-dashed py-3" onClick={() => setAdding(true)}><Plus className="size-4" />Add missing food</button>}
        </div>
      </div>
      <InsightCards meal={meal} />
      {!readOnly && <div className="card p-4 flex flex-col sm:flex-row gap-3 sm:items-center">
        <div className="flex gap-1.5 flex-wrap">{['breakfast', 'lunch', 'dinner', 'snack'].map(m => (
          <button key={m} onClick={() => setMealType(m)} className={`chip px-3 py-1.5 capitalize border ${mealType === m ? 'bg-brand-600 text-white border-brand-600' : 'bg-white border-slate-200 text-slate-600'}`}>{m}</button>))}</div>
        <div className="sm:ml-auto flex-1 sm:flex-none"><ErrorNote msg={err} /></div>
        <button className="btn-primary py-3 sm:px-6" onClick={save} disabled={saving || active.length === 0}>{saving ? <Spinner className="size-4 text-white" /> : <Check className="size-4" />}{meal.status === 'confirmed' ? 'Update saved meal' : 'Confirm & save meal'}</button>
      </div>}
      {adding && <FoodPicker title="Add missing food" onClose={() => setAdding(false)} onPick={async (ref, grams) => {
        setAdding(false)
        try { onChange(await api(`/meals/${meal.id}/foods`, { method: 'POST', json: { nutrition_key: ref.key, ...(grams ? { grams } : {}) } })) } catch (e: any) { setErr(e.message) }
      }} />}
    </div>
  )
}

function guessMealType() {
  const h = new Date().getHours()
  return h < 11 ? 'breakfast' : h < 15 ? 'lunch' : h < 18 ? 'snack' : 'dinner'
}
