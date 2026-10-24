import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Bot, Maximize2, MessageCircle, X } from 'lucide-react'
import { useAdvisor } from '../lib/advisor'
import AdvisorChat, { PROMPTS } from './AdvisorChat'

/** Floating "Ask" button on every page + slide-up chat sheet that knows which page / meal you are on. */
export default function AdvisorSheet() {
  const { open, openAdvisor, close, mealId, takePrompt } = useAdvisor()
  const loc = useLocation()
  const [initial, setInitial] = useState<string | null>(null)
  useEffect(() => { if (open) setInitial(takePrompt()) }, [open])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { close() }, [loc.pathname])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { document.body.style.overflow = open ? 'hidden' : ''; return () => { document.body.style.overflow = '' } }, [open])
  if (loc.pathname.startsWith('/advisor')) return null
  const page = mealId ? 'meal' : /^\/(history|insights)/.test(loc.pathname) ? 'week' : 'today'
  const prompts = page === 'meal' ? [...PROMPTS.meal, PROMPTS.today[0]] : page === 'week' ? [...PROMPTS.week, PROMPTS.today[0]] : [...PROMPTS.today, PROMPTS.week[0]]
  return (<>
    {!open && <button onClick={() => openAdvisor()} aria-label="Ask the Meal Advisor"
      className="fixed right-4 bottom-24 md:bottom-6 z-30 flex items-center gap-2 rounded-full bg-brand-600 text-white pl-3.5 pr-4 py-3 shadow-lg shadow-brand-600/30 hover:bg-brand-700 active:scale-95 transition">
      <MessageCircle className="size-5" /><span className="text-sm font-semibold">{mealId ? 'Ask about this meal' : 'Ask'}</span>
    </button>}
    {open && <div className="fixed inset-0 z-50 flex items-end md:items-stretch md:justify-end" role="dialog" aria-modal="true" aria-label="Meal Advisor">
      <div className="absolute inset-0 bg-black/40" onClick={close} />
      <div className="relative w-full md:max-w-md h-[85dvh] md:h-full flex flex-col rounded-t-3xl md:rounded-none bg-slate-50 shadow-2xl pb-[env(safe-area-inset-bottom)]">
        <div className="shrink-0 bg-white rounded-t-3xl md:rounded-none border-b border-slate-100 px-4 pt-2 pb-3">
          <div className="mx-auto mb-2 h-1.5 w-10 rounded-full bg-slate-300 md:hidden" />
          <div className="flex items-center gap-2">
            <span className="size-9 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><Bot className="size-5" /></span>
            <div className="flex-1 min-w-0"><div className="font-semibold text-slate-800">Meal Advisor</div>
              <div className="text-[11px] text-slate-500 truncate">{mealId ? `About meal #${mealId} · ` : ''}grounded in your meals · not medical advice</div></div>
            <Link to={mealId ? `/advisor?meal=${mealId}` : '/advisor'} className="size-9 grid place-items-center rounded-full hover:bg-slate-100" aria-label="Open full screen"><Maximize2 className="size-4" /></Link>
            <button onClick={close} className="size-9 grid place-items-center rounded-full hover:bg-slate-100" aria-label="Close"><X className="size-5" /></button>
          </div>
        </div>
        <div className="flex-1 min-h-0"><AdvisorChat key={mealId ?? 'general'} mealId={mealId} prompts={prompts} initialPrompt={initial} compact /></div>
      </div>
    </div>}
  </>)
}
