import { Link } from 'react-router-dom'
import PublicShell from '../components/PublicShell'

const STEPS: [string, string][] = [
  ['Capture', 'Take a photo of your meal. One top view is enough.'],
  ['Understand', 'See each food on the plate with estimated portions and nutrition, and correct anything.'],
  ['Decide', 'Get clear, personal insights on how the meal may affect your glucose and energy.'],
]
const SHOTS: [string, string][][] = [
  [['/landing/capture-identify.webp', 'MealSenseAI screen: a breakfast photo with each food outlined and numbered, and the meal total']],
  [['/landing/glucose-impact.webp', 'MealSenseAI screen: estimated glucose impact, carbohydrate, sugar, fibre and energy for the meal'],
   ['/landing/portion-simulator.webp', 'MealSenseAI screen: portion simulator table and a simulated glucose response curve']],
  [['/landing/exercise-whatif.webp', 'MealSenseAI screen: what-if exercise scenario comparing glucose excursion with and without a walk'],
   ['/landing/nutrition-insights.webp', 'MealSenseAI screen: nutrition insights with daily averages and macronutrients per day']],
]

function Phone({ src, alt, className = '' }: { src: string; alt: string; className?: string }) {
  return (
    <div className={`w-[190px] sm:w-[170px] lg:w-[190px] rounded-[1.6rem] p-1.5 shadow-xl ring-1 ${className}`} style={{ background: '#0B1211', ['--tw-ring-color' as string]: 'var(--p-border)' }}>
      <img src={src} alt={alt} loading="lazy" decoding="async" width={540} height={1000} className="block w-full h-auto rounded-[1.25rem]" />
    </div>
  )
}

function StepShots({ shots }: { shots: [string, string][] }) {
  if (shots.length === 1) return <Phone src={shots[0][0]} alt={shots[0][1]} />
  return (
    <div className="relative w-[250px] sm:w-[220px] lg:w-[250px] h-full">
      <Phone src={shots[1][0]} alt={shots[1][1]} className="absolute right-0 top-8 scale-[0.92] origin-top-right opacity-95" />
      <Phone src={shots[0][0]} alt={shots[0][1]} className="absolute left-0 top-0" />
    </div>
  )
}

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
      <section className="max-w-3xl mx-auto px-5 sm:px-8 pt-16 sm:pt-28 pb-12 sm:pb-16 text-center">
        <h1 className="text-[38px] sm:text-6xl font-semibold tracking-tight leading-[1.08]">Understand your food.<br className="hidden sm:block" /> Make healthier choices.</h1>
        <p className="mt-6 text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto" style={muted}>MealSenseAI helps you identify what's on your plate, estimate nutrition, and understand how your meals may affect your glucose and energy.</p>
      </section>

      <section id="how" className="scroll-mt-4">
        <div className="max-w-5xl mx-auto px-5 sm:px-8 pb-20">
          <ol className="grid sm:grid-cols-3 gap-14 sm:gap-8">{STEPS.map(([t, b], i) => (
            <li key={t} className="text-center sm:text-left">
              <div className="h-[400px] sm:h-[370px] lg:h-[410px] flex items-start justify-center mb-6 overflow-hidden">
                <StepShots shots={SHOTS[i]} />
              </div>
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
