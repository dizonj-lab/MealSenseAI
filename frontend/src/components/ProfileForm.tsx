import { useState } from 'react'
import { Lock } from 'lucide-react'
import type { Profile } from '../lib/types'
import { Toggle } from './ui'

export const EMPTY_PROFILE: Profile = {
  health_consent: false, age: null, sex: null, height_cm: null, weight_kg: null, activity_level: null, diet_preferences: [],
  diabetes_status: null, allergies: [], restrictions: [], glucose_unit: 'mmol/L', known_readings: null, hba1c: null, has_cgm: null,
  clinician_targets: null, goals: [], calorie_goal: null, carb_goal_g: null, protein_goal_g: null,
}
export const STEPS = ['Personal', 'Health', 'Diabetes context', 'Goals'] as const

const DIET: [string, string][] = [['vegetarian', 'Vegetarian'], ['vegan', 'Vegan'], ['halal', 'Halal'], ['pescatarian', 'Pescatarian'], ['low_carb', 'Lower carb'], ['no_beef', 'No beef'], ['no_pork', 'No pork']]
const ALLERGY: [string, string][] = [['peanut', 'Peanut'], ['shellfish', 'Shellfish'], ['fish', 'Fish'], ['egg', 'Egg'], ['dairy', 'Dairy'], ['gluten', 'Gluten'], ['soy', 'Soy']]
const DIABETES: [string, string][] = [['none', 'None'], ['prediabetes', 'Prediabetes'], ['type1', 'Type 1'], ['type2', 'Type 2'], ['gestational', 'Gestational'], ['prefer_not_to_disclose', 'Prefer not to say']]
const GOALS: [string, string][] = [['carb_awareness', 'Carbohydrate awareness'], ['calorie_awareness', 'Calorie awareness'], ['weight_management', 'Weight management'], ['balanced_nutrition', 'Balanced nutrition'], ['diabetes_friendly', 'Diabetes-friendly choices'], ['heart_health', 'Heart health (salt & saturated fat)']]

const num = (v: string) => (v === '' ? null : Number(v))
function Num({ label, value, onChange, unit, step = 1 }: { label: string; value: number | null; onChange: (v: number | null) => void; unit?: string; step?: number }) {
  return <label className="block"><span className="label">{label}{unit && <span className="text-slate-400 font-normal"> ({unit})</span>}</span>
    <input className="input" inputMode="decimal" type="number" step={step} value={value ?? ''} onChange={e => onChange(num(e.target.value))} /></label>
}

export function ProfileStep({ step, p, set }: { step: number; p: Profile; set: (p: Profile) => void }) {
  const u = <K extends keyof Profile>(k: K) => (v: Profile[K]) => set({ ...p, [k]: v })
  const [custom, setCustom] = useState('')
  if (step === 0) return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Num label="Age" value={p.age} onChange={u('age')} />
        <label className="block"><span className="label">Sex <span className="text-slate-400 font-normal">(optional)</span></span>
          <select className="input" value={p.sex ?? ''} onChange={e => u('sex')(e.target.value || null)}>
            <option value="">—</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option><option value="prefer_not_to_say">Prefer not to say</option>
          </select></label>
        <Num label="Height" unit="cm" value={p.height_cm} onChange={u('height_cm')} />
        <Num label="Weight" unit="kg" value={p.weight_kg} onChange={u('weight_kg')} step={0.1} />
      </div>
      <div><label className="label">Activity level</label>
        <Toggle options={[['sedentary', 'Sedentary'], ['light', 'Light'], ['moderate', 'Moderate'], ['active', 'Active'], ['very_active', 'Very active']]} value={p.activity_level} onChange={u('activity_level')} /></div>
      <div><label className="label">Diet preferences</label><Toggle multi options={DIET} value={p.diet_preferences} onChange={u('diet_preferences')} /></div>
    </div>
  )
  if (step === 1) return (
    <div className="space-y-4">
      <label className="flex gap-3 rounded-xl bg-brand-50 ring-1 ring-brand-100 p-3.5 cursor-pointer">
        <input type="checkbox" className="mt-1 size-4 accent-teal-600" checked={p.health_consent} onChange={e => u('health_consent')(e.target.checked)} />
        <span className="text-sm text-slate-700"><b className="flex items-center gap-1"><Lock className="size-3.5" />I consent to MealSenseAI storing my health information</b>
          Used only to tailor educational insights. Optional, editable and deletable anytime. Without consent, diabetes details are not stored.</span>
      </label>
      <div><label className="label">Diabetes status</label><Toggle options={DIABETES} value={p.diabetes_status} onChange={u('diabetes_status')} /></div>
      <div><label className="label">Allergies</label><Toggle multi options={ALLERGY} value={p.allergies} onChange={u('allergies')} /></div>
      <div><label className="label">Other dietary restrictions</label>
        <div className="flex gap-2"><input className="input" value={custom} placeholder="e.g. low sodium" onChange={e => setCustom(e.target.value)} />
          <button type="button" className="btn-ghost" onClick={() => { if (custom.trim()) { u('restrictions')([...p.restrictions, custom.trim()]); setCustom('') } }}>Add</button></div>
        <div className="flex flex-wrap gap-1.5 mt-2">{p.restrictions.map(r => <button type="button" key={r} className="chip bg-slate-100" onClick={() => u('restrictions')(p.restrictions.filter(x => x !== r))}>{r} ✕</button>)}</div>
      </div>
    </div>
  )
  if (step === 2) return (
    <div className="space-y-4">
      {!p.health_consent && <p className="text-sm rounded-xl bg-amber-50 text-amber-800 ring-1 ring-amber-200 p-3">Health consent is off — these optional fields won't be saved. You can skip this step.</p>}
      <div><label className="label">Glucose unit</label><Toggle options={[['mmol/L', 'mmol/L'], ['mg/dL', 'mg/dL']]} value={p.glucose_unit} onChange={v => u('glucose_unit')(v || 'mmol/L')} /></div>
      <div className="grid grid-cols-2 gap-3">
        <Num label="Latest HbA1c" unit="%" step={0.1} value={p.hba1c} onChange={u('hba1c')} />
        <div><label className="label">Uses a CGM?</label><Toggle options={[['yes', 'Yes'], ['no', 'No']]} value={p.has_cgm === null ? null : p.has_cgm ? 'yes' : 'no'} onChange={v => u('has_cgm')(v === null ? null : v === 'yes')} /></div>
      </div>
      <label className="block"><span className="label">Known readings <span className="text-slate-400 font-normal">(optional)</span></span>
        <textarea className="input" rows={2} placeholder={`e.g. fasting 6.1 ${p.glucose_unit}`} value={p.known_readings ?? ''} onChange={e => u('known_readings')(e.target.value || null)} /></label>
      <label className="block"><span className="label">Targets provided by your clinician <span className="text-slate-400 font-normal">(optional)</span></span>
        <textarea className="input" rows={2} value={p.clinician_targets ?? ''} onChange={e => u('clinician_targets')(e.target.value || null)} />
        <p className="text-xs text-slate-400 mt-1">MealSenseAI never sets clinical targets or gives medication advice.</p></label>
    </div>
  )
  return (
    <div className="space-y-4">
      <div><label className="label">What would you like help with?</label><Toggle multi options={GOALS} value={p.goals} onChange={u('goals')} /></div>
      <div className="grid grid-cols-3 gap-3">
        <Num label="Daily calories" unit="kcal" value={p.calorie_goal} onChange={u('calorie_goal')} />
        <Num label="Daily carbs" unit="g" value={p.carb_goal_g} onChange={u('carb_goal_g')} />
        <Num label="Daily protein" unit="g" value={p.protein_goal_g} onChange={u('protein_goal_g')} />
      </div>
      <p className="text-xs text-slate-400">Optional, self-chosen goals used only to show progress.</p>
    </div>
  )
}
