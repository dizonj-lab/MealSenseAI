import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Rocket, X } from 'lucide-react'
import { api } from '../lib/api'

const KEY = 'mealsense.gs.dismissed'
export const markSimulatorTried = () => { try { localStorage.setItem('mealsense.gs.sim', '1') } catch { /* private mode */ } }
const flag = (k: string) => { try { return localStorage.getItem(k) === '1' } catch { return false } }

/** First-run checklist for new accounts; progress comes from the user's own data. Dismissible. */
export default function GettingStarted({ totalMeals, confirmed }: { totalMeals: number; confirmed: boolean }) {
  const [hidden, setHidden] = useState(() => flag(KEY))
  const [readings, setReadings] = useState(false)
  useEffect(() => { if (!hidden) api<any[]>('/glucose?days=365').then(r => setReadings(r.length > 0)).catch(() => {}) }, [hidden])
  const steps: [string, string, boolean, string?][] = [
    ['Set up your health profile', 'Goals and optional health details shape your insights.', true, '/profile'],
    ['Capture your first meal', 'One top-view photo is enough.', totalMeals > 0, '/capture'],
    ['Check and save it', 'Name any unrecognised item, adjust portions, then save.', confirmed, '/capture'],
    ['Try the portion simulator', 'See how a smaller portion changes carbs and the simulated curve.', flag('mealsense.gs.sim')],
    ['Log a glucose reading (optional)', 'If you use a meter or CGM, add a reading under the portion simulator.', readings],
  ]
  const done = steps.filter(s => s[2]).length
  if (hidden || done === steps.length) return null
  const dismiss = () => { setHidden(true); try { localStorage.setItem(KEY, '1') } catch { /* private mode */ } }
  return (
    <section className="card p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <span className="size-9 shrink-0 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><Rocket className="size-5" /></span>
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-slate-800">Getting started</h2>
          <p className="text-xs text-slate-500">{done} of {steps.length} done</p>
        </div>
        <button onClick={dismiss} className="size-9 grid place-items-center rounded-full text-slate-400 hover:bg-slate-100" aria-label="Hide getting started"><X className="size-4" /></button>
      </div>
      <div className="mt-3 h-1.5 rounded-full bg-slate-100 overflow-hidden"><div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${done / steps.length * 100}%` }} /></div>
      <ol className="mt-3 space-y-2.5">{steps.map(([t, b, ok, to]) => (
        <li key={t} className="flex gap-3">
          <span className={`mt-0.5 size-5 shrink-0 rounded-full grid place-items-center ${ok ? 'bg-emerald-500 text-white' : 'ring-2 ring-slate-300'}`}>{ok && <Check className="size-3.5" />}</span>
          <div className="min-w-0">
            {to && !ok ? <Link to={to} className="text-sm font-semibold text-brand-700">{t}</Link> : <span className={`text-sm font-semibold ${ok ? 'text-slate-400 line-through' : 'text-slate-800'}`}>{t}</span>}
            {!ok && <p className="text-xs text-slate-500">{b}</p>}
          </div>
        </li>))}</ol>
    </section>
  )
}
