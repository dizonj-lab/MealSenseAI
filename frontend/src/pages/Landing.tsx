import { Link } from 'react-router-dom'
import PublicShell from '../components/PublicShell'

const STEPS: [string, string][] = [
  ['Capture', 'Take a photo of your meal. One top view is enough.'],
  ['Understand', 'See each food on the plate with estimated portions and nutrition, and correct anything.'],
  ['Decide', 'Get clear, personal insights on how the meal may affect your glucose and energy.'],
]
const BENEFITS: [string, string][] = [
  ['Identify multiple foods in a meal', 'Each item is recognised and listed separately, so you can confirm, rename or add what was missed.'],
  ['Understand nutrition and portions', 'Estimated calories, carbohydrate, sugar, protein, fat and sodium, with the uncertainty shown.'],
  ['Receive personalised meal insights', 'Suggestions that follow your goals and health context, and a Meal Advisor you can ask.'],
]

/** Minimalist public landing page shown at "/" before sign-in. */
export default function Landing() {
  const muted = { color: 'var(--p-muted)' }
  return (
    <PublicShell>
      <section className="max-w-3xl mx-auto px-5 sm:px-8 pt-16 sm:pt-28 pb-20 sm:pb-28 text-center">
        <h1 className="text-[38px] sm:text-6xl font-semibold tracking-tight leading-[1.08]">Understand your food.<br className="hidden sm:block" /> Make healthier choices.</h1>
        <p className="mt-6 text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto" style={muted}>MealSenseAI helps you identify what's on your plate, estimate nutrition, and understand how your meals may affect your glucose and energy.</p>
        <div className="mt-10 flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/register" className="rounded-xl px-7 py-3.5 text-base font-medium text-white" style={{ background: 'var(--p-primary)' }}>Get Started</Link>
          <a href="#how" className="rounded-xl px-7 py-3.5 text-base font-medium border" style={{ borderColor: 'var(--p-border)' }}>See How It Works</a>
        </div>
      </section>

      <section id="how" className="border-t scroll-mt-4" style={{ borderColor: 'var(--p-border)' }}>
        <div className="max-w-5xl mx-auto px-5 sm:px-8 py-20">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-center">How it works</h2>
          <ol className="mt-12 grid sm:grid-cols-3 gap-10 sm:gap-8">{STEPS.map(([t, b], i) => (
            <li key={t} className="text-center sm:text-left">
              <div className="text-sm font-medium" style={{ color: 'var(--p-primary)' }}>{String(i + 1).padStart(2, '0')}</div>
              <h3 className="mt-2 text-xl font-semibold">{t}</h3>
              <p className="mt-2 leading-relaxed" style={muted}>{b}</p>
            </li>))}</ol>
        </div>
      </section>

      <section className="border-t" style={{ borderColor: 'var(--p-border)' }}>
        <div className="max-w-3xl mx-auto px-5 sm:px-8 py-20">
          <ul className="space-y-10">{BENEFITS.map(([t, b]) => (
            <li key={t}><h3 className="text-lg font-semibold">{t}</h3><p className="mt-1.5 leading-relaxed" style={muted}>{b}</p></li>))}</ul>
          <div className="mt-14 text-center">
            <Link to="/register" className="inline-block rounded-xl px-7 py-3.5 text-base font-medium text-white" style={{ background: 'var(--p-primary)' }}>Get Started</Link>
            <p className="mt-4 text-sm" style={muted}>Educational information, not medical advice.</p>
          </div>
        </div>
      </section>
    </PublicShell>
  )
}
