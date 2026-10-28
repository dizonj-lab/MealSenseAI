import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Check, Crosshair, MessageCircle, Droplet, Flame, Info, Lightbulb, Merge, Pencil, Plus, RotateCcw, Scale, Search, Sparkles, Trash2, X } from 'lucide-react'
import { api, fmt } from '../lib/api'
import { useAdvisor } from '../lib/advisor'
import { useAuthImage } from '../lib/hooks'
import type { Food, Meal } from '../lib/types'
import FoodPicker from './FoodPicker'
import Forecast from './Forecast'
import MealComposition from './MealComposition'
import PortionSimulator from './PortionSimulator'
import { Card, DetailProvider, DetailSwitch, ErrorNote, InfoTip, LevelBadge, Progress, Section, Spinner, Tag, useDetail } from './ui'

const ORIGIN: Record<string, string> = { model: 'AI recognised', drawn: 'Marked by you, AI recognised', memory: 'Known from your earlier label', description: 'From description', manual: 'Added by you', slm: 'SLM suggestion' }
const MAPQ: Record<string, [string, string]> = {
  exact: ['Nutrition record matched', 'bg-emerald-50 text-emerald-700'], proxy: ['Nutrition approximated by a similar food', 'bg-amber-50 text-amber-700'],
  fuzzy: ['Approximate match — please confirm', 'bg-amber-50 text-amber-700'],
  provisional: ['Unverified SLM suggestion — confirm', 'bg-amber-50 text-amber-700'], none: ['No nutrition match', 'bg-rose-50 text-rose-700'],
}
const UNC: Record<string, string> = { low: 'text-emerald-700', medium: 'text-amber-700', high: 'text-rose-700', unknown: 'text-slate-500' }

export const ITEM_COLORS = ['#0d9488', '#6366f1', '#f59e0b', '#e11d48', '#0284c7', '#16a34a', '#9333ea', '#ea580c', '#0891b2', '#65a30d', '#db2777', '#4f46e5']

type Box = { x: number; y: number; w: number; h: number }
const MIN_BOX = 0.03   // smaller drags are treated as a tap, not a box

/** The meal photo with numbered boxes. In draw mode the user drags a box over a food (mouse, finger or pen: pointer
 *  events, with touch-action none so the drag does not scroll the page). Coordinates are fractions of the photo. */
function MealImage({ mealId, view, items, selected, onSelect, drawing, onDraw, onDrawn, onCancel, options = [], onPick }: { mealId: number; view: string; items: { f: Food; n: number }[]
  options?: Food[]; onPick?: (id: number) => void
  selected: number | null; onSelect: (id: number) => void; drawing: string | null; onDraw?: () => void; onDrawn: (view: string, box: Box) => void; onCancel: () => void }) {
  const [boxes, setBoxes] = useState(true)
  const [drag, setDrag] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null)
  const area = useRef<HTMLDivElement>(null)
  const url = useAuthImage(`/api/v1/meals/${mealId}/images/${view}`)
  const mine = items.filter(({ f }) => f.original_prediction?.bbox && f.original_prediction?.view === view)
  const found = options.filter(f => f.original_prediction?.bbox && f.original_prediction?.view === view)   // regions found but not listed
  const at = (e: React.PointerEvent) => {
    const r = area.current!.getBoundingClientRect()
    return { x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)) }
  }
  const rect = drag && { x: Math.min(drag.x0, drag.x1), y: Math.min(drag.y0, drag.y1), w: Math.abs(drag.x1 - drag.x0), h: Math.abs(drag.y1 - drag.y0) }
  const finish = () => {
    if (rect && rect.w >= MIN_BOX && rect.h >= MIN_BOX) onDrawn(view, { x: +rect.x.toFixed(4), y: +rect.y.toFixed(4), w: +rect.w.toFixed(4), h: +rect.h.toFixed(4) })
    setDrag(null)
  }
  return (<div>
    {drawing && <p className="mb-2 flex items-center gap-2 rounded-xl bg-slate-900 text-white text-sm px-3 py-2">
      <Crosshair className="size-4 shrink-0" /><span className="flex-1">{drawing}{found.length > 0 && onPick ? ', or tap + Add on a dotted outline the app found' : ''}</span></p>}
    <figure ref={area} className={`relative rounded-xl overflow-hidden bg-slate-100 select-none ${drawing ? 'ring-4 ring-brand-500' : ''}`}>
      {url ? <img src={url} className="w-full h-auto block pointer-events-none" alt={`${view} view`} draggable={false} /> : <div className="aspect-[4/3] grid place-items-center"><Spinner /></div>}
      {url && (boxes || drawing) && mine.map(({ f, n }) => { const b = f.original_prediction.bbox; const col = ITEM_COLORS[(n - 1) % ITEM_COLORS.length]; const sel = selected === f.id; return (
        <button key={f.id} onClick={() => onSelect(f.id)} aria-label={`Item ${n}: ${f.label}`} tabIndex={drawing ? -1 : 0}
          className="absolute rounded-md transition" style={{ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%`,
            border: `${sel ? 3 : 2}px ${f.nutrition_key ? 'solid' : 'dashed'} ${col}`, background: sel ? `${col}22` : 'transparent', opacity: drawing ? 0.5 : 1 }}>
          <span className="absolute -top-px -left-px rounded-br-md px-1.5 text-[11px] font-bold text-white" style={{ background: col }}>{n}</span>
        </button>) })}
      {url && drawing && <div data-testid="draw-area" className="absolute inset-0 cursor-crosshair" style={{ touchAction: 'none' }}
        onPointerDown={e => { e.currentTarget.setPointerCapture(e.pointerId); const p = at(e); setDrag({ x0: p.x, y0: p.y, x1: p.x, y1: p.y }) }}
        onPointerMove={e => { if (drag) { const p = at(e); setDrag({ ...drag, x1: p.x, y1: p.y }) } }}
        onPointerUp={finish} onPointerCancel={() => setDrag(null)}>
        {rect && <div className="absolute rounded-md border-2 border-dashed border-white bg-white/15 shadow-[0_0_0_9999px_rgba(15,23,42,0.35)]"
          style={{ left: `${rect.x * 100}%`, top: `${rect.y * 100}%`, width: `${rect.w * 100}%`, height: `${rect.h * 100}%` }} />}
      </div>}
      {url && drawing && onPick && !drag && [...found].sort((p, q) => q.original_prediction.bbox.w * q.original_prediction.bbox.h - p.original_prediction.bbox.w * p.original_prediction.bbox.h)
        .map(f => { const b = f.original_prediction.bbox; const c = f.original_prediction.candidates?.[0]; return (
        // only the tag takes taps, so a drag can still start anywhere on the photo, even over an outline
        <div key={f.id} className="absolute rounded-md border-2 border-dotted border-white shadow-[0_0_0_1px_rgba(15,23,42,0.5)] pointer-events-none"
          style={{ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%` }}>
          <button onClick={() => onPick(f.id)} aria-label={`Add the region the app found${c ? `, maybe ${c.label}` : ''}`}
            className="pointer-events-auto absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full shadow bg-white/95 hover:bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-700 flex items-center gap-0.5"><Plus className="size-3" />Add</button>
        </div>) })}
      <figcaption className="absolute bottom-2 left-2 chip bg-black/50 text-white capitalize pointer-events-none">{view === 'top' ? 'Top view' : 'Side view'}</figcaption>
      <div className="absolute bottom-2 right-2 z-20 flex gap-1.5">
        {drawing ? <button onClick={onCancel} className="chip bg-white/95 text-slate-700 shadow"><X className="size-3.5" />Cancel</button> : <>
          {onDraw && url && <button onClick={onDraw} className="chip bg-white/95 text-brand-700 shadow"><Crosshair className="size-3.5" />Mark a food</button>}
          {mine.length > 0 && <button onClick={() => setBoxes(v => !v)} className="chip bg-white/90 text-slate-700 shadow">{boxes ? 'Hide' : 'Show'} boxes</button>}</>}
      </div>
    </figure></div>
  )
}

function FoodCard({ f, n, meal, onChange, readOnly, selected, onSelect, mergeChecked, onMergeToggle, onMark }: { f: Food; n: number; meal: Meal; onChange: (m: Meal) => void; readOnly: boolean; selected: boolean; onSelect: () => void; mergeChecked: boolean; onMergeToggle: () => void; onMark?: () => void }) {
  const [picker, setPicker] = useState(false)
  const [editG, setEditG] = useState(false)
  const [g, setG] = useState(String(f.grams))
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const call = async (p: Promise<Meal>) => { setBusy(true); setErr(null); try { onChange(await p) } catch (e: any) { setErr(e.message) } finally { setBusy(false) } }
  const put = (json: object) => call(api(`/meals/${meal.id}/foods/${f.id}`, { method: 'PUT', json }))
  const pred = f.original_prediction
  const [mq, mqc] = MAPQ[f.mapping_quality] ?? MAPQ.none
  const nu = f.nutrients
  const unknown = !f.nutrition_key && pred?.kind && pred.kind !== 'food'
  const col = ITEM_COLORS[(n - 1) % ITEM_COLORS.length]
  const { detailed } = useDetail()
  const [why, setWhy] = useState<boolean | null>(null)
  useEffect(() => setWhy(null), [detailed])
  const open = why ?? detailed
  return (
    <div id={`food-${f.id}`} onClick={onSelect} className={`card p-4 transition ${selected ? 'ring-2' : f.confirmed ? 'ring-1 ring-emerald-200' : unknown ? 'ring-1 ring-amber-300' : ''}`} style={selected ? { boxShadow: `0 0 0 2px ${col}` } : undefined}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 size-7 shrink-0 rounded-lg grid place-items-center text-sm font-bold text-white" style={{ background: col }} title={`Item ID ${f.id}`}>{n}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="font-semibold text-slate-900">{f.label}</h3>
            {unknown && <span className="chip bg-amber-50 text-amber-800">Not recognised — please name it</span>}
            {!unknown && !f.confirmed && pred?.needs_review && <span className="chip bg-amber-50 text-amber-700">Needs your check</span>}
            {open && pred?.score !== undefined && pred?.kind === 'food' && <span className="chip bg-violet-50 text-violet-700" title="Raw softmax score, not a calibrated probability">model {(pred.score * 100).toFixed(0)}% (raw)</span>}
            {f.confirmed && <span className="chip bg-emerald-50 text-emerald-700"><Check className="size-3" />Confirmed</span>}
            {pred?.memory && !f.user_corrected && <span className="chip bg-violet-50 text-violet-700" title={`Looks like the item you named “${pred.memory.label}” before (similarity ${pred.memory.similarity})`}>Known from your earlier label</span>}
            {open && f.nutrition_source?.match === 'proxy' && <span className="chip bg-amber-50 text-amber-700">≈ {f.nutrition_source.name}</span>}
            {open && f.user_corrected && <span className="chip bg-sky-50 text-sky-700">Corrected</span>}
          </div>
          {!unknown && <p className="mt-0.5 text-sm text-slate-600 tabular-nums">{fmt(f.grams)} g · {fmt(nu.calories_kcal)} kcal · {fmt(nu.carbs_g, 0)} g carbs · {fmt(nu.sugar_g, 0)} g sugar
            {f.portion.range_g && <span className="text-slate-400"> (≈{f.portion.range_g[0]}–{f.portion.range_g[1]} g)</span>}</p>}
          {open && <div className="mt-1 flex flex-wrap gap-1.5 text-xs">
            <span className="chip bg-slate-100 text-slate-600">{ORIGIN[f.origin]}</span>
            <span className={`chip ${mqc}`}>{mq}</span>
          </div>}
        </div>
        {busy && <Spinner className="size-4" />}
        {!readOnly && <label className="flex items-center gap-1 text-[11px] text-slate-500" onClick={e => e.stopPropagation()}>
          <input type="checkbox" className="accent-teal-600" checked={mergeChecked} onChange={onMergeToggle} />merge
          <InfoTip label="Merge" align="right" text="Tick this on two or more cards that are really the same food (the detector sometimes splits one food into pieces), then tap “Merge … into one” above the cards. Portions are added together." /></label>}
      </div>

      {(open || unknown) && pred?.candidates?.length > 0 && <div className="mt-3 rounded-xl bg-violet-50/40 ring-1 ring-violet-100 px-3 py-2.5">
        <div className="flex items-center gap-2 text-xs text-slate-600 mb-2"><Tag kind="prediction" />
          <span>{unknown ? 'Best guesses for this region (all weak):' : pred.memory ? `Matched your earlier label “${pred.memory.label}” (fingerprint similarity ${pred.memory.similarity}). The model on its own suggested:` : `${pred.model_name} · ${pred.instance === 'whole photo' ? 'whole photo' : 'region ' + (pred.region_id ?? '')}`}</span></div>
        <div className="grid gap-1.5">{pred.candidates.map((c: any, i: number) => {
          const sel = (f.taxonomy_class ?? f.label) === c.label
          return (
            <button key={c.class_id} disabled={readOnly || busy || sel} onClick={e => { e.stopPropagation(); put({ candidate_class_id: c.class_id }) }}
              className={`relative overflow-hidden rounded-lg px-3 py-2 text-left text-sm ring-1 transition ${sel ? 'ring-violet-400 bg-white font-semibold' : 'ring-slate-200 bg-white/70 hover:ring-violet-300'}`}>
              <span className="absolute inset-y-0 left-0 bg-violet-100" style={{ width: `${Math.max(c.score * 100, 1)}%` }} />
              <span className="relative flex justify-between gap-2"><span>{i + 1}. {c.label}{c.match === 'none' && <span className="text-[11px] text-rose-600"> · no nutrition record</span>}</span>
                <span className="text-slate-500 tabular-nums">{(c.score * 100).toFixed(1)}%</span></span>
            </button>) })}</div>
        <p className="mt-1.5 text-[11px] text-slate-500">Tap a candidate to change the food. Percentages are raw model scores, not calibrated probabilities.</p>
      </div>}
      {open && pred?.description_text && <div className="mt-3 text-xs rounded-lg bg-slate-50 px-3 py-2 text-slate-600">From your description: “{pred.description_text}” ({pred.parser})</div>}

      {open && !unknown && <><div className="mt-3 grid grid-cols-3 sm:grid-cols-7 gap-1.5 text-center">
        {[['Portion', `${fmt(f.grams)} g`], ['kcal', fmt(nu.calories_kcal)], ['Carbs', `${fmt(nu.carbs_g, 1)} g`], ['Sugar', `${fmt(nu.sugar_g, 1)} g`],
          ['Protein', `${fmt(nu.protein_g, 1)} g`], ['Fat', `${fmt(nu.fat_g, 1)} g`], ['Sodium', `${fmt(nu.sodium_mg)} mg`]].map(([l, v]) => (
          <div key={l} className="rounded-xl bg-slate-50 py-1.5"><div className="text-[10px] text-slate-500">{l}</div><div className="text-sm font-semibold text-slate-800">{v}</div></div>))}
      </div>
      <div className="mt-2 text-xs text-slate-500 flex flex-wrap items-center gap-x-3 gap-y-1">
        <Tag kind={f.portion.method === 'user_entered' ? 'measured' : 'estimate'} />
        <span>Fibre {fmt(nu.fiber_g, 1)} g</span><span>Sat. fat {nu.sat_fat_g == null ? 'n/a' : `${fmt(nu.sat_fat_g, 1)} g`}</span>
      </div></>}
      {open && !unknown && <div className="mt-2 text-xs">
        <span className={`font-semibold ${UNC[f.portion.uncertainty] ?? ''}`}><Scale className="inline size-3.5 -mt-0.5" /> Portion uncertainty: {f.portion.uncertainty}{f.portion.relative_error && ` (${f.portion.relative_error})`}</span>
        {f.portion.range_g && <span className="text-slate-500"> · likely {f.portion.range_g[0]}–{f.portion.range_g[1]} g</span>}
        <details className="text-slate-500 mt-1"><summary className="cursor-pointer">How was this estimated?</summary>
          <ul className="list-disc pl-4 mt-1 space-y-0.5">{f.portion.notes.map((x, i) => <li key={i}>{x}</li>)}</ul>
          {f.nutrition_source && <p className="mt-1">Nutrition estimate from “{f.nutrition_source.name}”{f.nutrition_source.match === 'proxy' && ' (closest available food — correct it if you know better)'}. Source: {f.nutrition_source.source} ({f.nutrition_source.verification.replace(/_/g, ' ')}).</p>}
        </details>
      </div>}

      {editG && <div className="mt-3 flex gap-2">
        <input className="input" type="number" inputMode="decimal" value={g} onChange={e => setG(e.target.value)} autoFocus />
        <button className="btn-primary" onClick={() => { put({ grams: Number(g) }); setEditG(false) }} disabled={!(Number(g) > 0)}>Save</button>
        <button className="btn-ghost" onClick={() => setEditG(false)}>Cancel</button></div>}
      <ErrorNote msg={err} />

      <button onClick={e => { e.stopPropagation(); setWhy(!open) }} aria-expanded={open}
        className="mt-2 text-xs font-semibold text-brand-700 flex items-center gap-1"><Info className="size-3.5" />{open ? 'Hide details' : 'Why? Show how this was estimated'}</button>
      {!readOnly && <div className="mt-3 grid grid-cols-4 gap-1.5" onClick={e => e.stopPropagation()}>
        <button className="btn-ghost px-2 text-xs" disabled={f.confirmed || !f.nutrition_key} onClick={() => put({ confirmed: true })}><Check className="size-4" />Confirm</button>
        <button className="btn-ghost px-2 text-xs" onClick={() => setPicker(true)}><Pencil className="size-4" />{unknown ? 'Name it' : 'Rename'}</button>
        <button className="btn-ghost px-2 text-xs" disabled={!f.nutrition_key} onClick={() => { setG(String(f.grams)); setEditG(true) }}><Scale className="size-4" />Portion</button>
        <button className="btn-ghost px-2 text-xs text-rose-600" onClick={() => call(api(`/meals/${meal.id}/foods/${f.id}`, { method: 'DELETE' }))}><Trash2 className="size-4" />Remove</button>
      </div>}
      {!readOnly && onMark && !pred?.bbox && <button className="mt-2 w-full btn-ghost py-2 text-xs text-brand-700" onClick={e => { e.stopPropagation(); onMark() }}>
        <Crosshair className="size-4" />Show where it is on the photo</button>}
      {!readOnly && n === 1 && <p className="mt-1.5 text-[11px] text-slate-400 flex items-center gap-1">What do these buttons do?
        <InfoTip label="Card actions" text={<><b>Confirm</b>: the food and portion look right. <b>Rename</b>/<b>Name it</b>: pick the correct food or create your own. <b>Portion</b>: enter the grams you ate. <b>Remove</b>: not part of this meal. Each change recalculates the totals and is remembered for next time.</>} /></p>}
      {picker && <FoodPicker title={unknown ? `What is item ${n}?` : `Rename “${f.label}”`} initial={unknown ? '' : f.nutrition_key ? '' : f.label} onClose={() => setPicker(false)}
        onPick={(ref, grams) => { setPicker(false); put({ nutrition_key: ref.key, ...(grams ? { grams } : {}) }) }} />}
    </div>
  )
}

export function InsightCards({ meal, onChange }: { meal: Meal; onChange?: (m: Meal) => void }) {
  const ins = meal.insights
  const pending = ins?.explanation?.source === 'pending'
  useEffect(() => {  // the local SLM writes its explanation after results are shown, so it never delays analysis
    if (pending && onChange) api<Meal>(`/meals/${meal.id}/explain`, { method: 'POST' }).then(onChange).catch(() => {})
  }, [pending, meal.id])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!ins?.glucose) return null
  const g = ins.glucose, e = ins.energy
  return (
    <div className="space-y-2.5">
      {ins.allergy_warnings.length > 0 && <div className="rounded-2xl bg-rose-50 ring-1 ring-rose-200 p-4 text-sm text-rose-800">
        <div className="font-semibold flex items-center gap-2 mb-1"><AlertTriangle className="size-4" />Allergy check</div>
        <ul className="list-disc pl-5">{ins.allergy_warnings.map(w => <li key={w}>{w}</li>)}</ul></div>}
      <Section title="Key takeaways" icon={<Sparkles className="size-5 text-brand-600" />} tag={<Tag kind="estimate" />}
        summary={<span className="inline-flex items-center gap-1.5">Glucose impact <LevelBadge level={g.level} />{ins.recommendations[0] && <span className="hidden sm:inline">· {ins.recommendations[0].title}</span>}</span>}>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-700"><Droplet className="size-4 text-sky-600" />Potential glucose impact <LevelBadge level={g.level} />
          {g.glycemic_load != null && <span className="text-slate-500">· glycaemic load {g.glycemic_load}</span>}</div>
        <ul className="mt-3 space-y-1.5">{ins.recommendations.slice(0, 2).map(r => <li key={r.tag} className="flex gap-2 text-sm text-slate-700"><Check className="size-4 mt-0.5 shrink-0 text-emerald-600" />{r.title}</li>)}
          {ins.personalised?.[0] && <li className="flex gap-2 text-sm text-slate-700"><Lightbulb className="size-4 mt-0.5 shrink-0 text-violet-600" /><span><b className="font-semibold">{ins.personalised[0].audience}:</b> {ins.personalised[0].title}</span></li>}</ul>
        <div className="mt-3 border-t border-slate-100 pt-3 text-sm">
          {pending ? <p className="text-slate-500 flex items-center gap-2"><Spinner className="size-4" />Local SLM is writing a plain-language explanation of these numbers…</p>
            : ins.explanation.text ? <div><p className="text-slate-700">{ins.explanation.text}</p><p className="text-[11px] text-slate-400 mt-1">Generated by local SLM ({ins.explanation.source.replace('slm:', '')}) from the numbers above{(ins.explanation as any).latency_ms ? ` in ${((ins.explanation as any).latency_ms / 1000).toFixed(1)} s` : ''}.</p></div>
            : <p className="text-xs text-slate-500">Local SLM offline — these insights come from the rule engine using food-composition data.</p>}
        </div>
      </Section>
      <Section title="Glucose, energy & tips" summary={`${ins.recommendations.length} tip(s) · reasoning & goals`}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Potential Glucose Impact" icon={<Droplet className="size-5 text-sky-600" />} action={<span className="flex gap-1.5"><Tag kind="estimate" /><LevelBadge level={g.level} /></span>}>
          <div className="grid grid-cols-3 gap-2 text-center mb-3">
            {[['Carbs', g.carbs_g, 'g'], ['Sugar', g.sugar_g, 'g'], ['Fibre', g.fiber_g, 'g']].map(([l, v, u]) => (
              <div key={l as string} className="rounded-xl bg-sky-50/60 py-2"><div className="text-[11px] text-slate-500">{l}</div><div className="font-bold text-slate-800">{fmt(v as number, 1)}<span className="text-xs font-normal text-slate-400"> {u}</span></div></div>))}
          </div>
          <div className="text-sm text-slate-600 mb-2">Estimated glycemic load: <b>{g.glycemic_load ?? 'not estimated'}</b></div>
          <ul className="text-sm text-slate-600 space-y-1.5 list-disc pl-4">{g.reasoning.map((r, i) => <li key={i}>{r}</li>)}</ul>
          <p className="mt-3 text-[11px] text-slate-400 flex gap-1"><Info className="size-3.5 shrink-0" />{g.disclaimer}</p>
        </Card>
        <Card title="Energy & Nutrition" icon={<Flame className="size-5 text-amber-500" />} action={<Tag kind="estimate" />}>
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
        <Card title="Practical Recommendations" icon={<Lightbulb className="size-5 text-emerald-600" />} action={<Tag kind="guidance" />}>
          <ul className="space-y-3">{ins.recommendations.map(r => (
            <li key={r.tag} className="flex gap-3"><span className="mt-0.5 size-6 shrink-0 rounded-lg bg-emerald-50 text-emerald-700 grid place-items-center"><Check className="size-3.5" /></span>
              <div><div className="text-sm font-semibold text-slate-800">{r.title}</div><div className="text-sm text-slate-600">{r.detail}</div></div></li>))}</ul>
          <p className="mt-3 text-[11px] text-slate-400">General educational guidance; not a treatment plan.</p>
        </Card>
      </div>
      </Section>
      {!!ins.personalised?.length && <Section title="Personalised for you" icon={<Sparkles className="size-5 text-violet-600" />} tag={<Tag kind="guidance" />} summary={ins.personalised.map(p => p.audience).join(' · ')}>
        <div className="grid sm:grid-cols-2 gap-3">{ins.personalised!.map(p => <div key={p.audience} className="rounded-xl bg-violet-50/50 ring-1 ring-violet-100 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">{p.audience}</div>
          <div className="text-sm font-semibold text-slate-800">{p.title}</div><p className="text-sm text-slate-600">{p.detail}</p>
          <p className="text-[11px] text-slate-400 mt-1">Basis: {p.basis}</p></div>)}</div>
      </Section>}
    </div>
  )
}

type ReviewProps = { meal: Meal; onChange: (m: Meal) => void; onSaved?: (m: Meal) => void; readOnly?: boolean }
export default function MealReview(props: ReviewProps) {
  return <DetailProvider><Review {...props} /></DetailProvider>
}

function Review({ meal, onChange, onSaved, readOnly = false }: ReviewProps) {
  const advisor = useAdvisor()
  useEffect(() => { advisor.setContextMeal(meal.id); return () => advisor.setContextMeal(null) }, [meal.id])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {   // the Meal Advisor can add a missed food; keep this page in sync
    const on = (e: Event) => { const m = (e as CustomEvent).detail; if (m?.id === meal.id) onChange(m) }
    window.addEventListener('mealsense-meal-updated', on)
    return () => window.removeEventListener('mealsense-meal-updated', on)
  }, [meal.id, onChange])
  const [adding, setAdding] = useState(false)
  // draw mode: a new food (food = null) or where an existing food is; the hint is shown over the photo
  const [drawing, setDrawing] = useState<{ food: number | null; hint: string } | null>(null)
  const [marking, setMarking] = useState(false)
  const [mealType, setMealType] = useState(meal.meal_type ?? guessMealType())
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)
  const [mergeIds, setMergeIds] = useState<number[]>([])
  const active = meal.foods.filter(f => !f.removed)
  const items = active.map((f, i) => ({ f, n: i + 1 }))
  const suggestions = meal.foods.filter(f => f.removed && f.original_prediction?.kind === 'suggestion' && !f.user_corrected)
  const select = (id: number) => { setSelected(id); document.getElementById(`food-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }
  const act = async (p: Promise<Meal>) => { setErr(null); try { onChange(await p) } catch (e: any) { setErr(e.message) } }
  const drawn = async (view: string, bbox: Box) => {
    const target = drawing
    setDrawing(null); setMarking(true); setErr(null)
    try {
      const before = new Set(meal.foods.map(f => f.id))
      const m = await api<Meal>(target?.food ? `/meals/${meal.id}/foods/${target.food}/region` : `/meals/${meal.id}/regions`,
        { method: target?.food ? 'PUT' : 'POST', json: { view, bbox } })
      onChange(m)
      const id = target?.food ?? m.foods.find(f => !before.has(f.id))?.id
      if (id) setTimeout(() => select(id), 50)
    } catch (e: any) { setErr(e.message) } finally { setMarking(false) }
  }
  const pick = (id: number) => {   // a region the detector found but did not list: add it, then name it
    setDrawing(null)
    act(api(`/meals/${meal.id}/foods/${id}`, { method: 'PUT', json: { restore: true } }))
    setTimeout(() => select(id), 300)
  }
  const startDraw = (food: number | null = null, label?: string) => {
    setDrawing({ food, hint: food ? `Drag a box around ${label} on the photo` : 'Drag a box around the food the app missed' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const merge = () => act(api<Meal>(`/meals/${meal.id}/foods/merge`, { method: 'POST', json: { food_ids: mergeIds } })).then(() => setMergeIds([]))
  const nUnknown = active.filter(f => !f.nutrition_key).length
  const cls = meal.stages.find(st => st.key === 'classify')
  const uncertain = cls?.status === 'uncertain' && !active.some(f => f.origin === 'model') ? (cls.per_view?.[0]?.top_labels ?? []) : []
  const t = meal.totals
  const save = async () => {
    setSaving(true); setErr(null)
    try { const m = await api<Meal>(`/meals/${meal.id}/confirm`, { method: 'PUT', json: { meal_type: mealType } }); onChange(m); onSaved?.(m) } catch (e: any) { setErr(e.message) } finally { setSaving(false) }
  }
  return (
    <div className="space-y-4">
      {!readOnly && <div className="sticky top-14 md:top-16 z-20 -mx-3 sm:mx-0 px-3 sm:px-4 py-2.5 bg-white/95 backdrop-blur border-b sm:border sm:rounded-2xl border-slate-200 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex gap-1 overflow-x-auto no-scrollbar min-w-0" role="group" aria-label="Meal type">{['breakfast', 'lunch', 'dinner', 'snack'].map(m => (
            <button key={m} onClick={() => setMealType(m)} aria-pressed={mealType === m}
              className={`chip shrink-0 px-2.5 py-1.5 capitalize border ${mealType === m ? 'bg-brand-600 text-white border-brand-600' : 'bg-white border-slate-200 text-slate-600'}`}>{m}</button>))}</div>
          <InfoTip label="Meal type and save" align="right" text={<>Pick the meal type, then <b>Save</b> to add this meal to your history and daily totals. Every item needs a name first; you can still edit a saved meal later.</>} />
          <button className="btn-primary ml-auto shrink-0 px-3.5 py-2" onClick={save} disabled={saving || active.length === 0}>
            {saving ? <Spinner className="size-4 text-white" /> : <Check className="size-4" />}{meal.status === 'confirmed' ? 'Update' : 'Save meal'}</button>
        </div>
        {(err || nUnknown > 0) && <div className="mt-2 text-xs">{err ? <ErrorNote msg={err} /> : <span className="text-amber-700">{nUnknown} item(s) need a name before saving.</span>}</div>}
      </div>}
      <div className="flex items-center justify-between gap-2"><span className="text-xs text-slate-500 flex items-center gap-1">Details are one tap away on every card.
        <InfoTip label="Simple and detailed view" text="Simple shows the essentials. Detailed opens every section and card: model guesses with raw scores, nutrients, portion ranges and sources. Your choice is remembered on this device." /></span><DetailSwitch /></div>
      <div className="grid lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-4 items-start">
        <div className="space-y-3 lg:sticky lg:top-36">
          {meal.images.length > 0 ? <div className={`grid gap-3 ${meal.images.length > 1 ? 'grid-cols-2 lg:grid-cols-1' : ''}`}>
            {meal.images.map(im => <MealImage key={im.view} mealId={meal.id} view={im.view} items={items} selected={selected} onSelect={select}
              drawing={drawing?.hint ?? null} onDraw={readOnly ? undefined : () => startDraw()} onDrawn={drawn} onCancel={() => setDrawing(null)}
              options={suggestions} onPick={drawing?.food ? undefined : pick} />)}</div>
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
          {!readOnly && uncertain.length > 0 && <div className="card p-4 ring-1 ring-amber-200">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Tag kind="prediction" />Not sure what this is — is it one of these?</div>
            <div className="mt-2 flex flex-wrap gap-1.5">{uncertain.map((c: any) => (
              <button key={c.class_id} className="chip ring-1 ring-slate-200 bg-white px-3 py-1.5 text-sm hover:ring-violet-300"
                onClick={async () => { try { onChange(await api(`/meals/${meal.id}/foods`, { method: 'POST', json: { candidate_class_id: c.class_id } })) } catch (e: any) { setErr(e.message) } }}>
                {c.label} <span className="text-slate-400">{(c.score * 100).toFixed(0)}%</span></button>))}</div>
            <p className="mt-1.5 text-[11px] text-slate-500">Low model confidence. Otherwise use “Add missing food”.</p>
          </div>}
          {active.length === 0 && <div className="card p-4 text-sm text-slate-600">No foods yet. Use <b>Add missing food</b> to enter what you ate.</div>}
          {active.length > 1 && <div className="text-sm text-slate-600 flex flex-wrap items-center gap-2">
            <b>{active.length} items</b>{nUnknown > 0 && <span className="chip bg-amber-50 text-amber-800">{nUnknown} need a name before saving</span>}
            {!readOnly && mergeIds.length >= 2 && <button className="btn-ghost ml-auto px-3 py-1.5 text-xs" onClick={merge}><Merge className="size-4" />Merge {mergeIds.length} items into one</button>}
          </div>}
          {items.map(({ f, n }) => <FoodCard key={f.id} f={f} n={n} meal={meal} onChange={onChange} readOnly={readOnly} selected={selected === f.id} onSelect={() => setSelected(f.id)}
            mergeChecked={mergeIds.includes(f.id)} onMergeToggle={() => setMergeIds(m => m.includes(f.id) ? m.filter(x => x !== f.id) : [...m, f.id])}
            onMark={meal.images.length > 0 ? () => startDraw(f.id, f.label) : undefined} />)}
          {!readOnly && suggestions.length > 0 && <div className="card p-4">
            <div className="text-sm font-semibold text-slate-800 flex items-center gap-1">Possible additional items ({suggestions.length})
              <InfoTip label="Possible additional items" text="Small or uncertain regions the detector found. They are not counted unless you tap one to add it, then name it. Mark it on the photo shows them as dotted outlines you can tap." /></div>
            <p className="text-[11px] text-slate-500 mb-2">Small or weak regions the detector found. Not counted unless you add them.</p>
            <div className="flex flex-wrap gap-1.5">{suggestions.map(f => (
              <button key={f.id} className="chip ring-1 ring-slate-200 bg-white px-3 py-1.5 text-sm hover:ring-teal-300" onClick={() => act(api(`/meals/${meal.id}/foods/${f.id}`, { method: 'PUT', json: { restore: true } }))}>
                <RotateCcw className="size-3.5" />Add region {f.original_prediction.region_id}{f.original_prediction.candidates?.[0] && <span className="text-slate-400"> (maybe {f.original_prediction.candidates[0].label})</span>}</button>))}</div>
          </div>}
          {!readOnly && (meal.images.length > 0 ? <div className="card p-3 border border-dashed border-slate-300">
            <div className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-2"><Plus className="size-4" />Add missing food
              <InfoTip label="Add missing food" text="Mark it on the photo: drag a box around the food (mouse, finger or pen). The model names what is inside the box and estimates the portion from its size; you can correct both. Or search the food list if it is not in the photo." /></div>
            <div className="grid sm:grid-cols-2 gap-2">
              <button className="btn-primary py-2.5" disabled={marking} onClick={() => startDraw()}>{marking ? <Spinner className="size-4 text-white" /> : <Crosshair className="size-4" />}Mark it on the photo</button>
              <button className="btn-ghost py-2.5" onClick={() => setAdding(true)}><Search className="size-4" />Search the food list</button></div></div>
            : <button className="btn-ghost w-full border-dashed py-3" onClick={() => setAdding(true)}><Plus className="size-4" />Add missing food</button>)}
        </div>
      </div>
      <div className="space-y-2.5">
      <h3 className="pt-2 text-sm font-semibold text-slate-500 flex items-center gap-1">Insights
        <InfoTip label="Insights" text="Each row shows its key point; tap it to open. Detailed view opens them all. Allergy warnings are always shown." /></h3>
      <InsightCards meal={meal} onChange={onChange} />
      <Section title="Ask the Meal Advisor" icon={<MessageCircle className="size-5 text-brand-600" />} summary="Suggested questions about this meal">
        <div className="flex flex-wrap gap-1.5">{['Is this meal OK for my goal?', 'Which food adds the most carbs?', 'Suggest a lower-carb swap for this meal'].map(q => (
          <button key={q} onClick={() => advisor.openAdvisor({ prompt: q, mealId: meal.id })} className="chip bg-brand-50 text-brand-700 px-3 py-1.5">{q}</button>))}</div>
      </Section>
      <MealComposition meal={meal} items={items} colors={ITEM_COLORS} />
      <PortionSimulator meal={meal} onChange={onChange} readOnly={readOnly} />
      {(meal.totals?.calories_kcal ?? 0) > 0 && <Forecast mealId={meal.id} version={meal.insights?.generated_at ?? ''} />}
      </div>
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
