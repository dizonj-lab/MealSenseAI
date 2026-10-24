import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Bot, Send, ShieldCheck, Trash2, User as UserIcon } from 'lucide-react'
import { api, tzOffset } from '../lib/api'
import { Spinner } from './ui'

type Msg = { role: 'user' | 'assistant'; content: string; source?: string; grounding?: { kind: string; label: string; detail: string }[] }
const SRC: Record<string, string> = { rules: 'Rule engine', safety: 'Safety reply' }
export const PROMPTS: Record<string, string[]> = {
  meal: ['Is this meal OK for my goal?', 'Which food adds the most carbs?', 'Suggest a lower-carb swap for this meal'],
  today: ['How am I doing today?', 'Any advice for my next meal?', 'How many carbs in chicken rice?'],
  week: ['How was my week?', "What's my trajectory? Any advice?", 'What are my biggest carb sources?'],
}

/** Grounded chat used by the full Advisor page and the slide-up sheet. History is kept per context for this session. */
export default function AdvisorChat({ mealId, prompts, initialPrompt, compact = false }: { mealId: number | null; prompts: string[]; initialPrompt?: string | null; compact?: boolean }) {
  const key = `mealsense.advisor.${mealId ?? 'general'}`
  const [msgs, setMsgs] = useState<Msg[]>(() => { try { return JSON.parse(sessionStorage.getItem(key) || '[]') } catch { return [] } })
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const end = useRef<HTMLDivElement>(null)
  const sent = useRef<string | null>(null)
  useEffect(() => { try { setMsgs(JSON.parse(sessionStorage.getItem(key) || '[]')) } catch { setMsgs([]) } }, [key])
  useEffect(() => { try { sessionStorage.setItem(key, JSON.stringify(msgs)) } catch { /* private mode */ } end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [msgs, key])

  const send = async (m: string) => {
    if (!m.trim() || busy) return
    setErr(null); setText(''); setBusy(true)
    const history = msgs.map(({ role, content }) => ({ role, content }))
    setMsgs(x => [...x, { role: 'user', content: m }])
    try {
      const r = await api<any>('/advisor/chat', { method: 'POST', json: { message: m, history, meal_id: mealId, tz_offset_min: tzOffset() } })
      setMsgs(x => [...x, { role: 'assistant', content: r.reply, source: r.source, grounding: r.grounding }])
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  useEffect(() => { if (initialPrompt && sent.current !== initialPrompt) { sent.current = initialPrompt; send(initialPrompt) } })  // eslint-disable-line react-hooks/exhaustive-deps
  const submit = (e: FormEvent) => { e.preventDefault(); send(text) }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className={`flex-1 min-h-0 overflow-y-auto space-y-3 ${compact ? 'px-4 py-3' : 'py-4'}`}>
        {msgs.length === 0 && <div className="text-center text-sm text-slate-500 pt-4">Ask about {mealId ? 'this meal' : 'your day, your week or any food'}. Answers use only your saved meals, goals and the food table.</div>}
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && <span className="size-7 shrink-0 rounded-lg bg-brand-50 text-brand-700 grid place-items-center"><Bot className="size-4" /></span>}
            <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm whitespace-pre-line ${m.role === 'user' ? 'bg-brand-600 text-white rounded-br-md' : 'bg-white ring-1 ring-slate-200 rounded-bl-md text-slate-700'}`}>
              {m.content}
              {m.role === 'assistant' && <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400">
                {m.source === 'safety' ? <span className="chip bg-amber-50 text-amber-700"><ShieldCheck className="size-3" />Safety reply</span>
                  : <span>{m.source?.startsWith('slm:') ? `Local SLM (${m.source.slice(4)})` : SRC[m.source ?? ''] ?? m.source}</span>}
                {!!m.grounding?.length && <details className="w-full"><summary className="cursor-pointer">Based on {m.grounding.length} source(s)</summary>
                  <ul className="mt-1 space-y-0.5">{m.grounding.map((g, j) => <li key={j}><b className="font-medium text-slate-500">{g.label}:</b> {g.detail}</li>)}</ul></details>}
              </div>}
            </div>
            {m.role === 'user' && <span className="size-7 shrink-0 rounded-lg bg-slate-100 text-slate-500 grid place-items-center"><UserIcon className="size-4" /></span>}
          </div>))}
        {busy && <div className="flex gap-2 items-center text-sm text-slate-500"><Spinner className="size-4" />Looking at your data…</div>}
        {err && <p className="text-sm text-rose-600">{err}</p>}
        <div ref={end} />
      </div>
      <div className={`space-y-2 ${compact ? 'px-4 pb-4 pt-2 border-t border-slate-100' : 'pb-2'}`}>
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar">{prompts.map(s => (
          <button key={s} onClick={() => send(s)} disabled={busy} className="chip shrink-0 bg-white ring-1 ring-slate-200 text-slate-700 px-3 py-1.5">{s}</button>))}
          {msgs.length > 0 && <button onClick={() => setMsgs([])} className="chip shrink-0 text-slate-400 px-2" aria-label="Clear conversation"><Trash2 className="size-3.5" /></button>}</div>
        <form onSubmit={submit} className="flex gap-1.5 rounded-2xl bg-white ring-1 ring-slate-200 p-1.5">
          <input className="input border-0 focus:ring-0 flex-1 bg-transparent" placeholder="Ask about a food or your meals…" value={text} onChange={e => setText(e.target.value)} maxLength={500} aria-label="Message" />
          <button className="btn-primary px-3" disabled={busy || !text.trim()} aria-label="Send"><Send className="size-4" /></button>
        </form>
      </div>
    </div>
  )
}
