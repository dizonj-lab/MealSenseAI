import { useEffect, useState } from 'react'
import { History, MessageSquareQuote, RotateCcw, Save, ShieldCheck } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { Card, ErrorNote, Spinner } from '../../components/ui'
import { ago } from './AdminShell'

type P = { key: string; label: string; help: string; default: string; text: string; active_version: number | null; versions: number }

function Editor({ p, onChange }: { p: P; onChange: () => void }) {
  const [text, setText] = useState(p.text)
  const [note, setNote] = useState('')
  const [hist, setHist] = useState<any[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => setText(p.text), [p.text])
  const run = async (fn: () => Promise<any>) => { setBusy(true); setErr(null); try { await fn(); setNote(''); setHist(null); onChange() } catch (e: any) { setErr(e.message) } finally { setBusy(false) } }
  const save = () => run(() => api(`/admin/prompts/${p.key}`, { method: 'POST', json: { text, note } }))
  const activate = (version: number | null) => run(() => api(`/admin/prompts/${p.key}/activate`, { method: 'POST', json: { version } }))
  const history = async () => setHist(hist ? null : (await api<any>(`/admin/prompts/${p.key}`)).history)
  return (
    <Card title={<span className="flex items-center gap-2">{p.label}<span className={`chip text-[10px] ${p.active_version ? 'bg-brand-50 text-brand-700' : 'bg-slate-100 text-slate-500'}`}>
      {p.active_version ? `version ${p.active_version}` : 'built-in'}</span></span>}
      action={<button className="btn-ghost px-2.5 py-1 text-xs" onClick={history}><History className="size-3.5" />History ({p.versions})</button>}>
      <p className="text-xs text-slate-500 -mt-1 mb-2">{p.help} <code className="text-slate-400">{p.key}</code></p>
      <textarea className="input font-mono text-[13px] leading-relaxed min-h-[7rem]" value={text} onChange={e => setText(e.target.value)} maxLength={4000} aria-label={p.label} />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input className="input py-1.5 text-sm flex-1 min-w-[12rem]" placeholder="What changed and why (for the history)" value={note} onChange={e => setNote(e.target.value)} maxLength={300} />
        <span className="text-[11px] text-slate-400">{text.length} / 4000</span>
        {p.active_version && <button className="btn-ghost py-1.5 text-sm" disabled={busy} onClick={() => activate(null)}><RotateCcw className="size-4" />Use built-in</button>}
        <button className="btn-primary py-1.5 text-sm" disabled={busy || text.trim() === p.text.trim()} onClick={save}>{busy ? <Spinner className="size-4 text-white" /> : <Save className="size-4" />}Save as new version</button>
      </div>
      <ErrorNote msg={err} />
      {hist && <ul className="mt-3 divide-y divide-slate-100 rounded-xl ring-1 ring-slate-200">
        <li className="p-3 text-sm flex items-start gap-3"><div className="flex-1 min-w-0"><div className="font-medium">Built-in default</div>
          <p className="text-xs text-slate-500 font-mono whitespace-pre-wrap mt-1">{p.default}</p></div>
          {p.active_version !== null ? <button className="btn-ghost px-2.5 py-1 text-xs" onClick={() => activate(null)}>Use</button> : <span className="chip bg-brand-50 text-brand-700">active</span>}</li>
        {hist.map(h => <li key={h.version} className="p-3 text-sm flex items-start gap-3"><div className="flex-1 min-w-0">
          <div className="font-medium">Version {h.version} <span className="text-xs font-normal text-slate-400">· {ago(h.created_at)}{h.note ? ` · ${h.note}` : ''}</span></div>
          <p className="text-xs text-slate-500 font-mono whitespace-pre-wrap mt-1">{h.text}</p></div>
          {h.active ? <span className="chip bg-brand-50 text-brand-700">active</span> : <button className="btn-ghost px-2.5 py-1 text-xs" onClick={() => activate(h.version)}>Use</button>}</li>)}
      </ul>}
    </Card>
  )
}

/** The local model's prompts, versioned. The Meal Advisor's checks on numbers, foods and unsafe advice apply whatever a prompt says. */
export default function Prompts() {
  const { data, reload } = useApi<P[]>('/admin/prompts')
  if (!data) return <div className="py-16 grid place-items-center"><Spinner /></div>
  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-emerald-50/70 ring-1 ring-emerald-200 p-4 text-sm text-emerald-900 flex gap-3">
        <ShieldCheck className="size-5 shrink-0 mt-0.5" /><div><b>Prompts shape wording, not facts.</b> Every number in a reply must come from the user's data or the food
          table, no new foods may appear, and unsafe advice is blocked; otherwise the rule engine's own answer is shown. These checks apply whatever a prompt says.
          Saving creates a new version; any version, or the built-in default, can be made active again.</div></div>
      {data.map(p => <Editor key={p.key} p={p} onChange={reload} />)}
      <p className="text-xs text-slate-400 flex items-center gap-1.5"><MessageSquareQuote className="size-3.5" />Used only when the local model is on (Model settings → Local language model).</p>
    </div>
  )
}
