export type Nutrients = { calories_kcal: number | null; carbs_g: number | null; protein_g: number | null; fat_g: number | null; sat_fat_g?: number | null; sugar_g: number | null; fiber_g: number | null; sodium_mg: number | null }
export type Profile = {
  health_consent: boolean; age: number | null; sex: string | null; height_cm: number | null; weight_kg: number | null
  activity_level: string | null; diet_preferences: string[]; diabetes_status: string | null; allergies: string[]; restrictions: string[]
  glucose_unit: string; known_readings: string | null; hba1c: number | null; has_cgm: boolean | null; clinician_targets: string | null
  goals: string[]; calorie_goal: number | null; carb_goal_g: number | null; protein_goal_g: number | null
}
export type User = { id: number; email: string; name: string; onboarded: boolean; training_consent?: boolean; created_at: string; profile: Profile | null }
export type BBox = { x: number; y: number; w: number; h: number }
export type Food = {
  id: number; origin: 'model' | 'description' | 'manual' | 'slm'; label: string; taxonomy_class?: string | null; nutrition_key: string | null
  mapping_quality: 'exact' | 'proxy' | 'fuzzy' | 'provisional' | 'none'; original_prediction: any; grams: number
  portion: { method: string; uncertainty: string; range_g: [number, number] | null; relative_error?: string; notes: string[] }
  nutrients: Nutrients; nutrition_source: any; confirmed: boolean; user_corrected: boolean; removed: boolean
}
export type Stage = { key: string; name: string; status: string; detail: string; latency_ms: number; per_view?: any[] }
export type Insights = {
  glucose: { level: string; carbs_g: number; available_carbs_g: number; sugar_g: number | null; fiber_g: number; glycemic_load: number | null; gi_coverage: number; reasoning: string[]; disclaimer: string }
  energy: { calories_kcal: number; carbs_g: number | null; protein_g: number | null; fat_g: number | null; fiber_g: number | null; sugar_g: number | null; sodium_mg: number | null; macro_energy_pct: Record<string, number>; goal_progress: { label: string; value: number; goal: number; unit: string; pct: number }[]; notes: string[] }
  recommendations: { tag: string; title: string; detail: string }[]
  allergy_warnings: string[]
  personalised?: { audience: string; title: string; detail: string; basis: string }[]
  explanation: { text: string | null; source: string }
  generated_at?: string
}
export type Meal = {
  id: number; status: string; meal_type: string | null; description: string | null; reference_object: string | null; serving_note: string | null
  images: { view: string; warnings: string[]; processed_size: number[]; overlay_path?: string | null }[]
  totals: Nutrients & { grams: number; item_count: number; incomplete_nutrients: string[]; unmapped_items: string[] }
  insights: Insights; model_info: any; stages: Stage[]; eaten_at: string; created_at: string; foods: Food[]
}
export type FoodRef = { key: string; name: string; category: string; region: string; default_serving_g: number; serving_desc: string; custom?: boolean }
