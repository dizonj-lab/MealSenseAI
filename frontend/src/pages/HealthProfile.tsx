import { useState } from 'react'
import { Check } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { User } from '../lib/types'
import { EMPTY_PROFILE, ProfileStep, STEPS } from '../components/ProfileForm'
import { Card, ErrorNote } from '../components/ui'

export default function HealthProfile() {
  const { user, setUser } = useAuth()
  const [p, setP] = useState({ ...EMPTY_PROFILE, ...(user?.profile ?? {}) })
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const save = async () => {
    setErr(null)
    try { setUser(await api<User>('/users/health-profile', { method: 'PUT', json: p })); setMsg('Saved'); setTimeout(() => setMsg(null), 2000) } catch (e: any) { setErr(e.message) }
  }
  return (
    <div className="space-y-4">
      {STEPS.map((s, i) => <Card key={s} title={s}><ProfileStep step={i} p={p} set={setP} /></Card>)}
      <ErrorNote msg={err} />
      <div className="sticky bottom-20 md:bottom-4 flex justify-end">
        <button className="btn-primary shadow-lg" onClick={save}><Check className="size-4" />{msg ?? 'Save profile'}</button>
      </div>
    </div>
  )
}
