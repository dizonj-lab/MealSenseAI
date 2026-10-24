import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../lib/api'
import PublicShell from '../components/PublicShell'
import CreatorProfile from '../components/CreatorProfile'
import { Spinner } from '../components/ui'

function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <PublicShell>
      <article className="max-w-2xl mx-auto px-5 sm:px-8 py-14 space-y-4 leading-relaxed">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <div className="space-y-4 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:pt-2 [&_p]:text-[15px] [&_li]:text-[15px] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1" style={{ color: 'var(--p-text)' }}>{children}</div>
      </article>
    </PublicShell>
  )
}

export function Privacy() {
  return (
    <Page title="Privacy Policy">
      <h2>What we collect</h2>
      <ul><li>Account details: name, email and a hashed password.</li>
        <li>Meal photos you upload, the foods recognised in them, and your corrections.</li>
        <li>Optional health information you choose to share (for example diabetes status or glucose readings), stored only with your consent.</li>
        <li>Meal Advisor conversations, kept for 30 days after your last message.</li></ul>
      <h2>How we use it</h2>
      <p>Only to provide MealSenseAI to you: recognising foods, estimating nutrition and giving educational insights. Health information is never used to diagnose a condition, and meal photos are never used to infer one.</p>
      <h2>Where it is processed</h2>
      <p>On the MealSenseAI server. Food recognition and the Meal Advisor run on local models; your data is not sent to external AI services.</p>
      <h2>Training data</h2>
      <p>Your corrected photo regions are used to improve the food model only if you switch on “Use my corrected photos to improve the model” in Settings.</p>
      <h2>Your choices</h2>
      <p>You can edit your profile, clear Advisor conversations, and delete your account and data at any time in Settings.</p>
      <h2>Contact</h2><p>Use the <Link className="underline" to="/contact">contact form</Link>.</p>
    </Page>
  )
}

export function Terms() {
  return (
    <Page title="Terms of Service">
      <h2>Educational use</h2>
      <p>MealSenseAI provides estimated nutrition information and general education. It is not a medical device, does not diagnose or treat any condition, and does not give medication or insulin advice. Always follow your healthcare team's guidance.</p>
      <h2>Estimates</h2>
      <p>Food recognition, portions and nutrition values are estimates and can be wrong. Glucose curves are estimates, not measurements, even when they start from a reading you entered. Please check results before relying on them.</p>
      <h2>Your account</h2>
      <p>Keep your password private. Only upload photos you have the right to use.</p>
      <h2>Changes</h2>
      <p>These terms may be updated; the version in the app applies.</p>
      <h2>Contact</h2><p>Use the <Link className="underline" to="/contact">contact form</Link>.</p>
    </Page>
  )
}

const TOPICS = ['Question', 'Feedback', 'Bug report', 'Data request', 'Other']

export function Contact() {
  const [f, setF] = useState({ name: '', email: '', topic: 'Question', message: '', website: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null)
    try { await api('/contact', { method: 'POST', json: f }); setSent(true) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Page title="Contact">
      <p>Questions, feedback, bug reports or data requests: send a message and the creator of MealSenseAI will reply by email.</p>
      {sent ? <div role="status" className="rounded-2xl p-5 flex gap-3 items-start" style={{ background: 'var(--p-surface)', border: '1px solid var(--p-border)' }}>
        <CheckCircle2 className="size-5 shrink-0 mt-0.5 text-brand-600" />
        <div><p className="font-semibold">Thanks, your message was sent.</p><p style={{ color: 'var(--p-muted)' }}>You'll get a reply at {f.email}.</p></div>
      </div> : <form onSubmit={submit} className="space-y-4 pt-2">
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="block"><span className="label">Name</span><input className="input" required maxLength={120} value={f.name} onChange={set('name')} autoComplete="name" /></label>
          <label className="block"><span className="label">Email</span><input className="input" type="email" required value={f.email} onChange={set('email')} autoComplete="email" /></label>
        </div>
        <label className="block"><span className="label">Topic</span>
          <select className="input" value={f.topic} onChange={set('topic')}>{TOPICS.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="block"><span className="label">Message</span>
          <textarea className="input" required minLength={10} maxLength={5000} rows={6} value={f.message} onChange={set('message')} /></label>
        <label aria-hidden="true" className="absolute -left-[9999px]" tabIndex={-1}>Website<input tabIndex={-1} autoComplete="off" value={f.website} onChange={set('website')} /></label>
        {err && <p className="text-sm text-rose-600">{err}</p>}
        <button className="btn-primary w-full sm:w-auto px-6 py-3" disabled={busy}>{busy ? <Spinner className="size-4 text-white" /> : 'Send message'}</button>
      </form>}
      <p style={{ color: 'var(--p-muted)' }}>For medical concerns, please contact your doctor. In an emergency, call your local emergency number.</p>
    </Page>
  )
}

export function Creator() {
  return (
    <PublicShell>
      <article className="max-w-2xl mx-auto px-5 sm:px-8 py-14">
        <p className="text-xs font-medium uppercase tracking-wider mb-6" style={{ color: 'var(--p-muted)' }}>About the creator</p>
        <CreatorProfile />
      </article>
    </PublicShell>
  )
}
