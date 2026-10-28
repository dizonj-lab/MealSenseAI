import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import PublicShell from '../components/PublicShell'
import { Spinner } from '../components/ui'

/** Landing page of the email-verification link. Works signed in or not; the token is the proof. */
export default function Verify() {
  const [params] = useSearchParams()
  const { user, refresh } = useAuth()
  const [state, setState] = useState<{ ok: boolean; msg: string } | null>(null)
  useEffect(() => {
    const token = params.get('token')
    if (!token) { setState({ ok: false, msg: 'This link has no token.' }); return }
    api<{ email: string }>('/auth/verify', { method: 'POST', json: { token } })
      .then(r => { setState({ ok: true, msg: `${r.email} is confirmed. Thank you!` }); refresh() })
      .catch(e => setState({ ok: false, msg: e.message }))
  }, [params])  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <PublicShell>
      <div className="max-w-md mx-auto px-5 py-24 text-center">
        {!state ? <Spinner className="size-8 mx-auto" /> : <>
          {state.ok ? <CheckCircle2 className="size-12 mx-auto text-emerald-600" /> : <XCircle className="size-12 mx-auto text-rose-500" />}
          <h1 className="mt-4 text-2xl font-semibold">{state.ok ? 'Email confirmed' : 'Link not valid'}</h1>
          <p className="mt-2" style={{ color: 'var(--p-muted)' }}>{state.msg}</p>
          <Link to={user ? '/settings' : '/login'} className="inline-block mt-8 rounded-xl px-6 py-3 font-medium text-white" style={{ background: 'var(--p-primary)' }}>
            {user ? 'Back to Settings' : 'Sign in'}</Link>
        </>}
      </div>
    </PublicShell>
  )
}
