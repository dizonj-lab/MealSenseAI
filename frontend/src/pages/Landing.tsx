import { Link } from 'react-router-dom'
import { Camera, Check, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import AuthForm from '../components/AuthForm'
import { ThemeButton } from '../components/Layout'

const GOALS = ['Type 1 diabetes', 'Type 2 diabetes', 'Prediabetes', 'Heart health', 'Weight management', 'General wellness']
const STEPS: [string, string][] = [
  ['Take one photo', 'A top view is enough. Add a side view or a short description if you like.'],
  ['Check each item', 'Every food gets its own card. Confirm, rename or merge, and adjust any portion.'],
  ['Explore and save', 'See where the carbs come from, try a smaller portion, then save to your history.'],
]
const FACTS: [string, string][] = [['320', 'food classes recognised'], ['~0.3 s', 'per photo on our test CPU'], ['0', 'cloud AI calls']]

/** Public landing page shown at "/" before login. */
export default function Landing() {
  return (
    <div className="min-h-full bg-slate-50">
      <header className="max-w-5xl mx-auto flex items-center justify-between px-5 py-4">
        <span className="flex items-center gap-2 font-extrabold text-lg"><img src="/favicon.svg" className="size-8" alt="" />MealSense<span className="text-brand-700 -ml-2">AI</span></span>
        <div className="flex items-center gap-1">
          <Link to="/login" className="px-3 py-2.5 text-sm font-semibold text-slate-700">Log in</Link>
          <ThemeButton />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-5 pb-10">
        <section className="grid md:grid-cols-2 gap-8 items-center pt-4 md:pt-10">
          <div className="space-y-4">
            <h1 className="text-[34px] sm:text-5xl leading-[1.1] font-extrabold tracking-tight text-slate-900">Understand what's on your plate — before you eat it.</h1>
            <p className="text-base sm:text-lg text-slate-600">Where the carbs come from, how a smaller portion changes things, and what that may mean for your energy and glucose.</p>
            <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
              <a href="#start" className="btn-primary py-3.5 text-base"><Camera className="size-5" />Create a free account</a>
              <Link to="/login" className="btn-ghost py-3.5 text-base">I already have an account</Link>
            </div>
          </div>

          <div className="space-y-3" aria-label="Example of the meal review">
            <div className="card p-4 space-y-3">
              <div className="flex items-center justify-between"><span className="font-bold text-slate-800">Breakfast plate</span><span className="chip bg-amber-50 text-amber-800">Illustration</span></div>
              <div className="text-xs font-semibold text-slate-500">Carbohydrate by food</div>
              <div className="flex h-3.5 rounded-full overflow-hidden"><div className="w-[62%] bg-brand-600" /><div className="w-[26%] bg-indigo-500" /><div className="w-[12%] bg-amber-400" /></div>
              <div className="flex flex-wrap gap-3 text-xs text-slate-600">
                {[['bg-brand-600', 'Pancakes'], ['bg-indigo-500', 'Maple syrup'], ['bg-amber-400', 'Other']].map(([c, l]) => <span key={l} className="flex items-center gap-1.5"><i className={`size-2.5 rounded-sm ${c}`} />{l}</span>)}
              </div>
            </div>
            <div className="card p-4 space-y-2">
              <div className="flex items-center justify-between"><span className="font-bold text-slate-800 flex items-center gap-2"><SlidersHorizontal className="size-4 text-brand-700" />Half the pancakes?</span><span className="chip bg-brand-50 text-brand-700">Simulated</span></div>
              <svg viewBox="0 0 320 110" className="w-full h-28" role="img" aria-label="Illustrative simulated glucose curves: the smaller portion peaks lower than the original">
                <line x1="0" y1="102" x2="320" y2="102" className="stroke-slate-200" strokeWidth="1" />
                <path d="M0 100 C40 92 60 14 110 12 S220 64 320 88" fill="none" className="stroke-slate-400" strokeWidth="2" strokeDasharray="5 4" />
                <path d="M0 100 C40 96 62 44 110 42 S220 78 320 94" fill="none" className="stroke-brand-600" strokeWidth="3" />
              </svg>
              <div className="flex gap-4 text-xs text-slate-600"><span>- - Original</span><span className="text-brand-700 font-semibold">— Smaller portion</span></div>
              <p className="text-xs text-slate-500">A population-average simulation for learning, not a prediction of your glucose. Your own meter readings are shown separately.</p>
            </div>
          </div>
        </section>

        <section className="mt-12 grid md:grid-cols-2 gap-8">
          <div className="space-y-3">
            <h2 className="text-xl font-bold text-slate-900">Tailored to your goal</h2>
            <p className="text-sm text-slate-600">Pick what matters to you and the insights adapt. No medication or insulin advice, ever.</p>
            <div className="flex flex-wrap gap-2">{GOALS.map(g => <span key={g} className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700">{g}</span>)}</div>
          </div>
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900">How it works</h2>
            <ol className="space-y-3.5">{STEPS.map(([t, b], i) => (
              <li key={t} className="flex gap-3"><span className="size-8 shrink-0 rounded-full bg-brand-600 text-white grid place-items-center text-sm font-bold">{i + 1}</span>
                <div><div className="font-semibold text-slate-800">{t}</div><div className="text-sm text-slate-600">{b}</div></div></li>))}</ol>
          </div>
        </section>

        <section className="mt-10 grid grid-cols-3 gap-2.5 text-center">
          {FACTS.map(([v, l]) => <div key={l} className="rounded-2xl bg-brand-50 px-2 py-4"><div className="text-xl sm:text-2xl font-extrabold text-brand-700">{v}</div><div className="text-[11px] sm:text-xs text-slate-600">{l}</div></div>)}
        </section>

        <section id="start" className="mt-12 grid md:grid-cols-2 gap-8 items-start scroll-mt-6">
          <div className="space-y-3">
            <h2 className="text-xl font-bold text-slate-900">Get started</h2>
            <ul className="space-y-2 text-sm text-slate-600">
              {['Free, and runs on your own server', 'Health details are optional and only used for your insights', 'Every result can be corrected before it is saved'].map(t => <li key={t} className="flex gap-2"><Check className="size-4 mt-0.5 shrink-0 text-emerald-600" />{t}</li>)}
              <li className="flex gap-2"><ShieldCheck className="size-4 mt-0.5 shrink-0 text-emerald-600" />Food recognition and explanations run locally; no cloud AI service sees your meals</li>
            </ul>
          </div>
          <div className="card p-5"><AuthForm initial="register" tabs /></div>
        </section>
      </main>

      <footer className="max-w-5xl mx-auto px-5 py-6 text-xs text-slate-500 border-t border-slate-200">
        Educational information only — not medical advice. Nutrition values are estimates from a reference table; portions are estimated from photos and can be corrected.
      </footer>
    </div>
  )
}
