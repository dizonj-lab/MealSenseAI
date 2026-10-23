import { useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Pencil, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import type { Meal } from '../lib/types'
import MealReview from '../components/MealReview'
import { ErrorNote, Spinner } from '../components/ui'

export default function MealDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const loc = useLocation()
  const { data: meal, error, setData } = useApi<Meal>(`/meals/${id}`)
  const [edit, setEdit] = useState(false)
  if (error) return <ErrorNote msg={error} />
  if (!meal) return <div className="grid place-items-center py-20"><Spinner /></div>
  const del = async () => { if (confirm('Delete this meal permanently?')) { await api(`/meals/${meal.id}`, { method: 'DELETE' }); nav('/history') } }
  return (
    <div className="space-y-4">
      {(loc.state as any)?.saved && !edit && <div className="rounded-2xl bg-emerald-50 ring-1 ring-emerald-200 p-3 text-sm text-emerald-800 flex gap-2"><CheckCircle2 className="size-5" />Meal saved to your history.</div>}
      <div className="flex flex-wrap items-center gap-2">
        <div><div className="text-lg font-semibold capitalize">{meal.meal_type ?? 'Meal'}</div>
          <div className="text-sm text-slate-500">{new Date(meal.eaten_at).toLocaleString()} · <span className="capitalize">{meal.status}</span></div></div>
        <div className="ml-auto flex gap-2">
          <button className="btn-ghost" onClick={() => setEdit(e => !e)}><Pencil className="size-4" />{edit ? 'Done' : 'Edit'}</button>
          <button className="btn-ghost text-rose-600" onClick={del}><Trash2 className="size-4" />Delete</button>
        </div>
      </div>
      <MealReview meal={meal} onChange={setData} readOnly={!edit && meal.status === 'confirmed'} onSaved={() => setEdit(false)} />
    </div>
  )
}
