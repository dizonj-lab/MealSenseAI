import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

/** App-wide access to the Meal Advisor: any page can open it (optionally with a question) and set the meal in view. */
type Ctx = { open: boolean; mealId: number | null; prompt: string | null
  openAdvisor: (o?: { prompt?: string; mealId?: number | null }) => void; close: () => void
  setContextMeal: (id: number | null) => void; takePrompt: () => string | null }
const AdvisorCtx = createContext<Ctx | null>(null)

export function AdvisorProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [mealId, setMealId] = useState<number | null>(null)
  const [prompt, setPrompt] = useState<string | null>(null)
  const openAdvisor = useCallback((o: { prompt?: string; mealId?: number | null } = {}) => {
    if (o.mealId !== undefined) setMealId(o.mealId)
    setPrompt(o.prompt ?? null); setOpen(true)
  }, [])
  const takePrompt = useCallback(() => { const p = prompt; if (p) setPrompt(null); return p }, [prompt])
  return <AdvisorCtx.Provider value={{ open, mealId, prompt, openAdvisor, close: () => setOpen(false), setContextMeal: setMealId, takePrompt }}>{children}</AdvisorCtx.Provider>
}

const NOOP: Ctx = { open: false, mealId: null, prompt: null, openAdvisor: () => {}, close: () => {}, setContextMeal: () => {}, takePrompt: () => null }
export const useAdvisor = () => useContext(AdvisorCtx) ?? NOOP
