import { useNavigate } from 'react-router-dom'
import { FileCode2, LogOut, ShieldAlert, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Card } from '../components/ui'

export default function Settings() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const del = async () => {
    if (!confirm('Delete your account, profile and all meals? This cannot be undone.')) return
    await api('/users/me', { method: 'DELETE' }); logout(); nav('/register')
  }
  return (
    <div className="space-y-4 max-w-2xl">
      <Card title="Account">
        <div className="text-sm"><div className="font-medium">{user?.name || '—'}</div><div className="text-slate-500">{user?.email}</div>
          <div className="text-xs text-slate-400 mt-1">Member since {user && new Date(user.created_at).toLocaleDateString()}</div></div>
        <button className="btn-ghost mt-4" onClick={() => { logout(); nav('/login') }}><LogOut className="size-4" />Log out</button>
      </Card>
      <Card title="Developer"><a className="btn-ghost" href="/docs" target="_blank" rel="noreferrer"><FileCode2 className="size-4" />OpenAPI docs</a></Card>
      <Card title="About & safety" icon={<ShieldAlert className="size-5 text-amber-500" />}>
        <p className="text-sm text-slate-600">MealSenseAI provides general, educational nutrition information estimated from photos and reference food-composition data. It does not predict your personal glucose response, set clinical targets or advise on medication. Talk to your healthcare team about your care.</p>
      </Card>
      <Card title="Privacy">
        <p className="text-sm text-slate-600 mb-3">All data and AI inference stay on this self-hosted server. Health details are stored only with consent.</p>
        <button className="btn-ghost text-rose-600" onClick={del}><Trash2 className="size-4" />Delete account & data</button>
      </Card>
    </div>
  )
}
