import type { ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

export const Spinner = ({ className = 'size-6' }: { className?: string }) => <Loader2 className={`animate-spin text-brand-600 ${className}`} />

export function Card({ title, icon, action, children, className = '' }: { title?: ReactNode; icon?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-4 sm:p-5 ${className}`}>
      {title && <header className="flex items-center justify-between mb-3 gap-2">
        <h2 className="flex items-center gap-2 font-semibold text-slate-800">{icon}{title}</h2>{action}
      </header>}
      {children}
    </section>
  )
}

export function Stat({ label, value, unit, sub, tone = 'slate' }: { label: string; value: ReactNode; unit?: string; sub?: ReactNode; tone?: string }) {
  const tones: Record<string, string> = { slate: 'text-slate-900', teal: 'text-teal-700', blue: 'text-sky-700', green: 'text-emerald-700', amber: 'text-amber-700' }
  return (
    <div className="card p-3.5">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold tracking-tight ${tones[tone]}`}>{value}<span className="ml-1 text-sm font-medium text-slate-400">{unit}</span></div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  )
}

export function Progress({ pct, tone = 'bg-brand-500' }: { pct: number; tone?: string }) {
  return <div className="h-2 rounded-full bg-slate-100 overflow-hidden"><div className={`h-full rounded-full ${pct > 100 ? 'bg-amber-500' : tone}`} style={{ width: `${Math.min(pct, 100)}%` }} /></div>
}

const LEVEL: Record<string, string> = {
  LOW: 'bg-emerald-50 text-emerald-700 ring-emerald-200', MODERATE: 'bg-amber-50 text-amber-700 ring-amber-200',
  HIGH: 'bg-rose-50 text-rose-700 ring-rose-200', UNCERTAIN: 'bg-slate-100 text-slate-600 ring-slate-200',
}
export const LevelBadge = ({ level }: { level?: string | null }) =>
  level ? <span className={`chip ring-1 ${LEVEL[level] || LEVEL.UNCERTAIN}`}>{level}</span> : null

export const Empty = ({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) => (
  <div className="text-center py-8 px-4">
    <div className="mx-auto mb-3 size-12 rounded-2xl bg-brand-50 text-brand-600 grid place-items-center">{icon}</div>
    <div className="font-semibold text-slate-800">{title}</div>
    <div className="mt-1 text-sm text-slate-500">{children}</div>
  </div>
)

export const ErrorNote = ({ msg }: { msg: string | null }) => msg ? <div className="rounded-xl bg-rose-50 text-rose-700 text-sm px-3 py-2 ring-1 ring-rose-200">{msg}</div> : null

export function Toggle({ options, value, onChange, multi = false }: { options: [string, string][]; value: string | string[] | null; onChange: (v: any) => void; multi?: boolean }) {
  const sel = (k: string) => (multi ? (value as string[]).includes(k) : value === k)
  const click = (k: string) => multi ? onChange(sel(k) ? (value as string[]).filter(x => x !== k) : [...(value as string[]), k]) : onChange(sel(k) ? null : k)
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(([k, l]) => (
        <button type="button" key={k} onClick={() => click(k)}
          className={`rounded-xl px-3 py-2 text-sm font-medium border transition ${sel(k) ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-slate-600 border-slate-200 hover:border-brand-500'}`}>{l}</button>
      ))}
    </div>
  )
}
