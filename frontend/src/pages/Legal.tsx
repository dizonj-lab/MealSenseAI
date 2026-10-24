import type { ReactNode } from 'react'
import PublicShell from '../components/PublicShell'
import CreatorProfile from '../components/CreatorProfile'

const DRAFT = 'Draft for review. This text has not been reviewed by a lawyer.'

function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <PublicShell>
      <article className="max-w-2xl mx-auto px-5 sm:px-8 py-14 space-y-4 leading-relaxed">
        <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--p-muted)' }}>{DRAFT}</p>
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
      <h2>Contact</h2><p>[contact email]</p>
    </Page>
  )
}

export function Terms() {
  return (
    <Page title="Terms of Service">
      <h2>Educational use</h2>
      <p>MealSenseAI provides estimated nutrition information and general education. It is not a medical device, does not diagnose or treat any condition, and does not give medication or insulin advice. Always follow your healthcare team's guidance.</p>
      <h2>Estimates</h2>
      <p>Food recognition, portions and nutrition values are estimates and can be wrong. Glucose curves are illustrative simulations, not measurements. Please check results before relying on them.</p>
      <h2>Your account</h2>
      <p>Keep your password private. Only upload photos you have the right to use.</p>
      <h2>Changes</h2>
      <p>These terms may be updated; the version in the app applies.</p>
      <h2>Contact</h2><p>[contact email]</p>
    </Page>
  )
}

export function Contact() {
  return (
    <Page title="Contact">
      <p>Questions, feedback or data requests: <b>[contact email]</b></p>
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
