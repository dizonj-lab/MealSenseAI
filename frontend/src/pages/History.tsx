import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarDays, Camera } from 'lucide-react'
import { fmt, tzOffset } from '../lib/api'
import { useApi } from '../lib/hooks'
import MealRow from '../components/MealRow'
import { Card, Empty, Spinner } from '../components/ui'

const iso = (d: Date) => d.toISOString().slice(0, 10)

export default function History() {
  const [start, setStart] = useState(iso(new Date(Date.now() - 13 * 864e5)))
  const [end, setEnd] = useState(iso(new Date()))
  const { data } = useApi<any>(`/meals/history?start=${start}&end=${end}&tz_offset_min=${tzOffset()}`)
  const local = (m: any) => { const d = new Date(m.eaten_at); return iso(new Date(d.getTime() - d.getTimezoneOffset() * 6e4)) }
  return (
    <div className="space-y-4">
      <div className="card p-3 flex flex-wrap items-end gap-3">
        <CalendarDays className="size-5 text-brand-600 mb-2.5" />
        <label className="block"><span className="label">From</span><input type="date" className="input py-2" value={start} max={end} onChange={e => setStart(e.target.value)} /></label>
        <label className="block"><span className="label">To</span><input type="date" className="input py-2" value={end} min={start} onChange={e => setEnd(e.target.value)} /></label>
      </div>
      {!data ? <div className="grid place-items-center py-16"><Spinner /></div> : data.days.length === 0 ?
        <Card><Empty icon={<Camera className="size-6" />} title="No meals in this range">Captured meals appear here. <Link className="text-brand-700 font-medium" to="/capture">Capture a meal</Link></Empty></Card> :
        data.days.map((d: any) => (
          <Card key={d.date} title={new Date(d.date + 'T00:00:00').toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'short' })}
            action={<span className="text-xs text-slate-500 text-right">{fmt(d.calories_kcal)} kcal · C {fmt(d.carbs_g)} g · P {fmt(d.protein_g)} g · F {fmt(d.fat_g)} g</span>}>
            <div className="divide-y divide-slate-100">{data.meals.filter((m: any) => local(m) === d.date).map((m: any) => <MealRow key={m.id} m={m} />)}</div>
          </Card>))}
    </div>
  )
}
