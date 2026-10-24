import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import AuthForm from '../components/AuthForm'
import PublicShell from '../components/PublicShell'

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user } = useAuth()
  if (user) return <Navigate to={user.onboarded ? '/' : '/onboarding'} replace />
  return (
    <PublicShell>
      <div className="max-w-sm mx-auto px-5 py-14 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p className="mt-2 mb-8" style={{ color: 'var(--p-muted)' }}>{mode === 'login' ? 'Sign in to continue.' : 'It takes a minute. Health details come next and are optional.'}</p>
        <AuthForm key={mode} initial={mode} />
        <p className="mt-6 text-sm text-center" style={{ color: 'var(--p-muted)' }}>{mode === 'login'
          ? <>New here? <Link className="font-medium" style={{ color: 'var(--p-primary)' }} to="/register">Create an account</Link></>
          : <>Have an account? <Link className="font-medium" style={{ color: 'var(--p-primary)' }} to="/login">Sign in</Link></>}</p>
      </div>
    </PublicShell>
  )
}
