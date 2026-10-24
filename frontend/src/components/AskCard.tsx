import { MessageCircle } from 'lucide-react'
import { useAdvisor } from '../lib/advisor'

/** One-tap questions for the Meal Advisor, placed where they are most useful. */
export default function AskCard({ title, prompts }: { title: string; prompts: string[] }) {
  const { openAdvisor } = useAdvisor()
  return (
    <section className="card p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><MessageCircle className="size-4 text-brand-700" />{title}</div>
      <div className="mt-2.5 flex gap-1.5 overflow-x-auto no-scrollbar">{prompts.map(q => (
        <button key={q} onClick={() => openAdvisor({ prompt: q, mealId: null })} className="chip shrink-0 bg-brand-50 text-brand-700 px-3 py-1.5">{q}</button>))}</div>
    </section>
  )
}
