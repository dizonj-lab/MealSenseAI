import { useRef, useState } from 'react'
import { CheckCircle2, Cpu, FolderUp, Rocket, Undo2, XCircle } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { Card, Empty, ErrorNote, InfoTip, Spinner } from '../../components/ui'
import { ago } from './AdminShell'

const STATUS: Record<string, string> = {
  candidate: 'bg-slate-100 text-slate-600', shadow: 'bg-amber-50 text-amber-800', promoted: 'bg-emerald-50 text-emerald-700',
  rejected: 'bg-rose-50 text-rose-700', retired: 'bg-slate-100 text-slate-400',
}
const pct = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

function Candidate({ c, onChange }: { c: any; onChange: () => void }) {
  const [note, setNote] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const act = async (action: string) => {
    if (action === 'promote' && !confirm(`Make ${c.name} the live model for every user now?`)) return
    setBusy(true); setErr(null)
    try { await api(`/admin/models/${c.id}/action`, { method: 'POST', json: { action, note: note || null } }); onChange() } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const open = c.status === 'candidate' || c.status === 'shadow'
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-slate-800">{c.name}</span><span className={`chip ${STATUS[c.status]}`}>{c.status === 'shadow' ? 'shadow mode' : c.status}</span>
        <span className={`chip ${c.gate.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>gate {c.gate.ok ? 'passed' : 'failed'}</span>
        {c.dataset && <span className="text-xs text-slate-500">trained with {c.dataset}</span>}<span className="ml-auto text-xs text-slate-400">{ago(c.created_at)}</span>
      </div>
      <div className="mt-3 grid lg:grid-cols-[1.4fr_1fr] gap-4">
        <table className="w-full text-sm"><thead><tr className="text-xs text-slate-500 text-left"><th className="font-medium py-1">Check</th><th className="font-medium text-right">Live</th>
          <th className="font-medium text-right">Candidate</th><th className="font-medium text-right">Change</th><th /></tr></thead>
          <tbody>{c.gate.checks.map((k: any) => (
            <tr key={k.name} className="border-t border-slate-100"><td className="py-1.5">{k.name}</td>
              <td className="text-right tabular-nums">{typeof k.live === 'number' ? pct(k.live) : k.live ?? '—'}</td>
              <td className="text-right tabular-nums font-medium">{typeof k.candidate === 'number' ? pct(k.candidate) : k.candidate ?? '—'}</td>
              <td className={`text-right tabular-nums ${k.delta_pts == null ? 'text-slate-400' : k.delta_pts < 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                {k.delta_pts == null ? (k.why ?? '') : `${k.delta_pts > 0 ? '+' : ''}${k.delta_pts} pts`}</td>
              <td className="pl-2">{k.ok ? <CheckCircle2 className="size-4 text-emerald-600" /> : <XCircle className="size-4 text-rose-500" />}</td></tr>))}</tbody></table>
        <div className="text-sm space-y-2">
          <div className="rounded-xl bg-slate-50 p-3"><div className="text-xs text-slate-500">Shadow mode</div>
            {c.shadow.total ? <><div><b>{c.shadow.agreement_pct}%</b> agreement over {c.shadow.total} foods</div>
              {c.shadow.disagreements.length > 0 && <ul className="mt-1 text-xs text-slate-500">{c.shadow.disagreements.slice(0, 4).map(([k, n]: [string, number]) => <li key={k}>{k} · {n}</li>)}</ul>}</>
              : <div className="text-slate-500">{c.status === 'shadow' ? 'Running: waiting for meals' : 'Not run yet'}</div>}</div>
          <div className="text-xs text-slate-500">Test set {c.report.test_set?.images ?? '?'} images · {c.report.test_set?.sha256?.slice(0, 12)}</div>
          {open && c.blockers.length > 0 && <div className="text-xs text-amber-800">Promotion blocked: {c.blockers.join('; ')}.</div>}
        </div>
      </div>
      {open && <div className="mt-3 flex flex-wrap items-center gap-2">
        <input className="input py-1.5 text-sm flex-1 min-w-[12rem]" placeholder="Note for the audit log" value={note} onChange={e => setNote(e.target.value)} />
        {c.status === 'candidate' && <button className="btn-ghost py-1.5 text-sm" disabled={busy || !c.gate.ok} onClick={() => act('shadow')}>Start shadow mode</button>}
        {c.status === 'shadow' && <button className="btn-ghost py-1.5 text-sm" disabled={busy} onClick={() => act('stop_shadow')}>Stop shadow mode</button>}
        <button className="btn-ghost py-1.5 text-sm" disabled={busy} onClick={() => act('reevaluate')} title="Apply today's tolerances from Model settings">Re-check</button>
        <button className="btn-ghost py-1.5 text-sm text-rose-600" disabled={busy} onClick={() => act('reject')}>Reject</button>
        <button className="btn-primary py-1.5 text-sm" disabled={busy || c.blockers.length > 0} onClick={() => act('promote')}><Rocket className="size-4" />Promote to live</button>
      </div>}
      {c.note && !open && <p className="mt-2 text-xs text-slate-500">Note: {c.note}</p>}
      <div className="mt-2"><ErrorNote msg={err} /></div>
    </li>
  )
}

export default function Models() {
  const { data, loading, reload } = useApi<any>('/admin/models')
  const { data: versions } = useApi<any[]>('/admin/datasets')
  const files = useRef<HTMLInputElement>(null)
  const [ds, setDs] = useState('')
  const [picked, setPicked] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const upload = async () => {
    setBusy(true); setErr(null)
    try {
      const fd = new FormData()
      picked.forEach(f => fd.append('files', f))
      if (ds) fd.append('dataset_version', ds)
      await api('/admin/models', { method: 'POST', body: fd }); setPicked([]); if (files.current) files.current.value = ''; reload()
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const builtin = async () => {
    if (!confirm('Roll back to the built-in model for every user now?')) return
    try { await api('/admin/models/use-builtin', { method: 'POST' }); reload() } catch (e: any) { setErr(e.message) }
  }
  if (loading && !data) return <div className="py-16 grid place-items-center"><Spinner /></div>
  const live = data?.live, need = data?.package_files ?? []
  const names = new Set(picked.map(f => f.name))
  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Live model" icon={<Cpu className="size-5 text-brand-600" />} action={live?.promoted && <button className="btn-ghost py-1.5 text-sm" onClick={builtin}><Undo2 className="size-4" />Use the built-in model</button>}>
          {live ? <dl className="text-sm grid grid-cols-[9rem_1fr] gap-y-1.5">
            <dt className="text-slate-500">Model</dt><dd className="font-medium">{live.name} · {live.version}</dd>
            <dt className="text-slate-500">Source</dt><dd>{live.promoted ? <>Promoted package <b>{live.promoted}</b></> : 'Built into the app image'}</dd>
            <dt className="text-slate-500">Classes</dt><dd>{live.food_classes}</dd><dt className="text-slate-500">Device</dt><dd>{(live.device ?? 'cpu').toUpperCase()}</dd>
            <dt className="text-slate-500">Shadow</dt><dd>{live.shadow ?? 'none'}</dd></dl> : <p className="text-sm text-rose-600">{data?.errors ?? 'No classifier loaded'}</p>}
        </Card>
        <Card title={<span className="flex items-center gap-2">Model updates location<InfoTip label="Model updates" text="New models are uploaded here as a package: model.onnx, class_mapping.json, model_card.json, and report.json from ml/evaluation/gate_report.py on the fixed test set. The package must load before it is accepted. It then waits at the gate; promoting it makes it live at once, without a rebuild." /></span>}
          icon={<FolderUp className="size-5 text-violet-600" />}>
          <div className="text-xs text-slate-500">Stored on the server in</div>
          <div className="font-mono text-xs rounded-lg bg-slate-50 ring-1 ring-slate-200 px-2.5 py-1.5 mt-1 break-all">{data?.updates_dir}/&lt;name&gt;/</div>
          <div className="mt-3 flex flex-wrap gap-1.5">{need.map((f: string) => <span key={f} className={`chip ${names.has(f) ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{names.has(f) ? '✓ ' : ''}{f}</span>)}</div>
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <input ref={files} type="file" multiple accept=".onnx,.json" className="text-sm flex-1 min-w-[12rem]" onChange={e => setPicked(Array.from(e.target.files ?? []))} />
            <select className="input py-1.5 text-sm w-44" value={ds} onChange={e => setDs(e.target.value)} aria-label="Trained with">
              <option value="">Trained with…</option>{(versions ?? []).map(v => <option key={v.id} value={v.name}>{v.name}</option>)}</select>
            <button className="btn-primary py-1.5 text-sm" disabled={busy || need.some((f: string) => !names.has(f))} onClick={upload}>{busy ? <Spinner className="size-4 text-white" /> : <FolderUp className="size-4" />}Upload</button>
          </div>
          <div className="mt-2"><ErrorNote msg={err} /></div>
        </Card>
      </div>
      <Card title={<span className="flex items-center gap-2">Model gate<InfoTip label="Model gate" text={`A candidate must match the live model overall and on rice, noodles and sweet drinks (tolerances in Model settings), on the same fixed test set. Then shadow mode: it classifies every food beside the live model, unseen by users. Promotion needs ${data?.shadow_requirements?.min_items} foods compared and ${data?.shadow_requirements?.min_agreement_pct}% agreement.`} /></span>}
        icon={<Rocket className="size-5 text-amber-500" />}>
        {!data?.candidates?.length ? <Empty icon={<Rocket className="size-6" />} title="No candidates yet">Upload a package above after training on a frozen dataset version.</Empty>
          : <ul className="divide-y divide-slate-100">{data.candidates.map((c: any) => <Candidate key={c.id} c={c} onChange={reload} />)}</ul>}
      </Card>
    </div>
  )
}
