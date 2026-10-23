import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Camera, ShieldCheck, Sparkles } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { ErrorNote, Spinner } from '../components/ui'

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user, login, register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ email: '', password: '', name: '' })
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to={user.onboarded ? '/' : '/onboarding'} replace />
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr(null); setBusy(true)
    try { mode === 'login' ? await login(f.email, f.password) : await register(f.email, f.password, f.name); nav('/') }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="min-h-full grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between p-10 bg-gradient-to-br from-brand-600 via-teal-600 to-sky-600 text-white">
        <div className="flex items-center gap-2 font-bold text-lg"><img src="/favicon.svg" className="size-9" alt="" />MealSenseAI</div>
        <div>
          <h2 className="text-3xl font-bold leading-tight">Understand every meal,<br />one photo at a time.</h2>
          <ul className="mt-6 space-y-3 text-white/90">
            <li className="flex gap-2"><Camera className="size-5" />Snap top & side views of your plate</li>
            <li className="flex gap-2"><Sparkles className="size-5" />On-device AI recognition you can correct</li>
            <li className="flex gap-2"><ShieldCheck className="size-5" />Private, self-hosted, health data optional</li>
          </ul>
        </div>
        <p className="text-xs text-white/70">Educational nutrition information — not medical advice.</p>
      </div>
      <div className="flex items-center justify-center p-5">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <div className="md:hidden flex items-center gap-2 font-bold text-lg mb-6"><img src="/favicon.svg" className="size-9" alt="" />MealSense<span className="text-brand-600 -ml-2">AI</span></div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
            <p className="text-sm text-slate-500 mt-1">{mode === 'login' ? 'Log in to continue tracking your meals.' : 'Start understanding your meals in minutes.'}</p>
          </div>
          {mode === 'register' && <label className="block"><span className="label">Name</span><input className="input" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} autoComplete="name" /></label>}
          <label className="block"><span className="label">Email</span><input className="input" type="email" required value={f.email} onChange={e => setF({ ...f, email: e.target.value })} autoComplete="email" /></label>
          <label className="block"><span className="label">Password</span><input className="input" type="password" required minLength={mode === 'register' ? 8 : 1} value={f.password} onChange={e => setF({ ...f, password: e.target.value })} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
            {mode === 'register' && <p className="text-xs text-slate-400 mt-1">At least 8 characters.</p>}</label>
          <ErrorNote msg={err} />
          <button className="btn-primary w-full py-3" disabled={busy}>{busy ? <Spinner className="size-4 text-white" /> : mode === 'login' ? 'Log in' : 'Create account'}</button>
          <p className="text-sm text-center text-slate-500">{mode === 'login' ? <>New here? <Link className="text-brand-700 font-semibold" to="/register">Create an account</Link></> : <>Have an account? <Link className="text-brand-700 font-semibold" to="/login">Log in</Link></>}</p>
        </form>
      </div>
    </div>
  )
}
