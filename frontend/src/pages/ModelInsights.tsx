import { Cpu, Database, FlaskConical, MessageSquareText, Ruler, UserCheck } from 'lucide-react'
import { fmt } from '../lib/api'
import { useApi } from '../lib/hooks'
import { Card, Spinner } from '../components/ui'

const Row = ({ k, v }: { k: string; v: any }) => <div className="flex justify-between gap-3 py-1.5 text-sm border-b border-slate-50 last:border-0"><span className="text-slate-500">{k}</span><span className="text-right font-medium text-slate-800">{v}</span></div>

export default function ModelInsights() {
  const { data: d } = useApi<any>('/ai/models')
  if (!d) return <div className="grid place-items-center py-20"><Spinner /></div>
  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-3 gap-4">
        {d.vision.models.map((m: any) => (
          <Card key={m.name} title={m.name} icon={<Cpu className="size-5 text-brand-600" />} action={<span className={`chip ${d.vision.available ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{d.vision.available ? 'Active' : 'Unavailable'}</span>}>
            <Row k="Pipeline stage" v={m.stage} /><Row k="Task" v={m.task} /><Row k="Version" v={m.version} /><Row k="Trained on" v={m.trained_on} /><Row k="Food classes" v={m.food_classes} />
            <Row k="Inferences" v={m.latency.count} /><Row k="Latency avg / p95" v={m.latency.count ? `${m.latency.avg_ms} / ${m.latency.p95_ms} ms` : '—'} />
            <Row k="Scores calibrated" v="No (raw scores shown qualitatively)" />
            <Row k="Accuracy" v={m.test_metrics ? <span className="text-emerald-700">{m.accuracy}</span> : <span className="text-amber-700">{m.accuracy}</span>} />
          </Card>))}
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Local SLM (Ollama)" icon={<MessageSquareText className="size-5 text-sky-600" />} action={<span className={`chip ${d.slm.available ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{d.slm.available ? 'Online' : 'Offline'}</span>}>
          <Row k="Endpoint" v={d.slm.url} /><Row k="Selected model" v={d.slm.selected ?? '—'} /><Row k="Installed models" v={d.slm.models.join(', ') || '—'} />
          <Row k="Role" v={d.slm.role} /><Row k="Calls / avg latency" v={`${d.slm.calls} / ${d.slm.avg_latency_ms} ms`} /><Row k="Tokens · cost" v={`${d.slm.tokens} · ${d.slm.cost}`} />
          {d.slm.error && <p className="mt-2 text-xs text-amber-700">{d.slm.error}. Rule-based fallbacks are used.</p>}
        </Card>
        <Card title="Nutrition data" icon={<Database className="size-5 text-emerald-600" />}>
          <Row k="Table" v={d.nutrition.table} /><Row k="Records" v={d.nutrition.records} /><Row k="Verification" v={<span className="text-amber-700">{d.nutrition.verification.replace('_', ' ')}</span>} />
          <ul className="mt-2 text-xs text-slate-500 list-disc pl-4">{d.nutrition.sources.map((s: string) => <li key={s}>{s}</li>)}</ul>
          <Row k="Cache" v={`${d.cache.backend} · ${d.cache.hits} hits / ${d.cache.misses} misses`} />
        </Card>
        <Card title="Portion estimation" icon={<Ruler className="size-5 text-amber-500" />}>
          <Row k="Method" v={d.portion.method} /><Row k="Volume measured" v="No" />
          <p className="text-xs text-slate-500 mt-2">Two photos without a calibrated scale or depth sensor cannot establish reliable volume. Estimates carry ±35–50% bands until you enter grams.</p>
        </Card>
        <Card title="Your corrections" icon={<UserCheck className="size-5 text-brand-600" />}>
          {['confirm', 'edit_food', 'edit_portion', 'add', 'remove'].map(k => <Row key={k} k={k.replace('_', ' ')} v={d.corrections[k] ?? 0} />)}
          <Row k="Model foods kept unchanged" v={d.user_agreement.rate === null ? '—' : `${fmt(d.user_agreement.rate * 100)}% (${d.user_agreement.accepted_unchanged}/${d.user_agreement.accepted_unchanged + d.user_agreement.corrected_or_removed})`} />
          <p className="text-xs text-slate-400 mt-1">{d.user_agreement.note}</p>
        </Card>
      </div>
      <Card title="Experiments" icon={<FlaskConical className="size-5 text-violet-600" />}>
        {d.experiments.length === 0 ? <p className="text-sm text-slate-500">No evaluation runs recorded. Run <code className="text-xs bg-slate-100 px-1 rounded">ml/evaluation/evaluate.py</code> on a labeled dataset (e.g. Food-101) to measure accuracy, precision, recall and F1.</p> :
          <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th className="py-1">Run</th><th>Model</th><th>Dataset</th><th>N</th><th>Metrics</th></tr></thead>
            <tbody>{d.experiments.map((e: any) => <tr key={e.id} className="border-t border-slate-100 align-top"><td className="py-1.5">{e.name}</td><td>{e.model}</td><td>{e.dataset}</td><td>{e.n_samples}</td>
              <td className="text-xs">{e.has_ground_truth ? Object.entries(e.metrics).filter(([, v]) => typeof v === 'number').map(([k, v]) => `${k}: ${(v as number).toFixed(3)}`).join(' · ') : 'latency only (no ground truth)'}</td></tr>)}</tbody></table></div>}
      </Card>
    </div>
  )
}
