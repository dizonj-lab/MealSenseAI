import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Users } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { Card, Empty, ErrorNote, InfoTip, Spinner } from '../../components/ui'

const TRUST: Record<string, [string, string]> = {
  established: ['Established', 'bg-emerald-50 text-emerald-700'], normal: ['Normal', 'bg-slate-100 text-slate-600'],
  new: ['New', 'bg-sky-50 text-sky-700'], watch: ['Watch', 'bg-amber-50 text-amber-800'], suspended: ['Suspended', 'bg-rose-50 text-rose-700'],
}

export default function Contributors() {
  const { data, loading, reload } = useApi<any[]>('/admin/contributors')
  const [err, setErr] = useState<string | null>(null)
  const act = async (id: number, action: string) => {
    if (action === 'suspend' && !confirm('Suspend this contributor? Their samples stay stored but are left out of new dataset versions.')) return
    setErr(null)
    try { await api(`/admin/contributors/${id}`, { method: 'POST', json: { action } }); reload() } catch (e: any) { setErr(e.message) }
  }
  return (
    <Card title={<span className="flex items-center gap-2">Contributors<InfoTip label="Contributors" text="People who recorded labelled photo crops. Trust: New under 3 days; Watch when at least 1 in 5 decided samples was rejected; Established after 30 days and 10 accepted samples. The largest share is this person's share of one food's shared examples, compared with the contributor cap in Model settings." /></span>}
      icon={<Users className="size-5 text-brand-600" />}>
      <ErrorNote msg={err} />
      {loading && !data ? <div className="py-10 grid place-items-center"><Spinner /></div> : !data?.length ? <Empty icon={<Users className="size-6" />} title="No contributors yet">Samples appear when people name or correct foods in their photos.</Empty> :
        <div className="overflow-x-auto -mx-1"><table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-slate-500 [&>th]:px-2 [&>th]:py-2 [&>th]:font-medium">
            <th>Contributor</th><th>Trust</th><th className="text-right">Samples</th><th className="text-right">Shared</th><th className="text-right">Accepted</th>
            <th className="text-right">Flagged</th><th className="text-right">Rejected</th><th className="text-right">7 days</th><th>Largest share</th><th></th></tr></thead>
          <tbody>{data.map(c => { const [tl, tc] = TRUST[c.trust] ?? TRUST.normal; return (
            <tr key={c.id} className="border-t border-slate-100 [&>td]:px-2 [&>td]:py-2.5 align-top">
              <td><div className="font-medium text-slate-800">{c.pseudonym}</div><div className="text-xs text-slate-500">{c.email}</div>
                <div className="text-xs text-slate-400">{c.account_days} d · {c.verified ? 'verified' : 'not verified'} · {c.consent ? 'sharing' : 'not sharing'}</div></td>
              <td><span className={`chip ${tc}`}>{tl}</span></td>
              <td className="text-right tabular-nums">{c.samples}</td><td className="text-right tabular-nums">{c.shared}</td>
              <td className="text-right tabular-nums">{c.approved + c.passed}</td><td className="text-right tabular-nums text-amber-700">{c.flagged || ''}</td>
              <td className="text-right tabular-nums text-rose-700">{c.rejected || ''}</td><td className="text-right tabular-nums">{c.week}</td>
              <td className="text-xs">{c.largest_share.label ? <>{c.largest_share.pct}% of <b>{c.largest_share.label}</b></> : <span className="text-slate-400" title="Shares count once a food has 20 shared examples">—</span>}</td>
              <td><div className="flex flex-wrap gap-1 justify-end">
                <Link to={`/admin/review?queue=all&contributor=${c.id}`} className="btn-ghost px-2.5 py-1 text-xs">Samples</Link>
                {!c.verified && <button className="btn-ghost px-2.5 py-1 text-xs" onClick={() => act(c.id, 'verify_email')} title="Mark the email as verified (when verification emails cannot be sent)">Verify</button>}
                {c.status === 'suspended' ? <button className="btn-ghost px-2.5 py-1 text-xs" onClick={() => act(c.id, 'reactivate')}>Reactivate</button>
                  : <button className="btn-ghost px-2.5 py-1 text-xs text-rose-600" onClick={() => act(c.id, 'suspend')}>Suspend</button>}</div></td>
            </tr>) })}</tbody></table></div>}
    </Card>
  )
}
