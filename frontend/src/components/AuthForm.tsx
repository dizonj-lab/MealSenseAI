import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { ErrorNote, Spinner } from './ui'

/** Log-in / create-account form, used on the auth pages and inline on the landing page. */
export default function AuthForm({ initial = 'login', tabs = false }: { initial?: 'login' | 'register'; tabs?: boolean }) {
  const { login, register } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState(initial)
  const [f, setF] = useState({ email: '', password: '', name: '' })
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr(null); setBusy(true)
    try { mode === 'login' ? await login(f.email, f.password) : await register(f.email, f.password, f.name); nav(mode === 'register' ? '/onboarding' : '/') }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      {tabs && <div className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1" role="tablist">
        {([['login', 'Log in'], ['register', 'Create account']] as const).map(([m, l]) => (
          <button key={m} type="button" role="tab" aria-selected={mode === m} onClick={() => { setMode(m); setErr(null) }}
            className={`rounded-lg py-2.5 text-sm font-semibold transition ${mode === m ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}>{l}</button>))}
      </div>}
      {mode === 'register' && <label className="block"><span className="label">Name</span><input className="input" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} autoComplete="name" /></label>}
      <label className="block"><span className="label">Email</span><input className="input" type="email" required value={f.email} onChange={e => setF({ ...f, email: e.target.value })} autoComplete="email" /></label>
      <label className="block"><span className="label">Password</span><input className="input" type="password" required minLength={mode === 'register' ? 8 : 1} value={f.password} onChange={e => setF({ ...f, password: e.target.value })} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
        {mode === 'register' && <p className="text-xs text-slate-400 mt-1">At least 8 characters.</p>}</label>
      <ErrorNote msg={err} />
      <button className="btn-primary w-full py-3" disabled={busy}>{busy ? <Spinner className="size-4 text-white" /> : mode === 'login' ? 'Log in' : 'Create account'}</button>
    </form>
  )
}
