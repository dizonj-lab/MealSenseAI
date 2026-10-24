import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUp, RotateCcw, Trash2 } from 'lucide-react'
import { api, tzOffset } from '../lib/api'
import { Spinner } from './ui'

type Ev = { level: string; label: string; detail: string }
type Msg = { role: 'user' | 'assistant'; content: string; created_at?: string; source?: string; evidence?: Ev[]; followups?: string[]; hypothetical?: boolean }
export const PROMPTS: Record<string, string[]> = {
  meal: ['What is in my meal?', 'How might this affect my glucose?', 'What could I change to make this meal healthier?', 'Why did you classify this food this way?'],
  today: ['How many carbohydrates did I consume today?', 'How am I doing today?', 'What is in my meal?'],
  week: ['How was my week?', "What's my trajectory? Any advice?", 'What are my biggest carb sources?'],
}
const LEVEL: Record<string, string> = { L1: 'You', L2: 'Model', L3: 'Food table', L4: 'Guidance', L5: 'Calculated' }
const time = (iso?: string) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''

function Sources({ ev, source }: { ev: Ev[]; source?: string }) {
  const [open, setOpen] = useState(false)
  const by = source?.startsWith('slm:') ? 'Worded by the local model, checked against your data' : source === 'safety' ? 'Safety response' : 'From your data'
  return (
    <div className="mt-1.5 text-[11px] text-slate-400">
      <button onClick={() => setOpen(o => !o)} className="hover:text-slate-600">{by}{ev.length ? ` · ${ev.length} source${ev.length > 1 ? 's' : ''}` : ''}{ev.length ? (open ? ' ▴' : ' ▾') : ''}</button>
      {open && <ul className="mt-1 space-y-0.5">{ev.map((e, i) => <li key={i}><span className="text-slate-500">{LEVEL[e.level] ?? e.level} · {e.label}</span>: {e.detail}</li>)}</ul>}
    </div>
  )
}

/** Grounded chat (full Advisor page and the slide-up sheet). Conversation history lives on the server, per meal. */
export default function AdvisorChat({ mealId, prompts, initialPrompt, compact = false }: { mealId: number | null; prompts: string[]; initialPrompt?: string | null; compact?: boolean }) {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [thread, setThread] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<{ msg: string; retry: string } | null>(null)
  const end = useRef<HTMLDivElement>(null)
  const sent = useRef<string | null>(null)
  useEffect(() => {
    setLoading(true)
    api<any>(`/advisor/threads${mealId ? `?meal_id=${mealId}` : ''}`).then(t => { setMsgs(t.messages); setThread(t.thread_id) }).catch(() => {}).finally(() => setLoading(false))
  }, [mealId])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [msgs, busy])

  const send = async (m: string) => {
    if (!m.trim() || busy) return
    setErr(null); setText(''); setBusy(true)
    setMsgs(x => [...x, { role: 'user', content: m, created_at: new Date().toISOString() }])
    try {
      const r = await api<any>('/advisor/chat', { method: 'POST', json: { message: m, meal_id: mealId, thread_id: thread, tz_offset_min: tzOffset() } })
      setThread(r.thread_id)
      setMsgs(x => [...x, { role: 'assistant', content: r.reply, created_at: new Date().toISOString(), source: r.source, evidence: r.evidence, followups: r.followups, hypothetical: r.hypothetical }])
    } catch (e: any) { setMsgs(x => x.slice(0, -1)); setErr({ msg: e.message, retry: m }) } finally { setBusy(false) }
  }
  useEffect(() => { if (!loading && initialPrompt && sent.current !== initialPrompt) { sent.current = initialPrompt; send(initialPrompt) } })  // eslint-disable-line react-hooks/exhaustive-deps
  const clear = async () => { if (thread) await api(`/advisor/threads/${thread}`, { method: 'DELETE' }).catch(() => {}); setMsgs([]); setThread(null) }
  const submit = (e: FormEvent) => { e.preventDefault(); send(text) }
  const last = [...msgs].reverse().find(m => m.role === 'assistant')
  const chips = busy ? [] : (last?.followups?.length ? last.followups : prompts)

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className={`flex-1 min-h-0 overflow-y-auto ${compact ? 'px-4 py-4' : 'py-5'} space-y-4`}>
        {loading ? <div className="grid place-items-center py-10"><Spinner /></div>
          : msgs.length === 0 && <div className="text-center pt-8 px-4">
            <p className="text-slate-800 font-medium">How can I help with {mealId ? 'this meal' : 'your meals'}?</p>
            <p className="mt-1 text-sm text-slate-500">I answer from your logged meals, the food recognition results and the food table.</p></div>}
        {msgs.map((m, i) => m.role === 'user' ? (
          <div key={i} className="flex flex-col items-end">
            <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 text-white px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-line">{m.content}</div>
            {m.created_at && <span className="mt-1 text-[10px] text-slate-400">{time(m.created_at)}</span>}
          </div>) : (
          <div key={i} className="max-w-[92%]">
            {m.hypothetical && <div className="mb-1 text-[11px] font-medium text-amber-700">Hypothetical · not saved</div>}
            <div className="text-[15px] leading-relaxed text-slate-800 whitespace-pre-line">{m.content}</div>
            <Sources ev={m.evidence ?? []} source={m.source} />
            {m.created_at && <span className="text-[10px] text-slate-400">{time(m.created_at)}</span>}
          </div>))}
        {busy && <div className="flex items-center gap-2 text-sm text-slate-500"><Spinner className="size-4" />Checking your data…</div>}
        {err && <div className="text-sm text-rose-600 flex items-center gap-2">{err.msg}
          <button onClick={() => send(err.retry)} className="inline-flex items-center gap-1 underline"><RotateCcw className="size-3.5" />Retry</button></div>}
        <div ref={end} />
      </div>
      <div className={`space-y-2 ${compact ? 'px-4 pb-4 pt-2 border-t border-slate-100' : 'pb-2'}`}>
        {chips.length > 0 && <div className="flex gap-1.5 overflow-x-auto no-scrollbar">{chips.map(s => (
          <button key={s} onClick={() => send(s)} className="shrink-0 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[13px] text-slate-700 hover:border-brand-500">{s}</button>))}</div>}
        <form onSubmit={submit} className="flex items-center gap-1.5 rounded-2xl border border-slate-200 bg-white p-1.5 focus-within:border-brand-500">
          <input className="flex-1 bg-transparent px-2.5 py-2 text-[15px] outline-none" placeholder="Ask about your meals…" value={text} onChange={e => setText(e.target.value)} maxLength={500} aria-label="Message" />
          <button className="size-9 grid place-items-center rounded-xl bg-brand-600 text-white disabled:opacity-40" disabled={busy || !text.trim()} aria-label="Send"><ArrowUp className="size-4" /></button>
        </form>
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
          <span>Estimates for education, not medical advice.{mealId && <> <Link to={`/meals/${mealId}`} className="underline hover:text-slate-600">Open meal</Link></>}</span>
          {msgs.length > 0 && <button onClick={clear} className="inline-flex items-center gap-1 hover:text-slate-600" aria-label="Clear conversation"><Trash2 className="size-3.5" />Clear</button>}
        </div>
      </div>
    </div>
  )
}
