import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Bot, Send, ShieldCheck, User as UserIcon, X } from 'lucide-react'
import { api, tzOffset } from '../lib/api'
import { InfoTip, Spinner } from '../components/ui'

type Msg = { role: 'user' | 'assistant'; content: string; source?: string; grounding?: { kind: string; label: string; detail: string }[] }
const GENERAL = ['How am I doing today?', 'How many carbs in chicken rice?', "What's a lower-carb swap for nasi lemak?", 'How was my week?']
const MEAL = ['Is this meal OK for my goal?', 'Which food adds the most carbs?', 'Suggest a lower-carb swap for this meal']
const SRC: Record<string, string> = { rules: 'Rule engine', safety: 'Safety reply' }

/** Meal Advisor chat: answers come only from the user's logged meals, profile and the food table. */
export default function Advisor() {
  const [params, setParams] = useSearchParams()
  const mealId = params.get('meal') ? Number(params.get('meal')) : null
  const key = `mealsense.advisor.${mealId ?? 'general'}`
  const [msgs, setMsgs] = useState<Msg[]>(() => { try { return JSON.parse(sessionStorage.getItem(key) || '[]') } catch { return [] } })
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { try { sessionStorage.setItem(key, JSON.stringify(msgs)) } catch { /* private mode */ } end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, key])

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
  const submit = (e: FormEvent) => { e.preventDefault(); send(text) }

  return (
    <div className="max-w-2xl mx-auto flex flex-col min-h-[calc(100dvh-9rem)] md:min-h-[calc(100dvh-7rem)]">
      <div className="card p-4 flex items-start gap-3">
        <span className="size-10 shrink-0 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><Bot className="size-5" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-slate-800 flex items-center gap-1">Meal Advisor
            <InfoTip label="Meal Advisor" text="Answers only from your saved meals, your profile and goals, the food table (including your own foods) and what the photo model recognises. Each reply lists what it used. It never gives medication or insulin advice." /></h2>
          <p className="text-xs text-slate-500">Grounded in your meals and the food table · not medical advice</p>
          {mealId && <span className="mt-2 chip bg-brand-50 text-brand-700">About meal #{mealId}
            <button aria-label="Stop discussing this meal" onClick={() => setParams({})}><X className="size-3.5" /></button></span>}
        </div>
      </div>

      <div className="flex-1 py-4 space-y-3">
        {msgs.length === 0 && <div className="text-center text-sm text-slate-500 pt-6">Ask about a food, your day, or {mealId ? 'this meal' : 'a meal you logged'}.</div>}
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && <span className="size-7 shrink-0 rounded-lg bg-brand-50 text-brand-700 grid place-items-center"><Bot className="size-4" /></span>}
            <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm whitespace-pre-line ${m.role === 'user' ? 'bg-brand-600 text-white rounded-br-md' : 'card rounded-bl-md text-slate-700'}`}>
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
        {busy && <div className="flex gap-2 items-center text-sm text-slate-500"><Spinner className="size-4" />Thinking with your data…</div>}
        {err && <p className="text-sm text-rose-600">{err}</p>}
        <div ref={end} />
      </div>

      <div className="sticky bottom-20 md:bottom-4 space-y-2">
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar">{(mealId ? [...MEAL, ...GENERAL.slice(0, 1)] : GENERAL).map(s => (
          <button key={s} onClick={() => send(s)} disabled={busy} className="chip shrink-0 bg-white ring-1 ring-slate-200 text-slate-700 px-3 py-1.5">{s}</button>))}</div>
        <form onSubmit={submit} className="card p-1.5 flex gap-1.5">
          <input className="input border-0 focus:ring-0 flex-1" placeholder="Ask about a food or your meals…" value={text} onChange={e => setText(e.target.value)} maxLength={500} aria-label="Message" />
          <button className="btn-primary px-3" disabled={busy || !text.trim()} aria-label="Send"><Send className="size-4" /></button>
        </form>
      </div>
    </div>
  )
}
