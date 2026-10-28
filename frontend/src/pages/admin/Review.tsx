import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Check, ClipboardCheck, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi, useAuthImage } from '../../lib/hooks'
import { Card, Empty, ErrorNote, InfoTip, Spinner, Stat } from '../../components/ui'
import { ReasonChip, ago } from './AdminShell'

const QUEUES: [string, string][] = [['review', 'Needs review'], ['audit', 'Random audit'], ['flagged', 'Flagged'], ['passed', 'Passed'],
  ['approved', 'Approved'], ['rejected', 'Rejected'], ['withdrawn', 'Withdrawn'], ['all', 'All']]

function Crop({ url }: { url: string }) {
  const src = useAuthImage(url)
  return src ? <img src={src} alt="" className="size-20 sm:size-24 rounded-xl object-cover bg-slate-100 shrink-0" />
    : <div className="size-20 sm:size-24 rounded-xl bg-slate-100 shrink-0" />
}

function Row({ s, selected, onSelect, onDecide }: { s: any; selected: boolean; onSelect: () => void; onDecide: (d: 'approve' | 'reject', note?: string) => void }) {
  const [note, setNote] = useState('')
  const decided = s.status === 'approved' || s.status === 'rejected'
  return (
    <li className="py-3 flex gap-3 items-start">
      <input type="checkbox" className="mt-1 size-4 accent-teal-600" checked={selected} onChange={onSelect} aria-label={`Select sample ${s.id}`} />
      <Crop url={s.crop_url} />
      <div className="min-w-0 flex-1 grid gap-1.5 sm:grid-cols-[1fr_1fr] lg:grid-cols-[1.1fr_1.2fr_1.5fr]">
        <div className="min-w-0"><div className="text-xs text-slate-500">User's label · #{s.id}</div>
          <div className="font-semibold text-slate-800 truncate">{s.label}</div>
          <div className="text-xs text-slate-500">{s.source}{s.shared ? '' : s.withdrawn ? ' · withdrawn' : ' · not shared'}</div></div>
        <div className="min-w-0"><div className="text-xs text-slate-500">Model's view</div>
          <div className="text-sm text-slate-700">{s.model_label ?? '—'}{s.model_score != null && <span className="text-slate-400"> {(s.model_score * 100).toFixed(0)}%</span>}</div>
          <div className="text-xs text-slate-400 truncate">top 3: {(s.model_candidates || []).map((c: any) => c.label).join(', ') || '—'}</div></div>
        <div className="min-w-0 sm:col-span-2 lg:col-span-1">
          <div className="flex flex-wrap gap-1">{s.reasons.filter((r: any) => r.severity !== 'info').map((r: any) => <ReasonChip key={r.code} r={r} />)}
            {s.audit && s.status === 'passed' && <span className="chip ring-1 bg-sky-50 text-sky-700 ring-sky-200">Random audit</span>}
            {s.reasons.filter((r: any) => r.severity === 'info').map((r: any) => <ReasonChip key={r.code} r={r} />)}</div>
          <div className="mt-1 text-xs text-slate-500">{s.reasons.find((r: any) => r.severity !== 'info')?.detail}</div>
          <div className="mt-1 text-xs text-slate-400">{s.contributor.pseudonym} · account {s.contributor.account_days} d{s.contributor.verified ? ' · verified' : ' · not verified'}
            {s.contributor.status === 'suspended' && <span className="text-rose-600"> · suspended</span>} · {ago(s.created_at)}</div>
        </div>
      </div>
      <div className="shrink-0 flex flex-col items-end gap-1.5 w-36">
        {decided ? <span className={`chip ${s.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{s.status}</span> : <>
          <div className="flex gap-1.5"><button className="btn-primary px-3 py-1.5 text-xs" onClick={() => onDecide('approve', note)}><Check className="size-3.5" />Accept</button>
            <button className="btn-ghost px-3 py-1.5 text-xs text-rose-600" onClick={() => onDecide('reject', note)}><X className="size-3.5" />Reject</button></div>
          <input className="input py-1 text-xs" placeholder="Note (optional)" value={note} onChange={e => setNote(e.target.value)} maxLength={300} /></>}
        {decided && s.review_note && <span className="text-[11px] text-slate-400 text-right">{s.review_note}</span>}
      </div>
    </li>
  )
}

export default function Review() {
  const [params, setParams] = useSearchParams()
  const queue = params.get('queue') || 'review', reason = params.get('reason'), contributor = params.get('contributor')
  const qs = new URLSearchParams({ queue, ...(reason ? { reason } : {}), ...(contributor ? { contributor } : {}) })
  const { data: ov, reload: reloadOv } = useApi<any>('/admin/overview')
  const { data, loading, reload } = useApi<any>(`/admin/samples?${qs}`)
  const [sel, setSel] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const set = (k: string, v: string | null) => { const p = new URLSearchParams(params); v ? p.set(k, v) : p.delete(k); if (k === 'queue') p.delete('reason'); setParams(p); setSel([]) }
  const decide = async (ids: number[], decision: 'approve' | 'reject', note?: string) => {
    setErr(null)
    try { await api('/admin/samples/review', { method: 'POST', json: { ids, decision, note: note || null } }); setSel([]); reload(); reloadOv() }
    catch (e: any) { setErr(e.message) }
  }
  const rescreen = async () => { setBusy(true); try { await api('/admin/screen', { method: 'POST' }); reload(); reloadOv() } catch (e: any) { setErr(e.message) } finally { setBusy(false) } }
  const st = ov?.by_status ?? {}
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex-1 min-w-[16rem]"><h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2"><ClipboardCheck className="size-5 text-brand-600" />Training data review
          <InfoTip label="Training data review" text="Photo crops users chose to share for training. Every sample is checked automatically; flagged ones and a random audit sample wait here for a person. Nothing reaches a dataset version without passing." /></h2>
          <p className="text-sm text-slate-500">Nothing reaches a dataset version without passing these checks or a person's approval.</p></div>
        <button className="btn-ghost" onClick={rescreen} disabled={busy}>{busy ? <Spinner className="size-4" /> : <RefreshCw className="size-4" />}Run all checks again</button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="Received this week" value={ov?.received_week ?? '…'} />
        <Stat label="Passed automatically" value={st.passed ?? 0} tone="green" />
        <Stat label="Waiting for review" value={ov ? (st.flagged ?? 0) + (ov.audit_open ?? 0) : '…'} tone="amber" sub={ov && `${ov.audit_open} random audit`} />
        <Stat label="Rejected" value={st.rejected ?? 0} sub="duplicates, junk, by a person" />
        <Stat label="Eligible for a dataset" value={ov?.eligible ?? '…'} tone="teal" sub={ov?.latest_dataset ? `latest: ${ov.latest_dataset}` : 'no version yet'} />
      </div>
      <Card>
        <div className="flex flex-wrap gap-1.5">{QUEUES.map(([k, l]) => (
          <button key={k} onClick={() => set('queue', k)} className={`chip px-3 py-1.5 ${queue === k ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'}`}>{l}</button>))}
          {contributor && <button onClick={() => set('contributor', null)} className="chip px-3 py-1.5 bg-sky-50 text-sky-700">Contributor #{contributor} <X className="size-3" /></button>}</div>
        {data?.reasons?.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
          <span className="text-slate-400 py-1">Why:</span>
          {data.reasons.map((r: any) => <button key={r.code} onClick={() => set('reason', reason === r.code ? null : r.code)}
            className={`chip ring-1 ${reason === r.code ? 'bg-slate-800 text-white ring-slate-800' : 'bg-white text-slate-600 ring-slate-200'}`}>{r.label} · {r.count}</button>)}</div>}
        <div className="mt-3"><ErrorNote msg={err} /></div>
        {sel.length > 0 && <div className="mt-3 flex items-center gap-2 rounded-xl bg-slate-50 p-2 text-sm">
          <span className="text-slate-600">{sel.length} selected</span>
          <button className="btn-primary px-3 py-1.5 text-xs ml-auto" onClick={() => decide(sel, 'approve')}><Check className="size-3.5" />Accept all</button>
          <button className="btn-ghost px-3 py-1.5 text-xs text-rose-600" onClick={() => decide(sel, 'reject')}><X className="size-3.5" />Reject all</button></div>}
        {loading && !data ? <div className="py-10 grid place-items-center"><Spinner /></div>
          : !data?.items.length ? <Empty icon={<ShieldCheck className="size-6" />} title="Nothing here">{queue === 'review' ? 'No sample is waiting for a person.' : 'No samples in this list.'}</Empty>
          : <ul className="divide-y divide-slate-100">{data.items.map((s: any) => <Row key={s.id} s={s} selected={sel.includes(s.id)}
              onSelect={() => setSel(x => x.includes(s.id) ? x.filter(i => i !== s.id) : [...x, s.id])} onDecide={(d, n) => decide([s.id], d, n)} />)}</ul>}
        {data && data.total > data.items.length && <p className="mt-2 text-xs text-slate-400">Showing {data.items.length} of {data.total}. Decide these to see more.</p>}
      </Card>
    </div>
  )
}
