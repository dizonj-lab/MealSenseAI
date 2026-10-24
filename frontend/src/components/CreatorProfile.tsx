/** Creator profile, shown on the About page and the public /creator page. */
export default function CreatorProfile({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`flex ${compact ? 'gap-4' : 'flex-col sm:flex-row gap-5'} items-start`}>
      <div aria-hidden="true" className="size-16 shrink-0 rounded-2xl bg-brand-600 text-white grid place-items-center text-xl font-semibold tracking-wide">JD</div>
      <div className="min-w-0">
        <h3 className="text-lg font-semibold text-slate-900">Joselito Villanueva Dizon</h3>
        <p className="text-sm font-medium text-brand-700">AI Solution Architect | Creator of MealSenseAI</p>
        <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-slate-600">
          <p>Joselito Villanueva Dizon is an experienced technology architect with a passion for artificial intelligence and innovation.</p>
          <p>He developed MealSenseAI as part of his postgraduate studies in AI Systems at the National University of Singapore (NUS), applying machine learning, computer vision, and conversational AI to make food recognition and nutritional awareness simpler and more accessible.</p>
          <p className="text-slate-800">His vision is simple: <em>Making AI practical, personal, and meaningful in everyday life.</em></p>
        </div>
      </div>
    </div>
  )
}
