/** Vector illustrations for the public landing page (no photos, no numbers: purely illustrative). */
const C = { primary: 'var(--p-primary)', muted: 'var(--p-muted)', border: 'var(--p-border)', surface: 'var(--p-surface)', text: 'var(--p-text)' }
const ITEMS = [
  { n: 1, label: 'Pancakes', color: '#147D73', box: [40, 52, 104, 96] },
  { n: 2, label: 'Fried egg', color: '#6366F1', box: [150, 44, 88, 78] },
  { n: 3, label: 'Sausages', color: '#E07A2E', box: [138, 128, 104, 60] },
  { n: 4, label: 'Name this item', color: '#B45309', box: [70, 150, 56, 40], unknown: true },
]

function Foods() {
  return (
    <g>
      {/* pancake stack */}
      <ellipse cx="92" cy="112" rx="46" ry="16" fill="#C98A3E" />
      <ellipse cx="92" cy="104" rx="46" ry="16" fill="#E2A955" />
      <ellipse cx="92" cy="96" rx="46" ry="16" fill="#EDBB66" />
      <path d="M70 92 q22 -10 44 0 q-8 10 -22 9 q-14 1 -22 -9z" fill="#8B4A14" opacity=".75" />
      <rect x="84" y="86" width="16" height="9" rx="2" fill="#FFF3C4" />
      {/* fried egg */}
      <path d="M160 82 q-6 -24 22 -26 q30 -2 32 22 q4 22 -24 26 q-26 2 -30 -22z" fill="#FFFDF7" stroke="#EDE7D9" />
      <circle cx="190" cy="82" r="13" fill="#F4B227" />
      <circle cx="186" cy="78" r="4" fill="#FFD66B" />
      {/* sausages */}
      <rect x="146" y="140" width="88" height="15" rx="7.5" fill="#9A4A2B" transform="rotate(-8 190 147)" />
      <rect x="148" y="160" width="86" height="15" rx="7.5" fill="#86402A" transform="rotate(-4 190 167)" />
      {/* butter pat (the "unknown" item) */}
      <rect x="84" y="160" width="28" height="20" rx="4" fill="#FCE9A6" stroke="#EBD27E" />
    </g>
  )
}

export function PlateArt({ boxes = false, className = '' }: { boxes?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 280 230" className={className} role="img" aria-label={boxes ? 'Illustration: foods on a plate, each outlined and numbered' : 'Illustration: a breakfast plate'}>
      <rect width="280" height="230" rx="20" fill="var(--p-table)" />
      <ellipse cx="140" cy="118" rx="122" ry="98" fill="var(--p-plate-rim)" />
      <ellipse cx="140" cy="118" rx="108" ry="86" fill="var(--p-plate)" />
      <Foods />
      {boxes && ITEMS.map(i => (
        <g key={i.n}>
          <rect x={i.box[0]} y={i.box[1]} width={i.box[2]} height={i.box[3]} rx="6" fill="none" stroke={i.color} strokeWidth="2.5" strokeDasharray={i.unknown ? '6 4' : undefined} />
          <rect x={i.box[0]} y={i.box[1] - 1} width="18" height="16" rx="4" fill={i.color} />
          <text x={i.box[0] + 9} y={i.box[1] + 11} textAnchor="middle" fontSize="11" fontWeight="700" fill="#fff" fontFamily="Inter, sans-serif">{i.n}</text>
        </g>))}
    </svg>
  )
}

export function CaptureArt() {
  return (
    <div className="relative mx-auto w-[220px] rounded-[2.2rem] p-2.5 shadow-xl" style={{ background: '#111816' }} role="img" aria-label="Illustration: taking a photo of a meal with a phone">
      <div className="relative overflow-hidden rounded-[1.7rem]" style={{ background: '#0B0F0E' }}>
        <div className="h-8 flex items-center justify-center"><span className="h-1.5 w-14 rounded-full" style={{ background: 'rgba(255,255,255,.2)' }} /></div>
        <PlateArt className="block w-full" />
        <div className="py-2 text-center text-[11px] text-white/70">Hold steady, top view</div>
        {[['top-11 left-3', 'border-t-2 border-l-2'], ['top-11 right-3', 'border-t-2 border-r-2'], ['bottom-[6.5rem] left-3', 'border-b-2 border-l-2'], ['bottom-[6.5rem] right-3', 'border-b-2 border-r-2']].map(([pos, b]) => (
          <span key={pos} className={`absolute ${pos} ${b} size-6 rounded-sm border-white/90`} />))}
        <div className="flex items-center justify-center gap-6 py-3" style={{ background: '#0B0F0E' }}>
          <span className="size-7 rounded-lg" style={{ background: 'rgba(255,255,255,.15)' }} />
          <span className="size-12 rounded-full border-4 grid place-items-center" style={{ borderColor: 'rgba(255,255,255,.9)' }}><span className="size-8 rounded-full" style={{ background: '#fff' }} /></span>
          <span className="size-7 rounded-full" style={{ background: 'rgba(255,255,255,.15)' }} />
        </div>
      </div>
    </div>
  )
}

export function IdentifyArt() {
  return (
    <div className="rounded-2xl border p-3 shadow-sm" style={{ background: C.surface, borderColor: C.border }}>
      <PlateArt boxes className="block w-full rounded-xl" />
      <ul className="mt-3 space-y-1.5">{ITEMS.map(i => (
        <li key={i.n} className="flex items-center gap-2.5 text-sm">
          <span className="size-5 shrink-0 rounded-md grid place-items-center text-[11px] font-bold text-white" style={{ background: i.color }}>{i.n}</span>
          <span className={i.unknown ? 'italic' : 'font-medium'} style={{ color: i.unknown ? '#B45309' : C.text }}>{i.label}</span>
          <span className="ml-auto h-1.5 rounded-full" style={{ width: i.unknown ? 24 : 56, background: i.unknown ? '#F3D9A8' : 'var(--p-border)' }} />
        </li>))}</ul>
    </div>
  )
}

/** Small charts: carbohydrate by food, calorie split, and a simulated "smaller portion" curve. */
export function ChartsArt() {
  const bars = [['Pancakes', 0.92, '#147D73'], ['Syrup', 0.55, '#6366F1'], ['Sausages', 0.12, '#E07A2E'], ['Egg', 0.05, '#F4B227']] as const
  const arcs = [[0.5, '#147D73'], [0.22, '#6366F1'], [0.18, '#E07A2E'], [0.1, '#F4B227']] as const
  let acc = 0
  return (
    <div className="grid gap-3">
      <div className="rounded-2xl border p-4" style={{ background: C.surface, borderColor: C.border }}>
        <div className="text-xs font-medium mb-3" style={{ color: C.muted }}>Carbohydrate by food</div>
        <div className="space-y-2" role="img" aria-label="Illustration: bar chart of carbohydrate by food">
          {bars.map(([l, w, c]) => (
            <div key={l} className="grid grid-cols-[4.5rem_1fr] items-center gap-2 text-xs" style={{ color: C.text }}>
              <span>{l}</span><span className="h-2.5 rounded-full" style={{ width: `${w * 100}%`, background: c }} /></div>))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl border p-4" style={{ background: C.surface, borderColor: C.border }}>
          <div className="text-xs font-medium mb-2" style={{ color: C.muted }}>Calories</div>
          <svg viewBox="0 0 42 42" className="w-20 h-20 mx-auto -rotate-90" role="img" aria-label="Illustration: donut chart of calories by food">
            {arcs.map(([f, c], i) => { const el = <circle key={i} cx="21" cy="21" r="15.9" fill="none" stroke={c} strokeWidth="6" strokeDasharray={`${f * 100} ${100 - f * 100}`} strokeDashoffset={-acc * 100} pathLength={100} />; acc += f; return el })}
          </svg>
        </div>
        <div className="rounded-2xl border p-4" style={{ background: C.surface, borderColor: C.border }}>
          <div className="flex items-center justify-between text-xs font-medium mb-2" style={{ color: C.muted }}><span>Smaller portion?</span></div>
          <svg viewBox="0 0 120 70" className="w-full h-20" role="img" aria-label="Illustration: simulated curves, the smaller portion peaks lower">
            <line x1="0" y1="66" x2="120" y2="66" stroke="var(--p-border)" />
            <path d="M0 64 C18 60 26 10 48 8 S92 44 120 56" fill="none" stroke="var(--p-muted)" strokeWidth="2" strokeDasharray="4 3" />
            <path d="M0 64 C18 62 28 30 48 28 S92 52 120 60" fill="none" stroke="var(--p-primary)" strokeWidth="2.5" />
          </svg>
          <div className="text-[10px]" style={{ color: C.muted }}>Simulated, for learning</div>
        </div>
      </div>
    </div>
  )
}
