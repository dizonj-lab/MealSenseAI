import { useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BarChart3 } from 'lucide-react'
import { fmt, tzOffset } from '../lib/api'
import { useApi } from '../lib/hooks'
import { Card, Empty, Spinner, Stat, Toggle } from '../components/ui'
import { MACRO_COLORS } from './Dashboard'

export default function NutritionInsights() {
  const [days, setDays] = useState('7')
  const { data: d } = useApi<any>(`/dashboard/summary?tz_offset_min=${tzOffset()}&days=${days}`)
  if (!d) return <div className="grid place-items-center py-20"><Spinner /></div>
  const logged = d.trend.filter((x: any) => x.meals > 0)
  const avg = (k: string) => (logged.length ? logged.reduce((s: number, x: any) => s + x[k], 0) / logged.length : null)
  const label = (s: string) => new Date(s + 'T00:00:00').toLocaleDateString([], { day: 'numeric', month: 'short' })
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2"><p className="text-sm text-slate-500">Averages over days with logged meals.</p>
        <Toggle options={[['7', '7 days'], ['30', '30 days']]} value={days} onChange={v => v && setDays(v)} /></div>
      {!logged.length ? <Card><Empty icon={<BarChart3 className="size-6" />} title="No data yet">Save a few meals to see trends.</Empty></Card> : <>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Stat label="Avg calories / day" value={fmt(avg('calories_kcal'))} unit="kcal" tone="teal" />
          <Stat label="Avg carbs / day" value={fmt(avg('carbs_g'))} unit="g" tone="blue" />
          <Stat label="Avg protein / day" value={fmt(avg('protein_g'))} unit="g" tone="green" />
          <Stat label="Avg fibre / day" value={fmt(avg('fiber_g'), 1)} unit="g" tone="amber" sub="25–30 g/day is a common general guideline" />
        </div>
        <Card title="Macronutrients per day (g)">
          <div className="h-64"><ResponsiveContainer><BarChart data={d.trend} margin={{ left: -20 }}>
            <CartesianGrid vertical={false} stroke="#f1f5f9" /><XAxis dataKey="date" tickFormatter={label} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={label} /><Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="carbs_g" name="Carbs" stackId="m" fill={MACRO_COLORS.carbs} /><Bar dataKey="protein_g" name="Protein" stackId="m" fill={MACRO_COLORS.protein} />
            <Bar dataKey="fat_g" name="Fat" stackId="m" fill={MACRO_COLORS.fat} radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </Card>
        <div className="grid lg:grid-cols-2 gap-4">
          <Card title="Sugar & fibre (g)"><div className="h-52"><ResponsiveContainer><AreaChart data={d.trend} margin={{ left: -20 }}>
            <CartesianGrid vertical={false} stroke="#f1f5f9" /><XAxis dataKey="date" tickFormatter={label} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={label} /><Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            <Area dataKey="sugar_g" name="Sugar" stroke="#f43f5e" fill="#ffe4e6" /><Area dataKey="fiber_g" name="Fibre" stroke="#10b981" fill="#d1fae5" /></AreaChart></ResponsiveContainer></div></Card>
          <Card title="Sodium (mg)"><div className="h-52"><ResponsiveContainer><BarChart data={d.trend} margin={{ left: -10 }}>
            <CartesianGrid vertical={false} stroke="#f1f5f9" /><XAxis dataKey="date" tickFormatter={label} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={label} />
            <Bar dataKey="sodium_mg" name="Sodium" fill="#6366f1" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
            <p className="text-xs text-slate-400">Values are estimates from photo-based portions and reference composition data.</p></Card>
        </div></>}
    </div>
  )
}
