import { useEffect, useState } from 'react'
import { Activity, CheckCircle2, ChevronUp, CircleDashed, Copy, Cpu, Loader2, ShieldCheck, X, XCircle } from 'lucide-react'
import type { Meal, Stage } from '../lib/types'

export const STAGES = [
  ['capture', 'Meal capture'], ['preprocess', 'Image pre-processing'], ['detect', 'Food instance detection'],
  ['classify', 'Food classification'], ['portion', 'Portion estimation'], ['nutrition', 'Nutrition mapping'],
  ['aggregate', 'Meal aggregation'], ['contextualise', 'AI contextualisation'], ['recommend', 'Recommendations'],
  ['output', 'Application output'],
] as const
const WARN = new Set(['unsupported', 'fallback', 'uncertain'])
const COLOR: Record<string, string> = { done: '#10b981', deferred: '#8b5cf6', skipped: '#cbd5e1', uncertain: '#f59e0b', fallback: '#f59e0b', unsupported: '#f43f5e' }

function StageIcon({ s, running }: { s?: Stage; running: boolean }) {
  if (!s) return running ? <Loader2 className="size-5 text-brand-600 animate-spin" /> : <CircleDashed className="size-5 text-slate-300" />
  if (s.status === 'done') return <CheckCircle2 className="size-5 text-emerald-600" />
  if (s.status === 'deferred') return <Activity className="size-5 text-violet-500" />
  return WARN.has(s.status) ? <XCircle className="size-5 text-amber-500" /> : <CircleDashed className="size-5 text-slate-400" />
}

/** Compact live progress bar; the full pipeline and telemetry open in a pull-up drawer. */
export default function PipelineDrawer({ stages, current, elapsedMs, meal }: { stages: Stage[]; current: string | null; elapsedMs: number | null; meal: Meal | null }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const running = current !== null
  const done = stages.length
  const pct = Math.round((done / STAGES.length) * 100)
  const curName = STAGES.find(([k]) => k === current)?.[1]
  const total = stages.reduce((a, s) => a + (s.latency_ms || 0), 0)
  const warns = stages.filter(s => WARN.has(s.status))
  const device = stages.find(s => s.key === 'classify')?.detail.match(/ on (\w+)/)?.[1]
  useEffect(() => { document.body.style.overflow = open ? 'hidden' : ''; return () => { document.body.style.overflow = '' } }, [open])

  const foods = meal?.foods ?? []
  const active = foods.filter(f => !f.removed)
  const vis = meal?.model_info?.vision ?? {}
  const trace = { meal_id: meal?.id, stages, model_info: meal?.model_info, items: foods.map(f => ({ id: f.id, label: f.label, removed: f.removed,
    kind: f.original_prediction?.kind, raw_score: f.original_prediction?.score, region: f.original_prediction?.region_id, nutrition_key: f.nutrition_key, grams: f.grams })) }

  return (<>
    <button onClick={() => setOpen(true)} className="card w-full p-3.5 text-left" aria-label="Open analysis telemetry">
      <div className="flex items-center gap-2.5">
        {running ? <Loader2 className="size-5 text-brand-600 animate-spin shrink-0" /> : warns.length ? <XCircle className="size-5 text-amber-500 shrink-0" /> : <CheckCircle2 className="size-5 text-emerald-600 shrink-0" />}
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-slate-800 truncate">{running ? `Step ${Math.min(done + 1, STAGES.length)}/${STAGES.length} · ${curName}` : 'Analysis complete'}</div>
          <div className="text-xs text-slate-500 truncate">{running ? `${((elapsedMs ?? 0) / 1000).toFixed(1)} s elapsed` :
            `${done} steps · ${(total / 1000).toFixed(2)} s${device ? ` · ${device.toUpperCase()}` : ''}${warns.length ? ` · ${warns.length} note(s)` : ''}`}</div>
        </div>
        <span className="chip bg-slate-100 text-slate-600 shrink-0"><ChevronUp className="size-3.5" />Details</span>
      </div>
      <div className="mt-2.5 h-1.5 rounded-full bg-slate-100 overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={`h-full rounded-full transition-all duration-300 ${running ? 'bg-brand-600' : warns.length ? 'bg-amber-400' : 'bg-emerald-500'}`} style={{ width: `${pct}%` }} />
      </div>
    </button>

    {open && <div className="fixed inset-0 z-50 flex items-end sm:items-stretch sm:justify-end" role="dialog" aria-modal="true" aria-label="Analysis telemetry">
      <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
      <div className="relative w-full sm:max-w-lg max-h-[88vh] sm:max-h-none sm:h-full overflow-y-auto rounded-t-3xl sm:rounded-none bg-white shadow-2xl pb-[env(safe-area-inset-bottom)]">
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur px-4 pt-2 pb-3 border-b border-slate-100">
          <div className="mx-auto mb-2 h-1.5 w-10 rounded-full bg-slate-300 sm:hidden" />
          <div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900 flex items-center gap-2"><Activity className="size-5 text-brand-600" />Pipeline telemetry</h2>
            <button onClick={() => setOpen(false)} className="size-9 grid place-items-center rounded-full hover:bg-slate-100" aria-label="Close"><X className="size-5" /></button></div>
          <div className="mt-2 h-1.5 rounded-full bg-slate-100 overflow-hidden"><div className="h-full bg-brand-600 transition-all" style={{ width: `${pct}%` }} /></div>
          <div className="mt-1 text-[11px] text-slate-500">{done}/{STAGES.length} steps · {running ? `running ${curName} · ${((elapsedMs ?? 0) / 1000).toFixed(1)} s` : `${(total / 1000).toFixed(2)} s total`}</div>
        </div>
        <div className="p-4 space-y-5">
          {meal && <div className="grid grid-cols-2 gap-2 text-center">
            {[['Total time', `${(total / 1000).toFixed(2)} s`], ['Device', (device ?? 'cpu').toUpperCase()],
              ['Items', `${active.length} listed · ${foods.filter(f => f.removed && f.original_prediction?.kind === 'suggestion').length} offered`],
              ['Nutrition coverage', `${active.filter(f => f.nutrition_key).length}/${active.length} matched`]].map(([l, v]) => (
              <div key={l} className="rounded-xl bg-slate-50 py-2"><div className="text-[10px] text-slate-500">{l}</div><div className="text-sm font-semibold text-slate-800">{v}</div></div>))}
          </div>}

          <section><h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Latency by step</h3>
            <div className="space-y-1.5">{STAGES.map(([k, name], i) => { const s = stages.find(x => x.key === k); const w = s && total ? Math.max((s.latency_ms / total) * 100, 1) : 0; return (
              <div key={k} className="grid grid-cols-[7.5rem_minmax(0,1fr)_3.5rem] items-center gap-2 text-[11px]">
                <span className={`truncate ${s || k === current ? 'text-slate-700' : 'text-slate-400'}`}>{i + 1}. {name}</span>
                <div className="h-2.5 rounded bg-slate-100 overflow-hidden">{s ? <div className="h-full rounded" style={{ width: `${w}%`, background: COLOR[s.status] ?? '#94a3b8' }} />
                  : k === current ? <div className="h-full w-1/3 rounded bg-brand-600/60 animate-pulse" /> : null}</div>
                <span className="text-right tabular-nums text-slate-500">{s ? `${s.latency_ms} ms` : k === current ? '…' : ''}</span></div>) })}</div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-500">{[['done', 'done'], ['deferred', 'deferred'], ['uncertain', 'uncertain / fallback'], ['unsupported', 'unsupported'], ['skipped', 'skipped']].map(([k, l]) =>
              <span key={k} className="flex items-center gap-1"><i className="inline-block size-2 rounded-sm" style={{ background: COLOR[k] }} />{l}</span>)}</div></section>

          <section><h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Steps</h3>
            <ol className="space-y-3">{STAGES.map(([k, name], i) => { const s = stages.find(x => x.key === k); return (
              <li key={k} className="flex gap-3"><span className="mt-0.5"><StageIcon s={s} running={k === current} /></span>
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between gap-2 text-sm"><span className={`font-medium ${s || k === current ? 'text-slate-800' : 'text-slate-400'}`}>{i + 1}. {name}</span>
                    {s && <span className="text-xs text-slate-400 shrink-0">{s.status !== 'done' && <b className="font-medium mr-1">{s.status}</b>}{s.latency_ms} ms</span>}</div>
                  {s && <p className="text-xs text-slate-500 mt-0.5">{s.detail}</p>}
                  {s?.per_view?.map(v => v.top_labels?.length > 0 && <p key={v.view} className="text-[11px] text-slate-400 mt-0.5">{v.view} view, whole-image top-5 (raw): {v.top_labels.map((t: any) => `${t.label} ${t.score.toFixed(2)}`).join(', ')}</p>)}
                  {s?.per_view?.map(v => v.instances?.length > 0 && <p key={v.view + 'i'} className="text-[11px] text-slate-400 mt-0.5">{v.view} view regions: {v.instances.map((x: any) => `${x.label} (${x.kind}, ${(x.area_frac * 100).toFixed(0)}%)`).join('; ')}</p>)}
                </div></li>) })}</ol></section>

          {meal && <section><h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-1.5"><Cpu className="size-3.5" />Models & data</h3>
            <dl className="text-xs space-y-1.5">
              {Object.entries(vis).map(([role, m]: [string, any]) => <div key={role} className="flex gap-2"><dt className="w-20 shrink-0 capitalize text-slate-500">{role}</dt>
                <dd className="text-slate-700">{m.name} <span className="text-slate-400">v{m.version} · {m.task}{m.trained_on ? ` · ${m.trained_on}` : ''}</span></dd></div>)}
              <div className="flex gap-2"><dt className="w-20 shrink-0 text-slate-500">Text SLM</dt><dd className="text-slate-700">{meal.model_info?.slm ?? 'offline (rule-based fallback)'}</dd></div>
              <div className="flex gap-2"><dt className="w-20 shrink-0 text-slate-500">Nutrition</dt><dd className="text-slate-700">reference table {meal.model_info?.nutrition_table}</dd></div>
            </dl></section>}

          <section className="rounded-xl bg-emerald-50/60 ring-1 ring-emerald-100 p-3 text-xs text-slate-600 space-y-1">
            <h3 className="font-semibold text-emerald-800 flex items-center gap-1.5"><ShieldCheck className="size-4" />Transparency</h3>
            <p>All models run on this server (ONNX Runtime; optional local Ollama). No cloud AI service is called.</p>
            <p>Percentages are raw softmax scores, not calibrated probabilities. Portions are typical-serving priors with uncertainty ranges; volume is not measured.</p>
            <p>Nutrition values come from a transcribed, unverified reference table. Glucose curves are simulations, never measurements.</p>
          </section>

          {meal && <details className="text-xs"><summary className="cursor-pointer text-slate-600 font-medium">Raw trace (JSON)</summary>
            <button className="mt-2 chip bg-slate-100 text-slate-700" onClick={() => { navigator.clipboard?.writeText(JSON.stringify(trace, null, 2)).then(() => setCopied(true)).catch(() => {}) }}>
              <Copy className="size-3.5" />{copied ? 'Copied' : 'Copy'}</button>
            <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-slate-900 text-slate-100 p-3 text-[10px] leading-snug">{JSON.stringify(trace, null, 2)}</pre></details>}
        </div>
      </div>
    </div>}
  </>)
}
