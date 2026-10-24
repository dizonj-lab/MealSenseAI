import { useSearchParams } from 'react-router-dom'
import { Bot, X } from 'lucide-react'
import AdvisorChat, { PROMPTS } from '../components/AdvisorChat'
import { InfoTip } from '../components/ui'

/** Full-screen Meal Advisor (the same chat also opens as a sheet from the Ask button on every page). */
export default function Advisor() {
  const [params, setParams] = useSearchParams()
  const mealId = params.get('meal') ? Number(params.get('meal')) : null
  return (
    <div className="max-w-2xl mx-auto flex flex-col h-[calc(100dvh-10.5rem)] md:h-[calc(100dvh-8rem)]">
      <div className="card p-4 flex items-start gap-3 shrink-0">
        <span className="size-10 shrink-0 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><Bot className="size-5" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-slate-800 flex items-center gap-1">Meal Advisor
            <InfoTip label="Meal Advisor" text="Answers only from your saved meals, your profile and goals, the food table (including your own foods) and what the photo model recognises. Each reply lists what it used. It never gives medication or insulin advice." /></h2>
          <p className="text-xs text-slate-500">Grounded in your meals and the food table · not medical advice</p>
          {mealId && <span className="mt-2 chip bg-brand-50 text-brand-700">About meal #{mealId}
            <button aria-label="Stop discussing this meal" onClick={() => setParams({})}><X className="size-3.5" /></button></span>}
        </div>
      </div>
      <AdvisorChat mealId={mealId} prompts={mealId ? [...PROMPTS.meal, PROMPTS.today[0]] : [...PROMPTS.today.slice(0, 1), ...PROMPTS.week]} />
    </div>
  )
}
