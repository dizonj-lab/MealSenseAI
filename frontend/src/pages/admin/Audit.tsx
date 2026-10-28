import { useState } from 'react'
import { ScrollText } from 'lucide-react'
import { useApi } from '../../lib/hooks'
import { Card, Empty, Spinner } from '../../components/ui'

const brief = (d: Record<string, any>) => Object.entries(d ?? {}).filter(([, v]) => v !== null && v !== undefined && v !== '')
  .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · ')

export default function Audit() {
  const [limit, setLimit] = useState(100)
  const { data } = useApi<any>(`/admin/audit?limit=${limit}`)
  return (
    <Card title="Audit log" icon={<ScrollText className="size-5 text-brand-600" />}>
      <p className="text-sm text-slate-500 -mt-1 mb-3">Every admin action, setting and prompt change, and every consent change, newest first. It cannot be edited.</p>
      {!data ? <div className="py-10 grid place-items-center"><Spinner /></div> : !data.items.length ? <Empty icon={<ScrollText className="size-6" />} title="Nothing recorded yet" /> : <>
        <div className="overflow-x-auto -mx-1"><table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-slate-500 [&>th]:px-2 [&>th]:py-2 [&>th]:font-medium"><th>When</th><th>Who</th><th>Action</th><th>On</th><th>Detail</th></tr></thead>
          <tbody>{data.items.map((e: any) => (
            <tr key={e.id} className="border-t border-slate-100 [&>td]:px-2 [&>td]:py-2 align-top">
              <td className="whitespace-nowrap text-slate-500">{new Date(e.at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</td>
              <td className="whitespace-nowrap">{e.actor}</td><td className="whitespace-nowrap font-mono text-xs">{e.action}</td>
              <td className="whitespace-nowrap text-xs text-slate-500">{e.target_type ? `${e.target_type} ${e.target_id ?? ''}` : '—'}</td>
              <td className="text-xs text-slate-500 break-all">{brief(e.detail)}</td></tr>))}</tbody></table></div>
        {data.total > data.items.length && <button className="btn-ghost mt-3 w-full" onClick={() => setLimit(l => l + 100)}>Show more ({data.total - data.items.length})</button>}
      </>}
    </Card>
  )
}
