import { useEffect, useState } from 'react'
import { Search, X } from 'lucide-react'
import { api } from '../lib/api'
import type { FoodRef } from '../lib/types'

export default function FoodPicker({ title, onPick, onClose, initial = '' }: { title: string; onPick: (f: FoodRef, grams: number | null) => void; onClose: () => void; initial?: string }) {
  const [q, setQ] = useState(initial)
  const [list, setList] = useState<FoodRef[]>([])
  const [sel, setSel] = useState<FoodRef | null>(null)
  const [grams, setGrams] = useState('')
  useEffect(() => {
    const t = setTimeout(() => api<FoodRef[]>(`/foods/search?q=${encodeURIComponent(q)}`).then(setList).catch(() => {}), 150)
    return () => clearTimeout(t)
  }, [q])
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div className="relative w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl max-h-[85vh] flex flex-col pb-safe">
        <div className="flex items-center justify-between p-4 pb-2"><h3 className="font-semibold">{title}</h3><button onClick={onClose} className="p-1"><X className="size-5" /></button></div>
        <div className="px-4 relative"><Search className="size-4 absolute left-7 top-3.5 text-slate-400" />
          <input autoFocus className="input pl-9" placeholder="Search e.g. chicken rice, laksa, apple" value={q} onChange={e => { setQ(e.target.value); setSel(null) }} /></div>
        <ul className="overflow-y-auto px-2 py-2 flex-1">
          {list.map(f => (
            <li key={f.key}><button onClick={() => { setSel(f); setGrams(String(f.default_serving_g)) }}
              className={`w-full text-left rounded-xl px-3 py-2.5 flex justify-between gap-2 ${sel?.key === f.key ? 'bg-brand-50 ring-1 ring-brand-200' : 'hover:bg-slate-50'}`}>
              <span><span className="font-medium text-slate-800">{f.name}</span>{f.region === 'sg' && <span className="chip bg-sky-50 text-sky-700 ml-2">SG</span>}</span>
              <span className="text-xs text-slate-400 shrink-0">{f.serving_desc} · {f.default_serving_g} g</span></button></li>))}
        </ul>
        {sel && <div className="border-t border-slate-100 p-4 flex gap-2 items-end">
          <label className="block flex-1"><span className="label">Portion (grams)</span><input className="input" type="number" inputMode="decimal" value={grams} onChange={e => setGrams(e.target.value)} /></label>
          <button className="btn-primary" onClick={() => onPick(sel, grams ? Number(grams) : null)}>Use {sel.name.split(' ')[0]}</button>
        </div>}
      </div>
    </div>
  )
}
