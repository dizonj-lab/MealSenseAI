import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Camera, Salad, TrendingUp } from 'lucide-react'
import { fmt, tzOffset } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useApi } from '../lib/hooks'
import AskCard from '../components/AskCard'
import GettingStarted from '../components/GettingStarted'
import MealRow from '../components/MealRow'
import { Card, Empty, Progress, Spinner, Stat } from '../components/ui'

export const MACRO_COLORS = { carbs: '#0ea5e9', protein: '#10b981', fat: '#f59e0b' }
const day = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString([], { weekday: 'short' })

export default function Dashboard() {
  const { user } = useAuth()
  const { data: d } = useApi<any>(`/dashboard/summary?tz_offset_min=${tzOffset()}`)
  if (!d) return <div className="grid place-items-center py-20"><Spinner /></div>
  const t = d.today, g = d.goals
  const macro = Object.entries(d.macro_energy_pct).map(([k, v]) => ({ name: k, value: v as number }))
  const goalRows = [['Calories', t.calories_kcal, g.calorie_goal, 'kcal'], ['Carbohydrate', t.carbs_g, g.carb_goal_g, 'g'], ['Protein', t.protein_g, g.protein_goal_g, 'g']].filter(r => r[2])
  return (
    <div className="space-y-4">
      <div className="card p-5 bg-gradient-to-br from-brand-600 to-sky-600 text-white border-0 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1"><div className="text-white/80 text-sm">{new Date().toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long' })}</div>
          <div className="text-xl font-bold mt-0.5">Hi {user?.name || 'there'} 👋</div>
          <div className="text-white/85 text-sm mt-1">{t.meals ? `${t.meals} meal(s) logged today.` : 'No meals logged yet today.'}</div></div>
        <Link to="/capture" className="btn bg-white text-brand-700 hover:bg-brand-50 py-3 px-5 text-base shadow"><Camera className="size-5" />Capture Meal</Link>
      </div>

      <GettingStarted totalMeals={d.total_meals} confirmed={d.recent_meals.some((m: any) => m.status === 'confirmed')} />
      {d.total_meals > 0 && <AskCard title="Ask your Meal Advisor" prompts={['How am I doing today?', 'How was my week?', 'Any advice for my next meal?']} />}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Calories today" value={fmt(t.calories_kcal)} unit="kcal" tone="teal" sub={g.calorie_goal && `of ${g.calorie_goal} goal`} />
        <Stat label="Carbohydrates" value={fmt(t.carbs_g)} unit="g" tone="blue" sub={g.carb_goal_g && `of ${g.carb_goal_g} g goal`} />
        <Stat label="Protein" value={fmt(t.protein_g)} unit="g" tone="green" sub={g.protein_goal_g && `of ${g.protein_goal_g} g goal`} />
        <Stat label="Meals today" value={t.meals} sub={`${d.total_meals} total logged`} />
      </div>

      {d.total_meals === 0 ? <Card><Empty icon={<Salad className="size-6" />} title="Your nutrition story starts with one photo">
        Capture your first meal — top view, optional side view — and MealSenseAI will identify foods it supports, estimate portions with honest uncertainty, and show composition-based insights. Charts appear here once you save meals.
        <div className="mt-4"><Link to="/capture" className="btn-primary"><Camera className="size-4" />Capture first meal</Link></div></Empty></Card> : <>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="7-day calories" icon={<TrendingUp className="size-5 text-brand-600" />} className="lg:col-span-2">
            <div className="h-56"><ResponsiveContainer><BarChart data={d.trend} margin={{ left: -20, right: 4 }}>
              <CartesianGrid vertical={false} stroke="#f1f5f9" /><XAxis dataKey="date" tickFormatter={day} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={day} formatter={(v: number) => [`${v} kcal`, 'Calories']} />
              <Bar dataKey="calories_kcal" fill="#14b8a6" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </Card>
          <Card title="Today's macro energy">
            {macro.length ? <><div className="h-40"><ResponsiveContainer><PieChart><Pie data={macro} dataKey="value" isAnimationActive={false} innerRadius={45} outerRadius={70} paddingAngle={2}>
              {macro.map(m => <Cell key={m.name} fill={MACRO_COLORS[m.name as keyof typeof MACRO_COLORS]} />)}</Pie><Tooltip formatter={(v: number) => `${v}%`} /></PieChart></ResponsiveContainer></div>
              <div className="flex justify-around text-xs">{macro.map(m => <span key={m.name} className="capitalize"><i className="inline-block size-2 rounded-full mr-1" style={{ background: MACRO_COLORS[m.name as keyof typeof MACRO_COLORS] }} />{m.name} {m.value}%</span>)}</div></>
              : <p className="text-sm text-slate-500 py-10 text-center">No meals today yet.</p>}
          </Card>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="Recent meals" className="lg:col-span-2" action={<Link to="/history" className="text-sm text-brand-700 font-medium">View all</Link>}>
            <div className="divide-y divide-slate-100">{d.recent_meals.map((m: any) => <MealRow key={m.id} m={m} />)}</div>
          </Card>
          <Card title="Daily goals">
            {goalRows.length ? <div className="space-y-3">{goalRows.map(([l, v, goal, u]) => { const pct = Math.round((v as number) / (goal as number) * 100); return (
              <div key={l as string}><div className="flex justify-between text-sm mb-1"><span>{l}</span><span className="text-slate-500">{fmt(v as number)} / {goal} {u}</span></div><Progress pct={pct} /></div>) })}</div>
              : <p className="text-sm text-slate-500">No daily goals set. <Link to="/profile" className="text-brand-700 font-medium">Add optional goals</Link></p>}
          </Card>
        </div></>}
    </div>
  )
}
