import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Camera, ImagePlus, Loader2, RefreshCw, Sparkles, X } from 'lucide-react'
import { api } from '../lib/api'
import type { Meal, Stage } from '../lib/types'
import MealReview from '../components/MealReview'
import PipelineDrawer from '../components/PipelineDrawer'
import { Card, ErrorNote } from '../components/ui'

const REFS: [string, string][] = [['none', 'None'], ['dinner_plate', 'Dinner plate'], ['rice_bowl', 'Rice bowl'], ['credit_card', 'Credit card'], ['hand', 'Hand']]

function PhotoSlot({ label, hint, file, onFile }: { label: string; hint: string; file: File | null; onFile: (f: File | null) => void }) {
  const cam = useRef<HTMLInputElement>(null), gal = useRef<HTMLInputElement>(null)
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => { if (!file) { setUrl(null); return } const u = URL.createObjectURL(file); setUrl(u); return () => URL.revokeObjectURL(u) }, [file])
  const pick = (e: React.ChangeEvent<HTMLInputElement>) => { onFile(e.target.files?.[0] ?? null); e.target.value = '' }
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5"><span className="text-sm font-semibold text-slate-700">{label}</span><span className="text-xs text-slate-400">{hint}</span></div>
      <div className="relative aspect-[4/3] rounded-2xl overflow-hidden border-2 border-dashed border-slate-200 bg-slate-50">
        {url ? <>
          <img src={url} className="absolute inset-0 size-full object-cover" alt={label} />
          <div className="absolute top-2 right-2 flex gap-1.5">
            <button onClick={() => gal.current?.click()} className="size-9 rounded-full bg-white/90 grid place-items-center shadow" title="Replace"><RefreshCw className="size-4" /></button>
            <button onClick={() => onFile(null)} className="size-9 rounded-full bg-white/90 grid place-items-center shadow" title="Remove"><X className="size-4" /></button>
          </div></> :
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-3">
            <button onClick={() => cam.current?.click()} className="btn-primary w-full max-w-[200px]"><Camera className="size-4" />Take photo</button>
            <button onClick={() => gal.current?.click()} className="btn-ghost w-full max-w-[200px]"><ImagePlus className="size-4" />Upload</button>
          </div>}
      </div>
      <input ref={cam} type="file" accept="image/*" capture="environment" hidden onChange={pick} />
      <input ref={gal} type="file" accept="image/*" hidden onChange={pick} />
    </div>
  )
}

export default function Capture() {
  const nav = useNavigate()
  const [top, setTop] = useState<File | null>(null)
  const [side, setSide] = useState<File | null>(null)
  const [desc, setDesc] = useState('')
  const [ref, setRef] = useState('none')
  const [note, setNote] = useState('')
  const [meal, setMeal] = useState<Meal | null>(null)
  const [stages, setStages] = useState<Stage[]>([])
  const [current, setCurrent] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const reviewRef = useRef<HTMLDivElement>(null)

  const analyze = async () => {
    setErr(null); setMeal(null); setStages([]); setCurrent('capture'); setElapsed(0)
    let timer: number | undefined
    const t0 = performance.now()
    const tick = window.setInterval(() => setElapsed(performance.now() - t0), 100)
    try {
      const fd = new FormData()
      if (top) fd.append('top', top)
      if (side) fd.append('side', side)
      if (desc.trim()) fd.append('description', desc.trim())
      if (ref !== 'none') fd.append('reference_object', ref)
      if (note.trim()) fd.append('serving_note', note.trim())
      const captured = await api<Meal>('/meals/capture', { method: 'POST', body: fd })
      setStages(captured.stages); setCurrent('detect')
      // stages 3–10 run server-side in one request; poll the live stage list the server records as each step finishes
      timer = window.setInterval(() => api<any>(`/meals/${captured.id}/progress`).then(p => { if (p.current) { setStages(p.stages); setCurrent(p.current) } }).catch(() => {}), 400)
      const analyzed = await api<Meal>('/meals/analyze', { method: 'POST', json: { meal_id: captured.id } })
      setStages(analyzed.stages); setMeal(analyzed)
      setTimeout(() => reviewRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (e: any) { setErr(e.message) } finally { clearInterval(timer); clearInterval(tick); setCurrent(null) }
  }
  const reset = () => { setTop(null); setSide(null); setDesc(''); setNote(''); setRef('none'); setMeal(null); setStages([]) }
  const busy = current !== null
  const ready = !!top || !!side || !!desc.trim()

  return (
    <div className="space-y-4">
      {!meal && <Card title="Capture your meal" icon={<Camera className="size-5 text-brand-600" />}>
        <div className="grid grid-cols-2 gap-3">
          <PhotoSlot label="Top view" hint="from above" file={top} onFile={setTop} />
          <PhotoSlot label="Side view" hint="optional" file={side} onFile={setSide} />
        </div>
        <p className="text-xs text-slate-400 mt-2">One photo is fine. A side view helps you review, but photos alone can't measure volume — you can correct portions after analysis.</p>
        <div className="mt-4 space-y-3">
          <label className="block"><span className="label">Describe the food <span className="text-slate-400 font-normal">(optional, improves results)</span></span>
            <input className="input" placeholder="e.g. chicken rice and kopi" value={desc} onChange={e => setDesc(e.target.value)} /></label>
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block"><span className="label">Reference object in photo</span>
              <select className="input" value={ref} onChange={e => setRef(e.target.value)}>{REFS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
            <label className="block"><span className="label">Serving size note</span><input className="input" placeholder="e.g. half plate, 2 pieces, large" value={note} onChange={e => setNote(e.target.value)} /></label>
          </div>
        </div>
        <div className="mt-4"><ErrorNote msg={err} /></div>
        <button className="btn-primary w-full mt-4 py-3.5 text-base tracking-wide" disabled={!ready || busy} onClick={analyze}>
          {busy ? <Loader2 className="size-5 animate-spin" /> : <Sparkles className="size-5" />}ANALYZE MEAL</button>
      </Card>}

      {(busy || stages.length > 0) && <div className="space-y-2">
        <PipelineDrawer stages={stages} current={current} elapsedMs={elapsed} meal={meal} />
        {meal && <button className="btn-ghost w-full py-2 text-sm" onClick={reset}><Camera className="size-4" />New capture</button>}
      </div>}

      <div ref={reviewRef}>{meal && <MealReview meal={meal} onChange={setMeal} onSaved={m => nav(`/meals/${m.id}`, { state: { saved: true } })} />}</div>
    </div>
  )
}
