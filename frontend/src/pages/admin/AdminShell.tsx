import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { ClipboardCheck, Cpu, Database, MessageSquareQuote, ScrollText, SlidersHorizontal, Users } from 'lucide-react'
import { useAuth } from '../../lib/auth'
import Review from './Review'
import Contributors from './Contributors'
import Datasets from './Datasets'
import Models from './Models'
import ModelSettings from './ModelSettings'
import Prompts from './Prompts'
import Audit from './Audit'

const TABS = [
  ['review', 'Training data review', ClipboardCheck], ['contributors', 'Contributors', Users], ['datasets', 'Dataset versions', Database],
  ['models', 'Models & updates', Cpu], ['settings', 'Model settings', SlidersHorizontal], ['prompts', 'Prompts', MessageSquareQuote],
  ['audit', 'Audit log', ScrollText],
] as const

/** Admin area. The tabs are a convenience: every admin API call is checked on the server. */
export default function AdminShell() {
  const { user } = useAuth()
  if (!user?.is_admin) return <Navigate to="/" replace />
  return (
    <div className="space-y-4">
      <nav className="flex gap-1.5 overflow-x-auto no-scrollbar -mx-1 px-1" aria-label="Admin sections">
        {TABS.map(([to, label, I]) => (
          <NavLink key={to} to={`/admin/${to}`} className={({ isActive }) => `shrink-0 inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition ${
            isActive ? 'bg-brand-600 text-white' : 'bg-white ring-1 ring-slate-200 text-slate-600 hover:ring-brand-500'}`}>
            <I className="size-4" />{label}</NavLink>))}
      </nav>
      <Routes>
        <Route index element={<Navigate to="review" replace />} />
        <Route path="review" element={<Review />} />
        <Route path="contributors" element={<Contributors />} />
        <Route path="datasets" element={<Datasets />} />
        <Route path="models" element={<Models />} />
        <Route path="settings" element={<ModelSettings />} />
        <Route path="prompts" element={<Prompts />} />
        <Route path="audit" element={<Audit />} />
        <Route path="*" element={<Navigate to="review" replace />} />
      </Routes>
    </div>
  )
}

export const ago = (iso?: string | null) => {
  if (!iso) return '—'
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  return s < 60 ? 'just now' : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`
}

const SEV: Record<string, string> = {
  reject: 'bg-rose-50 text-rose-700 ring-rose-200', flag: 'bg-amber-50 text-amber-800 ring-amber-200', info: 'bg-slate-100 text-slate-600 ring-slate-200',
}
export function ReasonChip({ r }: { r: { code: string; label: string; severity: string; detail: string } }) {
  const safety = r.code === 'lowers_carbs' || r.code === 'repeated_pattern'
  return <span title={r.detail} className={`chip ring-1 ${safety ? 'bg-rose-50 text-rose-700 ring-rose-200' : SEV[r.severity] ?? SEV.info}`}>{r.label}</span>
}
