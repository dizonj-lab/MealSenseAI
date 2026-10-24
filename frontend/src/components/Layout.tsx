import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Activity, BarChart3, Monitor, Moon, Sun, Camera, ChevronsLeft, ChevronsRight, Cpu, History, LayoutDashboard, LogOut, Menu, Settings, UserRound, X } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useTheme } from '../lib/theme'
import { api } from '../lib/api'

export const NAV = [
  { to: '/', label: 'Dashboard', short: 'Home', icon: LayoutDashboard },
  { to: '/capture', label: 'Capture Meal', short: 'Capture', icon: Camera },
  { to: '/history', label: 'Meal History', short: 'History', icon: History },
  { to: '/insights', label: 'Nutrition Insights', short: 'Insights', icon: BarChart3 },
  { to: '/profile', label: 'Health Profile', short: 'Profile', icon: UserRound },
  { to: '/ai', label: 'AI Model Insights', short: 'AI', icon: Cpu },
  { to: '/settings', label: 'Settings', short: 'Settings', icon: Settings },
]
const BOTTOM = [NAV[0], NAV[2], NAV[1], NAV[3], NAV[4]]

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/favicon.svg" className="size-8" alt="" />
      {!compact && <div className="leading-tight"><div className="font-bold text-slate-900">MealSense<span className="text-brand-600">AI</span></div><div className="text-[10px] uppercase tracking-wider text-slate-400">Nutrition intelligence</div></div>}
    </div>
  )
}

function AiStatus() {
  const [h, setH] = useState<any>(null)
  useEffect(() => { api('/health').then(setH).catch(() => setH({ status: 'down' })) }, [])
  if (!h) return null
  const ok = h.vision && h.database
  return (
    <span title={`Vision ${h.vision ? 'online' : 'offline'} · SLM ${h.slm ? h.slm_model : 'offline'}`}
      className={`chip ring-1 ${ok ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-amber-50 text-amber-700 ring-amber-200'}`}>
      <Activity className="size-3.5" aria-label={ok ? (h.slm ? 'AI online' : 'AI vision only') : 'AI degraded'} /><span className="hidden sm:inline">AI {ok ? (h.slm ? 'Online' : 'Vision only') : 'Degraded'}</span>
    </span>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [drawer, setDrawer] = useState(false)
  const loc = useLocation()
  const nav = useNavigate()
  useEffect(() => setDrawer(false), [loc.pathname])
  const current = NAV.find(n => (n.to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(n.to)))?.label ?? (loc.pathname.startsWith('/meals') ? 'Meal Details' : '')

  const links = (compact: boolean) => NAV.map(({ to, label, icon: I }) => (
    <NavLink key={to} to={to} end={to === '/'} title={label}
      className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'} ${compact ? 'justify-center' : ''}`}>
      <I className="size-5 shrink-0" />{!compact && label}
    </NavLink>
  ))

  return (
    <div className="min-h-full flex">
      <aside className={`hidden md:flex flex-col shrink-0 border-r border-slate-200 bg-white sticky top-0 h-screen transition-all ${collapsed ? 'w-[72px]' : 'w-64'}`}>
        <div className={`h-16 flex items-center px-4 ${collapsed ? 'justify-center' : ''}`}><Brand compact={collapsed} /></div>
        <nav className="flex-1 px-3 space-y-1">{links(collapsed)}</nav>
        <button onClick={() => setCollapsed(c => !c)} className="m-3 btn-ghost">{collapsed ? <ChevronsRight className="size-4" /> : <><ChevronsLeft className="size-4" />Collapse</>}</button>
      </aside>

      {drawer && <div className="fixed inset-0 z-40 md:hidden">
        <div className="absolute inset-0 bg-slate-900/30" onClick={() => setDrawer(false)} />
        <aside className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl flex flex-col">
          <div className="h-16 flex items-center justify-between px-4"><Brand /><button onClick={() => setDrawer(false)} className="p-2"><X className="size-5" /></button></div>
          <nav className="flex-1 px-3 space-y-1">{links(false)}</nav>
          <button onClick={() => { logout(); nav('/login') }} className="m-3 btn-ghost"><LogOut className="size-4" />Log out</button>
        </aside>
      </div>}

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 h-14 md:h-16 bg-white/85 backdrop-blur border-b border-slate-200 flex items-center gap-3 px-3 sm:px-6">
          <button className="md:hidden p-1.5 -ml-1" onClick={() => setDrawer(true)} aria-label="Menu"><Menu className="size-5" /></button>
          <div className="md:hidden"><Brand compact /></div>
          <h1 className="font-semibold text-slate-800 truncate">{current}</h1>
          <div className="ml-auto flex items-center gap-2.5">
            <AiStatus />
            <ThemeButton />
            <NavLink to="/settings" className="size-9 rounded-full bg-gradient-to-br from-brand-500 to-sky-500 text-white grid place-items-center text-sm font-semibold" title={user?.email}>
              {(user?.name || user?.email || '?')[0].toUpperCase()}
            </NavLink>
          </div>
        </header>
        <main className="flex-1 p-3 sm:p-6 pb-24 md:pb-8 max-w-6xl w-full mx-auto"><Outlet /></main>
      </div>

      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-white/95 backdrop-blur border-t border-slate-200 pb-safe">
        <div className="grid grid-cols-5">
          {BOTTOM.map(({ to, short, icon: I }) => to === '/capture' ? (
            <NavLink key={to} to={to} className="flex justify-center -mt-5">
              <span aria-label="Capture meal" className="size-14 rounded-2xl bg-brand-600 text-white grid place-items-center shadow-lg shadow-brand-600/30"><I className="size-6" /></span>
            </NavLink>
          ) : (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${isActive ? 'text-brand-700' : 'text-slate-500'}`}>
              <I className="size-5" />{short}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}

export function ThemeButton() {
  const { pref, cycle } = useTheme()
  const Icon = pref === 'dark' ? Moon : pref === 'light' ? Sun : Monitor
  return <button onClick={cycle} className="size-9 rounded-full grid place-items-center text-slate-600 hover:bg-slate-100" title={`Theme: ${pref} (tap to change)`} aria-label={`Theme: ${pref}`}><Icon className="size-[18px]" /></button>
}
