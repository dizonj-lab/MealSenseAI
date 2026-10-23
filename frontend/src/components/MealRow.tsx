import { Link } from 'react-router-dom'
import { ChevronRight, ImageIcon, Utensils } from 'lucide-react'
import { fmt } from '../lib/api'
import { LevelBadge } from './ui'

export default function MealRow({ m }: { m: any }) {
  const kcal = m.calories_kcal ?? m.totals?.calories_kcal, carbs = m.carbs_g ?? m.totals?.carbs_g
  return (
    <Link to={`/meals/${m.id}`} className="flex items-center gap-3 py-3 px-1 hover:bg-slate-50 rounded-xl">
      <span className="size-10 rounded-xl bg-brand-50 text-brand-600 grid place-items-center shrink-0">{m.has_image ? <ImageIcon className="size-5" /> : <Utensils className="size-5" />}</span>
      <div className="min-w-0 flex-1">
        <div className="font-medium text-slate-800 truncate">{m.labels.join(', ') || 'Meal'}</div>
        <div className="text-xs text-slate-500"><span className="capitalize">{m.meal_type ?? 'meal'}</span> · {new Date(m.eaten_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {fmt(kcal)} kcal · {fmt(carbs)} g carbs{m.status !== 'confirmed' && ' · draft'}</div>
      </div>
      <LevelBadge level={m.glucose_level} />
      <ChevronRight className="size-4 text-slate-300" />
    </Link>
  )
}
