import { AlertTriangle } from 'lucide-react'

/** Server-side calibration that turns the relative meal curve (peak = 100) into an estimated glucose value. */
export type GlucoseScale = {
  unit: 'mmol/L' | 'mg/dL'; mgdl_per_mmol: number; baseline_mmol: number | null; baseline_source: string | null
  peak_rise_mmol: number; band_mmol: [number, number]; glucose_group: string; anchor: string; note: string
  calibration: { kind: 'population' | 'personal'; n_meals: number; factor_vs_population: number; label: string }
}

/** value = baseline (your measured pre-meal level, or 0 = "rise above pre-meal" when unknown) + index/100 × rise. */
export function glucoseAxis(gs: GlucoseScale) {
  const k = gs.unit === 'mg/dL' ? gs.mgdl_per_mmol : 1
  const base = gs.baseline_mmol ?? 0
  const r = (v: number) => gs.unit === 'mg/dL' ? Math.round(v) : Math.round(v * 10) / 10
  const at = (idx: number, rise: number) => r((base + (idx / 100) * rise) * k)
  return {
    known: gs.baseline_mmol != null,
    unit: gs.unit,
    mmol: (v: number) => r(v * k),
    round: r,
    value: (idx: number) => at(idx, gs.peak_rise_mmol),
    low: (idx: number) => at(idx, gs.band_mmol[0]),
    high: (idx: number) => at(idx, gs.band_mmol[1]),
    rise: (idx: number) => r((idx / 100) * gs.peak_rise_mmol * k),
    title: gs.baseline_mmol != null ? `Estimated blood glucose (${gs.unit})` : `Estimated rise above your pre-meal level (${gs.unit})`,
  }
}

/** Y-axis range that always contains the band, lines and any measured dots (0 at the bottom when baseline unknown). */
export function yDomain(values: number[], known: boolean, unit: string): [number, number] {
  const step = unit === 'mg/dL' ? 10 : 0.5
  const lo = known ? Math.floor(Math.min(...values) / step) * step : 0
  return [Math.max(0, lo), Math.ceil(Math.max(...values) / step) * step + step]
}

export function GlucoseEstimateNote({ gs }: { gs: GlucoseScale }) {
  const ax = glucoseAxis(gs)
  return (
    <div className="mt-2 rounded-xl bg-amber-50 ring-1 ring-amber-200 p-3 text-xs text-amber-800 space-y-1">
      <div className="flex gap-2 font-semibold"><AlertTriangle className="size-4 shrink-0" />Estimate only, not your measured glucose</div>
      <p>{ax.known
        ? <>Starts from {gs.baseline_source} ({ax.mmol(gs.baseline_mmol!)} {gs.unit}). Everything after that point is modelled, not measured, and your real response can differ.</>
        : <>No pre-meal reading for this meal, so the curve shows only the estimated rise from 0. Log a “before meal” reading to see estimated levels.</>}
        {' '}Peak rise ~{ax.mmol(gs.peak_rise_mmol)} {gs.unit} (range {ax.mmol(gs.band_mmol[0])}–{ax.mmol(gs.band_mmol[1])}).</p>
      <p className="flex flex-wrap items-center gap-1.5">
        <span className={`chip ring-1 ${gs.calibration.kind === 'personal' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-white text-amber-800 ring-amber-200'}`}>{gs.calibration.label}</span>
        {gs.calibration.kind === 'population' && <span className="text-amber-700">Anchor: {gs.anchor}.</span>}
      </p>
      <p className="font-medium">Do not use it to adjust insulin or medication.</p>
    </div>
  )
}
