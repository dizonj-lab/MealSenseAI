import { useState } from 'react'
import { ChevronDown, Copy, Database, Snowflake } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { Card, Empty, ErrorNote, InfoTip, Spinner } from '../../components/ui'
import { ago } from './AdminShell'

function Detail({ id, onChanged }: { id: number; onChanged: () => void }) {
  const { data: d } = useApi<any>(`/admin/datasets/${id}`)
  const { data: people } = useApi<any[]>('/admin/contributors')
  const [who, setWho] = useState('')
  const [note, setNote] = useState('')
  const [err, setErr] = useState<string | null>(null)
  if (!d) return <div className="py-4 grid place-items-center"><Spinner className="size-5" /></div>
  const inVersion = (people ?? []).filter(p => d.contributor_counts?.[p.pseudonym])
  const exclude = async () => {
    if (!who || !confirm('Create a new version without this contributor? This version will be marked superseded.')) return
    setErr(null)
    try { await api(`/admin/datasets/${id}/exclude`, { method: 'POST', json: { contributor_id: Number(who), note } }); onChanged() } catch (e: any) { setErr(e.message) }
  }
  return (
    <div className="mt-3 grid md:grid-cols-2 gap-4 text-sm">
      <div><div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Foods</div>
        <ul className="space-y-0.5 max-h-56 overflow-y-auto pr-2">{Object.entries(d.per_label).map(([k, v]) => <li key={k} className="flex justify-between"><span>{k}</span><span className="tabular-nums text-slate-500">{v as number}</span></li>)}</ul></div>
      <div className="space-y-3">
        <div><div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Lineage</div>
          <div className="text-slate-600">Base: {d.base_datasets.join(' + ')} (fixed)<br />By source: {Object.entries(d.by_source).map(([k, v]) => `${k} ${v}`).join(' · ')}
            {d.excluded_contributors.length > 0 && <><br />Excluded: {d.excluded_contributors.join(', ')}</>}</div></div>
        <div><div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Export (on the server)</div>
          <div className="flex items-center gap-2 rounded-lg bg-slate-900 text-slate-100 px-3 py-2 font-mono text-[11px]"><span className="truncate">{d.export_command}</span>
            <button aria-label="Copy" className="ml-auto text-slate-400 hover:text-white" onClick={() => navigator.clipboard?.writeText(d.export_command)}><Copy className="size-3.5" /></button></div></div>
        {d.status === 'frozen' && <div><div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Roll back a contributor</div>
          <div className="flex flex-wrap gap-2"><select className="input py-1.5 text-sm flex-1 min-w-[10rem]" value={who} onChange={e => setWho(e.target.value)}>
            <option value="">Choose…</option>{inVersion.map(p => <option key={p.id} value={p.id}>{p.pseudonym} ({d.contributor_counts[p.pseudonym]} samples)</option>)}</select>
            <input className="input py-1.5 text-sm flex-1 min-w-[10rem]" placeholder="Reason" value={note} onChange={e => setNote(e.target.value)} />
            <button className="btn-ghost py-1.5 text-sm text-rose-600" disabled={!who} onClick={exclude}>New version without them</button></div>
          <ErrorNote msg={err} /></div>}
      </div>
    </div>
  )
}

export default function Datasets() {
  const { data, loading, reload } = useApi<any[]>('/admin/datasets')
  const { data: ov } = useApi<any>('/admin/overview')
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [open, setOpen] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const freeze = async () => {
    setBusy(true); setErr(null)
    try { const v = await api<any>('/admin/datasets', { method: 'POST', json: { name: name.trim(), notes } }); setName(''); setNotes(''); reload(); setOpen(v.id) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-4">
      <Card title={<span className="flex items-center gap-2">Freeze a dataset version<InfoTip label="Dataset versions" text="Freezing re-runs every check, then takes the eligible samples: shared with consent, from verified active contributors, and passed (not awaiting audit) or approved. The version never changes; withdrawals after freezing are honoured when it is exported." /></span>}
        icon={<Snowflake className="size-5 text-sky-600" />}>
        <p className="text-sm text-slate-600">{ov ? <><b>{ov.eligible}</b> samples are eligible now.</> : '…'} Base datasets (Food-101, FoodSG-233) are fixed and kept separate.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <input className="input w-40" placeholder="Name, e.g. EXP-003" value={name} onChange={e => setName(e.target.value)} />
          <input className="input flex-1 min-w-[12rem]" placeholder="Notes (optional)" value={notes} onChange={e => setNotes(e.target.value)} />
          <button className="btn-primary" disabled={!name.trim() || busy} onClick={freeze}>{busy ? <Spinner className="size-4 text-white" /> : <Snowflake className="size-4" />}Freeze</button>
        </div>
        <div className="mt-2"><ErrorNote msg={err} /></div>
      </Card>
      <Card title="Versions" icon={<Database className="size-5 text-brand-600" />}>
        {loading && !data ? <div className="py-8 grid place-items-center"><Spinner /></div> : !data?.length ? <Empty icon={<Database className="size-6" />} title="No versions yet">Freeze one when enough samples are eligible.</Empty> :
          <ul className="divide-y divide-slate-100">{data.map(v => (
            <li key={v.id} className="py-3">
              <button className="w-full flex flex-wrap items-center gap-x-4 gap-y-1 text-left" onClick={() => setOpen(open === v.id ? null : v.id)}>
                <span className="font-semibold text-slate-800">{v.name}</span>
                <span className={`chip ${v.status === 'frozen' ? 'bg-sky-50 text-sky-700' : 'bg-slate-100 text-slate-500'}`}>{v.status}</span>
                <span className="text-sm text-slate-600">{v.samples} samples · {v.labels} foods · {v.contributors} contributors</span>
                {v.largest_share?.label && <span className="text-xs text-slate-500">largest share {v.largest_share.pct}% ({v.largest_share.label})</span>}
                {(v.withdrawn_since > 0 || v.deleted_since > 0) && <span className="text-xs text-amber-700">{v.withdrawn_since + v.deleted_since} withdrawn since · {v.exportable} exportable</span>}
                <span className="ml-auto text-xs text-slate-400">{ago(v.created_at)}</span><ChevronDown className={`size-4 text-slate-400 transition ${open === v.id ? 'rotate-180' : ''}`} />
              </button>
              {v.notes && <p className="text-xs text-slate-500 mt-0.5">{v.notes}</p>}
              {open === v.id && <Detail id={v.id} onChanged={() => { reload(); setOpen(null) }} />}
            </li>))}</ul>}
      </Card>
    </div>
  )
}
