import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { BookOpen, Cpu, Database, FlaskConical, History, ShieldAlert, UserRound } from 'lucide-react'
import { useApi } from '../lib/hooks'
import { APP_VERSION, CHANGELOG } from '../lib/version'
import { Card } from '../components/ui'
import CreatorProfile from '../components/CreatorProfile'
import { DEMO, DemoDialog, PlayIcon, openDemo } from '../components/DemoVideo'

const Row = ({ k, v }: { k: string; v: React.ReactNode }) => (
  <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-3 py-1.5 border-b border-slate-100 last:border-0 text-sm"><dt className="text-slate-500">{k}</dt><dd className="text-slate-800">{v}</dd></div>)

/** About: datasets, pre-trained model, evaluation (measured vs reported) and release notes. */
export default function About() {
  const { data: h } = useApi<any>('/health')
  const loc = useLocation()
  useEffect(() => { if (loc.hash) document.getElementById(loc.hash.slice(1))?.scrollIntoView() }, [loc.hash])
  return (
    <div className="space-y-4 max-w-3xl">
      <Card title="About MealSenseAI" icon={<BookOpen className="size-5 text-brand-600" />}>
        <p className="text-sm text-slate-600">MealSenseAI recognises the foods in a meal photo, estimates portions and nutrition, and explains what the meal may mean for your energy and glucose, with every step open to correction. It is an educational tool, not a medical device.</p>
        <dl className="mt-3"><Row k="App version" v={`v${APP_VERSION}`} /><Row k="Server" v={h ? `v${h.version ?? '?'} · vision ${h.vision ? 'online' : 'offline'} · text SLM ${h.slm ? h.slm_model : 'offline'}` : '…'} /></dl>
      </Card>

      <section id="demo" className="scroll-mt-20"><button type="button" onClick={openDemo}
        className="card w-full p-4 flex items-center gap-4 text-left hover:ring-2 hover:ring-brand-500/40 transition">
        <span className="size-12 shrink-0 rounded-2xl bg-brand-600 text-white grid place-items-center"><PlayIcon className="size-5" /></span>
        <span className="min-w-0"><span className="block font-semibold text-slate-800">Watch the {DEMO.length} tour</span>
          <span className="block text-sm text-slate-500">One hawker lunch from photo to portions, glucose impact, a portion and walking what-if, and the Meal Advisor.</span></span>
      </button></section>
      <DemoDialog />

      <section id="creator" className="scroll-mt-20"><Card title="About the creator" icon={<UserRound className="size-5 text-brand-600" />}>
        <CreatorProfile />
      </Card></section>

      <Card title="Datasets" icon={<Database className="size-5 text-sky-600" />}>
        <p className="text-sm text-slate-600 mb-3">The food classifier was trained on two public research datasets, harmonised into one 320-class taxonomy.</p>
        <div className="space-y-4">
          <div className="rounded-xl bg-slate-50 p-3">
            <h3 className="font-semibold text-slate-800">Food-101</h3>
            <p className="text-sm text-slate-600 mt-1">101 food categories, 101,000 images (750 training and 250 manually reviewed test images per class). Training images were intentionally left uncleaned, so they contain some label noise. Created at ETH Zürich; images originally from Foodspotting.</p>
            <p className="text-xs text-slate-500 mt-2"><b>Cite:</b> L. Bossard, M. Guillaumin, L. Van Gool. “Food-101 – Mining Discriminative Components with Random Forests.” <i>European Conference on Computer Vision (ECCV)</i>, LNCS, pp. 446–461, Springer, 2014. <a className="text-brand-700 underline" href="https://doi.org/10.1007/978-3-319-10599-4_29" target="_blank" rel="noreferrer">doi:10.1007/978-3-319-10599-4_29</a></p>
            <p className="text-xs text-slate-500 mt-1"><b>Terms:</b> for research (scientific fair use); the images remain the property of their owners. <a className="text-brand-700 underline" href="https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/" target="_blank" rel="noreferrer">Dataset page</a></p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <h3 className="font-semibold text-slate-800">FoodSG-233</h3>
            <p className="text-sm text-slate-600 mt-1">233 popular Singaporean dishes across 13 food groups, 209,861 curated images, released by the FoodSG team at the National University of Singapore and partners.</p>
            <p className="text-xs text-slate-500 mt-2"><b>Cite:</b> K. Zheng, T. Nguyen, J. H. S. Chong, C. E. Goh, M. Herschel, H. H. Lee, C. Liu, B. C. Ooi, W. Wang, J. Yip. “From Plate to Prevention: A Dietary Nutrient-aided Platform for Health Promotion in Singapore.” arXiv:2301.03829, 2023. <a className="text-brand-700 underline" href="https://arxiv.org/abs/2301.03829" target="_blank" rel="noreferrer">arxiv.org/abs/2301.03829</a></p>
            <p className="text-xs text-slate-500 mt-1"><b>Terms:</b> non-commercial research and education only; access is granted by the authors on request. <a className="text-brand-700 underline" href="https://foodlg.comp.nus.edu.sg/" target="_blank" rel="noreferrer">foodlg.comp.nus.edu.sg</a></p>
          </div>
          <p className="text-xs text-slate-500">Nutrition values come from the app's reference table (286 foods): 62 transcribed from USDA FoodData Central, 20 from Singapore HPB's Energy &amp; Nutrient Composition of Food, and 204 typical-recipe approximations added so most model classes have a value. None are independently verified, and each item shows its source. GI values follow the International Tables of Glycemic Index (Atkinson et al., 2021) where available.</p>
        </div>
      </Card>

      <Card title="Pre-trained model" icon={<Cpu className="size-5 text-violet-600" />}>
        <dl>
          <Row k="Model" v="MealSenseAI EXP-002 — EfficientNet-B0" />
          <Row k="Pre-training" v="ImageNet-1k weights (torchvision), then EXP-001 on the unified Food-101 + FoodSG taxonomy" />
          <Row k="Fine-tuning" v="EXP-002: last 3 feature blocks + classifier head, 5 epochs" />
          <Row k="Classes" v="320 (Food-101 + FoodSG, harmonised)" />
          <Row k="Input" v="Resize 256 → centre crop 224 → ImageNet normalisation" />
          <Row k="Runtime" v="ONNX Runtime on CPU (GPU optional); outputs are raw softmax scores, not calibrated probabilities" />
          <Row k="Supporting models" v="YOLO11n-seg (COCO) for cups, bowls and cutlery; class-agnostic colour segmentation for food regions; optional local text SLM (Ollama) for explanations and the Meal Advisor" />
        </dl>
      </Card>

      <Card title="Evaluation" icon={<FlaskConical className="size-5 text-emerald-600" />}>
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-slate-500"><th className="py-1.5 pr-3 font-medium">What</th><th className="pr-3 font-medium">Result</th><th className="font-medium">Status</th></tr></thead>
          <tbody className="align-top">
            {[
              ['Classification (EXP-002 test split)', 'top-1 70.63% · top-3 85.66% · macro-F1 66.68%', 'Reported by model developer; not re-measured here (datasets not shipped)'],
              ['Runtime equivalence (601 images)', 'top-1/top-3 agreement 100%; max logit difference 1.35×10⁻⁴', 'Measured'],
              ['Multi-food detection (100 synthetic plates, 263 items)', 'precision 0.75 · recall 0.68 · AP50 0.59; matched items top-1 0.56 / top-3 0.75', 'Measured on synthetic composites of Food-101 test images; not real meals'],
              ['Single-dish photos (75)', '43 shown as exactly one item', 'Measured'],
              ['Food memory fingerprints', '94/120 held-out photos matched, all correct (threshold 0.70)', 'Measured on 3 classes only'],
              ['Latency (CPU)', '≈12 ms classifier; ≈260 ms full multi-food analysis per photo', 'Measured on a 4-vCPU test machine'],
            ].map(([a, b, c]) => <tr key={a} className="border-t border-slate-100"><td className="py-2 pr-3 text-slate-700">{a}</td><td className="pr-3 text-slate-800">{b}</td><td className="text-xs text-slate-500">{c}</td></tr>)}
          </tbody></table></div>
        <p className="mt-2 text-xs text-slate-500">Not measured: accuracy on real multi-food photos, portion-size error, and any glucose prediction (the glucose curves are illustrative simulations).</p>
      </Card>

      <Card title="Safety" icon={<ShieldAlert className="size-5 text-amber-500" />}>
        <p className="text-sm text-slate-600">Educational information only. MealSenseAI does not diagnose, does not predict your personal glucose response and never recommends medication or insulin doses. Talk to your healthcare team about your care.</p>
      </Card>

      <section id="whats-new" className="scroll-mt-20">
        <Card title="What's new" icon={<History className="size-5 text-brand-600" />}>
          <ol className="space-y-4">{CHANGELOG.map(r => (
            <li key={r.version}><div className="flex items-baseline gap-2"><span className="chip bg-brand-50 text-brand-700">v{r.version}</span><span className="font-semibold text-slate-800">{r.title}</span></div>
              <ul className="mt-1.5 list-disc pl-5 text-sm text-slate-600 space-y-0.5">{r.changes.map(c => <li key={c}>{c}</li>)}</ul></li>))}</ol>
        </Card>
      </section>
    </div>
  )
}
