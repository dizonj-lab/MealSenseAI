import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { User } from '../lib/types'
import { EMPTY_PROFILE, ProfileStep, STEPS } from '../components/ProfileForm'
import { ErrorNote } from '../components/ui'

export default function Onboarding() {
  const { user, setUser } = useAuth()
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [p, setP] = useState({ ...EMPTY_PROFILE, ...(user?.profile ?? {}) })
  const [err, setErr] = useState<string | null>(null)
  const save = async () => {
    try { setUser(await api<User>('/users/health-profile', { method: 'PUT', json: p })); nav('/') } catch (e: any) { setErr(e.message) }
  }
  return (
    <div className="min-h-full bg-gradient-to-b from-brand-50 to-slate-50 p-4 flex justify-center">
      <div className="w-full max-w-xl">
        <div className="flex items-center gap-2 font-bold my-4"><img src="/favicon.svg" className="size-8" alt="" />Let's personalise MealSenseAI</div>
        <ol className="flex gap-2 mb-4">{STEPS.map((s, i) => (
          <li key={s} className="flex-1"><div className={`h-1.5 rounded-full ${i <= step ? 'bg-brand-600' : 'bg-slate-200'}`} />
            <div className={`mt-1.5 text-[11px] font-medium ${i === step ? 'text-brand-700' : 'text-slate-400'}`}>{s}</div></li>))}</ol>
        <div className="card p-5">
          <h2 className="text-lg font-semibold mb-1">{STEPS[step]}</h2>
          <p className="text-sm text-slate-500 mb-4">{['Basic details help put portions in context. All optional.', 'Optional and consent-based. Skip anything you prefer not to share.', 'Only if relevant to you.', 'Choose what MealSenseAI should focus on.'][step]}</p>
          <ProfileStep step={step} p={p} set={setP} />
          <div className="mt-4"><ErrorNote msg={err} /></div>
          <div className="mt-6 flex gap-2">
            {step > 0 && <button className="btn-ghost" onClick={() => setStep(step - 1)}>Back</button>}
            <button className="btn-ghost ml-auto" onClick={() => (step < 3 ? setStep(step + 1) : save())}>Skip</button>
            {step < 3 ? <button className="btn-primary" onClick={() => setStep(step + 1)}>Continue</button>
              : <button className="btn-primary" onClick={save}><Check className="size-4" />Finish</button>}
          </div>
        </div>
      </div>
    </div>
  )
}
