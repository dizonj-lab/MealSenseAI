// MealSenseAI final report (Word). Every figure is from the repository's evidence files or a cited source.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, ImageRun, PageBreak, TableOfContents, Footer, Header, PageNumber, LevelFormat,
} = require("docx");

const HERE = __dirname;
const CH = (f) => path.join(HERE, "charts", f);
const SLM = fs.existsSync(path.join(HERE, "slm_eval.json")) ? JSON.parse(fs.readFileSync(path.join(HERE, "slm_eval.json"), "utf8")) : null;
const TEAL = "147D73", INK2 = "52514E", RULE = "D9DED c".replace(" c", "");
const W = 9026; // A4 text width in DXA (2.5 cm margins: 11906 - 2*1440)

// ---------------------------------------------------------------- helpers
const run = (t, o = {}) => new TextRun({ text: t, ...o });
const rich = (s) => {   // **bold** and *italic* inside a string
  const out = [];
  s.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/).forEach((part) => {
    if (!part) return;
    if (part.startsWith("**")) out.push(run(part.slice(2, -2), { bold: true }));
    else if (part.startsWith("*")) out.push(run(part.slice(1, -1), { italics: true }));
    else out.push(run(part));
  });
  return out;
};
const P = (s, o = {}) => new Paragraph({ children: rich(s), spacing: { after: 120, line: 288 }, ...o });
const H1 = (t, br = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(t)], pageBreakBefore: br, spacing: br ? undefined : { before: 400, after: 200 } });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [run(t)] });
const BUL = (items) => items.map((s) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: rich(s), spacing: { after: 60, line: 276 } }));
const NUM = (items, ref = "num") => items.map((s) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: rich(s), spacing: { after: 60, line: 276 } }));
const EQ = (s) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 }, children: [run(s, { font: "Cambria Math", size: 23 })] });
let figN = 0, tabN = 0;
const FIG = (file, widthIn, caption) => {
  const buf = fs.readFileSync(CH(file));
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const px = widthIn * 96;
  figN += 1;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: px, height: Math.round(px * h / w) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [run(`Figure ${figN}. `, { bold: true, size: 18, color: INK2 }), ...rich(caption).map((r) => { r.options = r.options; return r; })].map((r) => r), style: "Caption" }),
  ];
};
const border = { style: BorderStyle.SINGLE, size: 4, color: "D9DEDC" };
const borders = { top: border, bottom: border, left: border, right: border };
const TABLE = (caption, head, rows, widths) => {
  tabN += 1;
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, isHead) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: isHead ? { fill: "E6F2F0", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: isHead ? [run(t, { bold: true, size: 19 })] : rich(String(t)).map((r) => r), spacing: { after: 0, line: 252 } })],
  });
  return [
    new Paragraph({ keepNext: true, spacing: { before: 160, after: 80 }, children: [run(`Table ${tabN}. `, { bold: true, size: 18, color: INK2 }), run(caption, { size: 18, color: INK2 })] }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true)) }),
             ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))] }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
};

// ---------------------------------------------------------------- language-model results (from Buddy, if present)
const slmRows = SLM ? [
  ["Description parsing (20)", `F1 ${SLM.parse.slm.f1} (P ${SLM.parse.slm.precision}, R ${SLM.parse.slm.recall}); exact sets ${SLM.parse.slm_exact_sets}/20`, `F1 ${SLM.parse.rules.f1}; exact sets ${SLM.parse.rules_exact_sets}/20`, `${SLM.parse.latency_ms.p50} / ${SLM.parse.latency_ms.p95}`],
  ["Unknown-name matching (15)", `${Math.round(SLM.match.accuracy * 15)}/15 correct (${SLM.match.correct_when_in_table} in table, ${SLM.match.abstained_when_absent} abstained); ${SLM.match.slm_wrong_match} wrong`, `${Math.round(SLM.match.lookup_accuracy * 15)}/15 correct; ${SLM.match.lookup_wrong_match} wrong`, `${SLM.match.latency_ms.p50} / ${SLM.match.latency_ms.p95}`],
  ["Meal explanation (6)", `${SLM.explain.grounded} grounded (every number from the facts)`, "rule text (always grounded)", `${SLM.explain.latency_ms.p50} / ${SLM.explain.latency_ms.p95}`],
  ["Advisor rewording (8)", `${SLM.rewrite.passed_validator} passed the validator`, "rule answer shown", `${SLM.rewrite.latency_ms.p50} / ${SLM.rewrite.latency_ms.p95}`],
] : null;

// ---------------------------------------------------------------- content
const cover = [
  new Paragraph({ spacing: { before: 2600 }, children: [] }),
  new Paragraph({ children: [run("MealSenseAI", { bold: true, size: 72, color: TEAL })] }),
  new Paragraph({ spacing: { after: 240 }, children: [run("Understand your food. Make healthier choices.", { size: 30, color: INK2 })] }),
  new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL, space: 6 } }, spacing: { after: 360 }, children: [] }),
  new Paragraph({ spacing: { after: 120 }, children: [run("Final Report", { bold: true, size: 36 })] }),
  new Paragraph({ spacing: { after: 600 }, children: [run("A photo-based meal recognition and nutrition-awareness system for anyone who wants to understand their food, starting with people managing diabetes in Singapore", { size: 24, color: INK2 })] }),
  new Paragraph({ spacing: { after: 80 }, children: [run("NUS-ISS Practice Project (PT & Stackable) · Individual project", { size: 22 })] }),
  new Paragraph({ spacing: { after: 80 }, children: [run("Dizon Joselito Villanueva", { size: 22 })] }),
  new Paragraph({ spacing: { after: 80 }, children: [run("Final draft · 29 October 2026 · system version v0.13.13 · follows the proposal of 30 September 2026", { size: 22, color: INK2 })] }),
  new Paragraph({ spacing: { before: 2400 }, children: [run("Educational estimates, not medical advice. Wei Ming, used in examples, is fictional.", { size: 18, color: INK2, italics: true })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

const toc = [
  new Paragraph({ children: [run("Contents", { bold: true, size: 32, color: TEAL })], spacing: { after: 200 } }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ spacing: { before: 200 }, children: [run("If the contents list is empty, right-click it in Word and choose Update Field.", { size: 16, color: INK2, italics: true })] }),
];

const summary = [
  H1("Executive summary"),
  P("People living with diabetes decide what and how much to eat several times a day, and most hawker meals carry no label. **MealSenseAI** turns one meal photo into foods, portions and nutrition, then into meaning: potential glucose impact, glycaemic load (GL) and a practical next step, with every estimate labelled and correctable. It serves anyone, with or without a health condition: the profile sets goals such as general wellness, weight, heart health or balanced eating, and the guidance adapts. Diabetes is the first focus, as proposed, because the need there is sharpest."),
  ...TABLE("Headline results (all measured unless marked)", ["Area", "Result", "Evidence"], [
    ["Food recognition", "EfficientNet-B0, 320 classes: **70.6% top-1, 85.7% top-3**, macro-F1 66.7% (developer evaluation)", "model_card.json"],
    ["Runtime fidelity", "ONNX export gives the **same top-3 on 601 of 601 images**; 11.8 ms per photo on CPU", "onnx_parity.json"],
    ["Multi-food plates", "Detection **precision 74.7%, recall 68.4%**; 262 ms median per plate", "multifood_metrics.json"],
    ["Grounded advisor", "**38/38** test questions passed, **0%** unsupported claims, 12 ms median (rule engine)", "advisor_eval.json"],
    ["Coverage", "247 of 320 classes map exactly to a nutrition record; GL now estimable for **135 of 286** foods (57 published GI + 78 borrowed)", "nutrition_coverage.json, v0.13.8"],
    ["Quality", "**65** automated tests passing; 9/9 acceptance checks, also offline; data kept across restart", "TEST_REPORT.md"],
    ["Language model", SLM ? `qwen2.5:1.5b on Buddy: ${SLM.rewrite.passed_validator} rewordings passed the validator; ${SLM.explain.grounded} explanations grounded` : "Benchmark ready (app/tools/slm_eval.py); **results pending** the run on the deployment server", "slm_eval.json"],
  ], [1900, 5026, 2100]),
  P("The main weaknesses are honest ones: visually similar dishes (steak was recognised as itself in only 11% of matched cases), portions that a photo cannot weigh (±35–50%), nutrition values that are transcribed but not yet verified, and no trial with real users yet. Section 7 discusses each and the planned next steps."),
];

const business = [
  H1("1. Business case and market research"),
  H2("1.1 The problem"),
  P("A packet of biscuits states its sugar; a plate of chicken rice states nothing. In hawker meals the carbohydrate hides in the rice, the sauce and the drink, portions vary from stall to stall, and mixed dishes are hard to decompose. People therefore guess, and manual logging is tedious enough that most stop."),
  H2("1.2 Why it matters"),
  ...TABLE("Burden of diabetes (cited figures)", ["Indicator", "Figure", "Source"], [
    ["People living with diabetes worldwide", "about 830 million", "WHO, 2022 (cited in the project proposal)"],
    ["Adults in Singapore with diabetes", "about 1 in 12 (8.5%)", "MOH Singapore, 2023 (cited in the proposal)"],
    ["Singapore residents by 2050 without effective prevention", "up to 1 million", "MOH projection (cited in the proposal)"],
    ["Adults with diabetes, Singapore", "about 699,100 (2024)", "IDF Diabetes Atlas (cited in the proposal)"],
    ["Adults with diabetes, Southeast Asia", "34.9 million (2000) → 106.9 million (2024) → 184.5 million projected (2050)", "IDF Diabetes Atlas (cited in the proposal)"],
    ["Yearly cost of diabetes to Singapore", "about S$1 billion (2010), rising to S$2.5 billion (2050); most of it lost productivity", "Png et al., BMC Public Health 2016"],
    ["Effect of making nutrition visible", "about 18% less household sugar from pre-packed drinks after Nutri-Grade", "Before-and-after study (cited in the proposal)"],
  ], [3300, 3126, 2600]),
  P("The Nutri-Grade result is the business imperative in one line: when nutrition is easy to see, choices change. Labels, however, stop at the bottle and the box. The plate, where most carbohydrate is eaten, remains unlabelled."),
  H2("1.3 Existing solutions"),
  ...TABLE("Competitive landscape (indicative monthly prices as in the proposal, USD unless stated; MyFitnessPal and Healthy 365 added)", ["Product", "Model and positioning", "Price"], [
    ["Foodvisor", "Freemium + premium; AI nutrition and coaching", "from US$15/month"],
    ["Cal AI", "Freemium + premium; AI calorie tracking", "about US$9.99/month (about US$29.99 a year on annual billing)"],
    ["SnapCalorie", "Freemium + premium; AI food recognition", "US$8.99–19.99/month"],
    ["Healthify", "Freemium + premium/CGM; AI health and metabolic health", "US$10–60/month"],
    ["MyFitnessPal Premium", "General calorie and macro tracking, large food database", "US$79.99 a year"],
    ["Healthy 365 (HPB)", "Free government app; logging by search or photo, 3,000+ local foods", "Free"],
    ["**MealSenseAI (proposed)**", "Freemium + subscription; local food recognition, portion estimate, glucose meaning; ASEAN focus", "**S$3.99/month (Singapore), S$2.99/month (ASEAN)**"],
  ], [2300, 4426, 2300]),
  P("As the proposal put it, the goal is not to be the cheapest but to deliver the right features at a competitive price. Existing apps help people count calories or find a food. What remains hard is the moment of choice at the stall: knowing what this specific plate may do to glucose, and how sure that estimate is. MealSenseAI is designed around that moment."),
  H2("1.4 Value proposition and users"),
  ...BUL([
    "**One photo → foods, portions and nutrition**, with Singapore dishes in the 320-class vocabulary and a local nutrition table.",
    "**Numbers → meaning**: potential glucose impact, glycaemic load, a portion simulator and a walk what-if, before the person eats.",
    "**Honest by design**: every value is labelled as model prediction, estimate, guidance or the user's own input, with its range and source; nothing is saved until the user confirms.",
    "**Users**: anyone who wants to understand their food, with or without a health condition. The profile records a condition (none, prediabetes, Type 1, Type 2, gestational, or not disclosed) and goals (general wellness, carbohydrate or calorie awareness, weight management, balanced nutrition, diabetes-friendly, heart health); personalised notes follow them, for example salt and saturated fat against WHO limits for heart health, or energy density for weight.",
    "**First focus (MVP, as proposed)**: people with Type 1 and Type 2 diabetes in Singapore, where carbohydrate and portion awareness matter most; **also**: families and carers; **later**: organisations that support members. For Type 1 diabetes the app supports awareness only and is never a basis for insulin dosing.",
    "**Market focus**: Singapore first, scaling to Southeast Asia; aligned with UN SDG 3 (good health and well-being).",
  ]),
  H2("1.5 Pricing and market scenario"),
  P("The proposal set a freemium model with a subscription at **SGD 3.99 a month in Singapore and SGD 2.99 a month in ASEAN markets**. The built product supports that split: logging and nutrition stay free, and the subscription carries the features that make the product different."),
  ...TABLE("Tiers (prices as proposed; feature split from the built product)", ["Tier", "Includes", "Price"], [
    ["Free", "Photo and text meal logging, nutrition per meal and day, history and trends", "S$0"],
    ["Subscription", "Glucose impact and GL, Meal Advisor, portion and activity simulators, personal glucose calibration", "S$3.99/month (Singapore) · S$2.99/month (ASEAN)"],
    ["Organisations (later)", "The same app for members of clinics, employers and insurers", "per member, to be set with pilots"],
  ], [2000, 4826, 2200]),
  ...TABLE("Illustrative market scenario from the proposal (not a forecast)", ["", "Singapore", "Southeast Asia"], [
    ["Addressable adults with diabetes", "~699,100", "~106.9 million (2024)"],
    ["Paying users (scenario)", "1% penetration ≈ 6,991", "scale scenario ≈ 3.9 million"],
    ["Price", "S$3.99/month", "S$2.99/month"],
    ["Year-1 gross revenue", "≈ S$334.7K at a constant user base; ≈ S$353.6K with 1% monthly growth", "≈ S$147.9 million with 1% monthly growth"],
    ["Operating cost assumption", "50% of revenue (planning range 40–60%)", "50% of revenue"],
  ], [2700, 3163, 3163]),
  P("The scenario counts people with diabetes only, so it is conservative: users without a condition are not included. These are scenario calculations carried over from the proposal, not financial forecasts. The cost assumption is not yet validated; what the build adds is evidence that the marginal compute cost is low, because every model runs on one CPU server with no paid AI service. Willingness to pay is part of the trial plan (Section 7.4)."),
];

const tools = [
  H1("2. Tools and techniques"),
  ...TABLE("Tools and techniques used, and why", ["Area", "Tool / technique", "Why"], [
    ["Food recognition", "EfficientNet-B0 (torchvision), transfer learning; ONNX Runtime", "Accurate for its size; runs in ~12 ms on CPU"],
    ["Food regions", "YOLO11n-seg (COCO), mask and box regions", "Finds several foods and containers on one plate"],
    ["Portions", "Typical-serving priors, mask-area ratio to plate or bowl, user grams; uncertainty bands", "A photo cannot weigh food; bands make that explicit"],
    ["Nutrition", "286-record table with provenance; exact / proxy / none mapping; difflib fuzzy lookup", "Every number traceable to a record"],
    ["Glycaemic load", "Published GI (Atkinson 2021) plus rule-based GI borrowing from the staple", "Covers local dishes without inventing values"],
    ["Glucose estimate", "One-compartment mass-balance ODE, OGTT anchor, per-user median-ratio calibration", "Explainable and conservative"],
    ["Language model", "Ollama with Qwen 2.5 1.5B, JSON-schema output, temperature control", "Local, small, structured; wording only"],
    ["Grounding", "Rule engine draft → SLM rewrite → validator (numbers ±2%, food names, unsafe phrases)", "No unsupported number reaches the user (advisor replies and, from v0.13.13, meal explanations)"],
    ["Personal memory", "Class-probability fingerprints, cosine similarity ≥ 0.70 with a 0.05 margin", "Recognises a user's own foods without retraining"],
    ["Data governance", "Per-sample consent, 11 screening checks, perceptual hashes, frozen dataset versions, model gate with shadow mode", "Safe learning from user photos"],
    ["Backend", "FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Python 3.12", "Typed API, migrations on start"],
    ["Frontend", "React 18, TypeScript, Vite 6, Tailwind CSS 4, Recharts", "Phone-first, light and dark themes"],
    ["Deployment", "Docker Compose (nginx, backend, db, optional Ollama and Redis), CPU", "One command; works offline"],
    ["Testing", "pytest on real PostgreSQL, Playwright browser flows, acceptance scripts", "No mocks of the database or the browser"],
    ["Analysis", "matplotlib, ffmpeg (demo video), python-docx / docx", "Report figures and the demo"],
  ], [1700, 4026, 3300]),
];

const design = [
  H1("3. System design and models"),
  H2("3.1 Architecture"),
  P("The system is four containers on one server (Figure 1). The browser only talks to nginx, which serves the app and proxies /api to the FastAPI backend. The backend holds the models, rules and advisor in one process and stores everything in PostgreSQL; meal photos and model packages live in a volume. An optional local language model runs beside it. No paid cloud AI is involved."),
  ...FIG("09_architecture.png", 6.2, "Deployment architecture."),
  H2("3.2 The ten-stage pipeline"),
  P("The pipeline follows the proposal's ten stages: meal capture, image pre-processing, food instance detection, food classification, portion estimation, nutrition mapping, meal aggregation, AI contextualisation (with the user's context), recommendations and application output (Figure 2). Each stage is shown to the user with what it did, and outputs are tagged by kind: model prediction, estimate, guidance or user input."),
  ...FIG("10_pipeline.png", 6.2, "Inference pipeline; colour shows the kind of output."),
  H2("3.3 Data"),
  P("As proposed, the localised source is **FoodSG-233** (209,861 images, 233 Singapore food classes, 13 food groups) and the general source is **Food-101** (101,000 images, 101 classes). Class names were harmonised into one taxonomy of **320 classes**, images validated and de-duplicated, and the data split **70% / 15% / 15%** (train / validation / test), stratified with a fixed seed so no duplicate crosses splits. Augmentation is applied to the training set only (ml/training/config.yaml). Every class maps to a nutrition record or is marked for the user to choose (Section 3.6)."),
  H2("3.4 Recognition model"),
  ...TABLE("EXP-002 training configuration (ml/models/exp002/evidence/train_finetune.py)", ["Setting", "Value"], [
    ["Backbone", "EfficientNet-B0, initialised from EXP-001 (ImageNet weights, unified Food-101 + FoodSG taxonomy)"],
    ["Classes", "320 (Food-101 and FoodSG, harmonised)"],
    ["Strategy", "Partial fine-tuning: last 3 feature blocks and the classifier head trainable"],
    ["Optimiser", "AdamW; learning rate 1e-5 (backbone), 5e-5 (head); weight decay 1e-4"],
    ["Schedule", "5 epochs, batch 32, seed 42, image 224 px"],
    ["Augmentation", "RandomResizedCrop (0.8–1.0), horizontal flip 0.5, rotation 20°, colour jitter (0.2, 0.2, 0.2, hue 0.05)"],
    ["Deployment", "ONNX (opset 17) on ONNX Runtime CPU; preprocessing bit-identical to training (max abs diff 0.0)"],
  ], [2200, 6826]),
  P("Optimisation choices were made for a CPU server: a compact backbone, partial fine-tuning (fewer parameters to adapt, less over-fitting on a modest dataset), discriminative learning rates (smaller for pretrained layers) and export to ONNX. Scores are raw softmax values, not calibrated probabilities, so the UI never presents them as \"% sure\"; items below 0.20 are not auto-added and items between 0.20 and 0.50 are marked for checking."),
  H2("3.5 Several foods on a plate"),
  P("YOLO11n-seg proposes food and container regions; each region is cropped from the original photo and classified. Weak regions become \"Unidentified food\" with the model's own top three, and small or nested ones are kept as hidden suggestions. Users can also drag a box over a missed food (v0.13.2), which is classified on its own."),
  H2("3.6 Portions, nutrition and glycaemic load"),
  ...BUL([
    "**Portion**: grams entered by the user (±15%), mask area against a detected plate or bowl (±35%), or a typical serving (±50%); a serving note such as \"half\" scales it.",
    "**Nutrition mapping**: each class maps to a record as exact (247), proxy, the nearest food (66), or none (7, the user chooses). Nutrients scale linearly with grams.",
    "**Glycaemic load**: GL = Σ GI × available carbohydrate / 100, reported only when GI covers at least 70% of the meal's available carbohydrate.",
    "**GI borrowing (v0.13.8)**: 229 of 286 foods have no published GI. Fixed, ordered rules match a dish's name to its staple (noodles before rice, so rice noodles are noodles) and borrow that GI, labelled \"≈ … borrowed from …\". Where there is a choice the higher-GI staple is used, so the estimate errs high. No language model is involved.",
  ]),
  H2("3.7 Glucose model"),
  P("The estimate is a one-compartment mass balance of meal-derived glucose G (g):"),
  EQ("dG/dt = Rₐ(t) − k·G − Uₑₓ(t)"),
  ...BUL([
    "**Rₐ**: appearance of the meal's glycaemic carbohydrate (available carbs × GI / 100) along a gamma-shaped absorption curve, whose peak is delayed by fat, fibre and protein.",
    "**k**: first-order clearance, slower with reduced insulin sensitivity (by diabetes status).",
    "**Uₑₓ**: extra uptake by working muscle, from activity energy E = MET × kg × h (Ainsworth 2011) and the carbohydrate share of fuel.",
    "**Scale**: the relative curve is anchored so a 75 g glucose drink gives a typical OGTT peak rise (+3, +5, +8 mmol/L for normal, prediabetes, diabetes). After three meals with before-and-after readings, the median ratio of measured to predicted rise calibrates it to the person.",
  ]),
  H2("3.8 Grounded Meal Advisor"),
  P("A rule engine writes each answer from the user's meals, profile and the food table, tagging every point with its evidence level (you, the model, the food table, guidance, calculated). If the local language model is available it only rewords the draft; a validator then checks that every number is within ±2% of a number in the facts, that no new food names appear, and that no unsafe statement (dosing, diagnosis, guarantees) is present. If any check fails, the rule answer is shown. Medication and urgent questions bypass the model entirely."),
  H2("3.9 Learning safely from users"),
  ...BUL([
    "**Personal memory**: a named photo region is stored as a fingerprint (square root of the 320 class probabilities). A later region is matched by cosine similarity ≥ 0.70 with a 0.05 margin over any other label. On held-out Food-101 photos, 0.70 gave 94 of 120 matches, all correct.",
    "**Consent and screening**: samples are shared for training only while the user's consent is on; withdrawal removes them from future datasets. Eleven checks (duplicates, implausible or carbohydrate-lowering relabels, repeated patterns across accounts, contributor caps, outliers) flag samples for human review.",
    "**Model gate**: a candidate must stay within 0.2 points of the live model's top-1 on a fixed test set, not regress on safety food groups (rice, noodles, sweet drinks), and agree with it on ≥ 90% of at least 200 foods in shadow mode before promotion.",
  ]),
];

const dev = [
  H1("4. System development and implementation"),
  H2("4.1 Process"),
  P("The system was built iteratively in versioned increments (v0.1 to v0.13.13, about 50 commits from 23 to 29 October 2026, following the proposal of 30 September). Each change was tested, versioned, recorded in the changelog and test report, and deployed to the home server (\"Buddy\") by the developer. The code base has about 6,800 lines of Python in the backend, 3,700 lines of TypeScript in the frontend and 2,000 lines of ML tooling, with 10 test modules."),
  H2("4.2 From proposal to build"),
  ...TABLE("Proposed design (30 September 2026) and what was built", ["Proposed", "Built", "Why"], [
    ["Web UI with a webcam; smartphone later", "Phone-first responsive web app (camera or upload) plus desktop", "Capture happens at the table, so the phone came first"],
    ["Reverse proxy, web app, application API", "nginx, React app, FastAPI", "As proposed"],
    ["Redis job queue and a separate ML worker", "One backend process; Redis optional as a cache", "A full analysis takes ~0.26 s on CPU, so a queue added complexity without benefit"],
    ["Vision inference service (YOLO-Seg, CNN)", "YOLO11n-seg + EfficientNet-B0 on ONNX Runtime, inside the backend", "Loaded once; ~12 ms per classification"],
    ["Local object storage (MinIO)", "A Docker volume for photos and model packages", "One server; no S3 API needed yet"],
    ["Model registry (MLflow)", "Model updates location, model gate with shadow mode, admin promotion and rollback", "Gate decisions are part of the app and audited"],
    ["ML development environment (Jupyter / PyTorch)", "ml/training pipeline and evaluation scripts", "Reproducible from a config file"],
    ["Nutrition reference store", "286-record table with provenance, plus users' custom foods", "As proposed"],
    ["Local SLM (Ollama); optional frontier LLM", "Ollama with Qwen 2.5 1.5B; no external LLM", "Data stays on the server; no paid AI service"],
    ["Portion from plate/bowl dimensions (open challenge)", "Typical-serving priors, plate/bowl area ratio, reference objects, user grams, with bands", "Volume from one 2D photo remains unsolved; the bands say so"],
  ], [2700, 3626, 2700]),
  H2("4.3 Main features"),
  ...TABLE("Features and the use cases they serve", ["Use case", "Implementation"], [
    ["Log a meal from a photo or a description", "Capture page; 10-stage analysis; description parser (local SLM, rule-based fallback)"],
    ["Check and correct", "Editable review: confirm, rename (top-3 or search), portion, merge, remove; every edit logged in corrections"],
    ["Add a missed food", "Drag a box on the photo, tap a region the app found, or search; classified per region; remembered next time"],
    ["Understand the meal", "Key takeaways, glucose impact, GL (published or borrowed GI), meal composition, cited meal advisory"],
    ["Try before eating", "Portion simulator and activity forecast (desk vs walk), with glucose in mmol/L or mg/dL"],
    ["Ask questions", "Meal Advisor with evidence levels, one-tap fixes, 30-day history"],
    ["See habits", "Dashboard, history, nutrition trends"],
    ["Govern learning", "Admin area: review queue, contributors, dataset versions, model gate, settings and versioned prompts, audit log"],
  ], [3000, 6026]),
  H2("4.4 Implementation and optimisation choices"),
  ...BUL([
    "**One process, models loaded once** at start-up; ONNX Runtime on CPU (~12 ms per classification), no GPU required.",
    "**Deferred explanation**: results appear first; the language model's explanation is requested afterwards, so it never delays the review.",
    "**Fail-safe language model**: JSON-schema output, timeouts, a 5-minute back-off after an error, and the rule engine as fallback.",
    "**Caching**: nutrition computations and SLM replies cached (Redis optional, in-memory otherwise); custom foods never cached.",
    "**Images**: EXIF orientation fixed, originals kept for classification, a ≤1024 px copy for display.",
    "**Security**: bcrypt passwords, JWT tokens, owner-only photo access, non-root container, nginx rate limits; admin role granted only by a server command.",
    "**Operations**: Alembic migrations on every start; the database and photos in named volumes; each Compose project names its own images so a test copy cannot replace the live one.",
  ]),
];

const experiments = [
  H1("5. Experiments"),
  ...TABLE("Experiments and their set-up", ["#", "Experiment", "Data and method", "Metrics"], [
    ["E1", "Classifier quality", "EXP-002 evaluation on the held-out split (developer workstation)", "Top-1, top-3, macro-F1"],
    ["E2", "Runtime equivalence", "601 images; PyTorch + torchvision vs ONNX Runtime + app preprocessing", "Max abs diff, top-k agreement, latency"],
    ["E3", "Multi-food plates", "100 synthetic plates from Food-101 test images, 263 items; IoU ≥ 0.5", "Detection P/R, AP50; classification of matched items; latency"],
    ["E4", "Grounded advisor", "38 labelled questions in 16 categories, synthetic account; expected values from the server's own records", "Pass rate, unsupported-claim rate, latency"],
    ["E5", "Text matching baselines", "20 meal descriptions, 15 unknown food names (10 in the table, 5 absent)", "Precision/recall/F1; correct, wrong, no match"],
    ["E6", "Local language model", "Same sets as E5, 6 meal explanations, 8 advisor drafts; qwen2.5:1.5b on the deployment server", "As E5; grounded explanations; validator pass rate; latency; tokens/s"],
    ["E7", "End-to-end acceptance", "Fresh deployment: sign-up → capture → top-3 override → portion → save → history; restart; offline", "Pass/fail per check"],
    ["E8", "Glucose model scenarios", "Chicken rice + teh tarik, type 2 profile, 78 kg: desk, 15-min walk, two-thirds rice", "Peak, area, GL"],
  ], [500, 2000, 4126, 2400]),
  ...TABLE("Validation measures named in the proposal, and the results", ["Proposal measure", "Result", "Status"], [
    ["Segmentation: mean average precision", "AP50 (class-agnostic) 0.59 on 100 multi-food plates; precision 74.7%, recall 68.4%", "Measured (E3)"],
    ["Classification: confusion matrix, accuracy, precision, recall, F1", "Top-1 70.6%, top-3 85.7%, macro-F1 66.7%; confusion on plates (Figure 4)", "Reported (E1), measured (E3)"],
    ["Portion / nutrition: MAE or % error against known reference portions", "Not measured: no weighed reference portions yet; estimates carry ±15–50% bands", "Gap, planned with the trial"],
    ["Recommendations: factuality, relevance, safety", "38/38 labelled questions passed, 0% unsupported claims, safety 6/6, injection 3/3", "Measured (E4)"],
  ], [2900, 4126, 2000]),
  P("All experiments run on CPU (a 4-vCPU environment for E2–E5, E7 and E8; the deployment server for E6). E1 is reported, not reproduced, because the training datasets are not part of the package; ml/evaluation/evaluate.py re-measures it on any labelled folder."),
];

const perf = [
  H1("6. System performance"),
  H2("6.1 Recognition"),
  ...FIG("01_model_metrics.png", 5.6, "Classifier quality (E1)."),
  P("Roughly 7 in 10 photos get the right top-1 class and about 86% have it in the top three, which is why the review always offers three candidates. The ONNX deployment reproduces the trained model exactly in ranking (E2: 100% top-1 and top-3 agreement, logits within 1.35 × 10⁻⁴)."),
  ...FIG("02_multifood_outcomes.png", 6.0, "What happened to each true item on multi-food plates (E3)."),
  P("On mixed plates, detection found 180 of 263 items (recall 68.4%) with 61 false regions (precision 74.7%; AP50 0.59). Classification of matched items was 56.1% top-1 and 75.0% top-3. Pizza was recognised well (86%), but steak only 11% of the time: 29% went to close variants (sirloin, filet mignon) that carry similar nutrition, and 48% were left unidentified for the user to name rather than guessed."),
  H2("6.2 Speed"),
  ...FIG("03_latency.png", 5.8, "Response times on CPU."),
  H2("6.3 Nutrition and glycaemic coverage"),
  ...FIG("04_coverage.png", 5.8, "Mapping coverage: classes to nutrition records, foods to GI."),
  ...FIG("05_gi_borrowing.png", 5.4, "Where borrowed GI values come from (78 foods)."),
  P("Before v0.13.8 only 57 of 286 foods had a GI, so most hawker meals showed \"glycaemic load not estimated\". Rule-based borrowing raises that to 135 foods (47%); the remaining 151 are mostly meat, vegetables, kueh and fruit, where no single staple dominates."),
  H2("6.4 Language and text matching"),
  ...FIG("06_text_matching.png", 5.6, "Matching food names that the table does not list verbatim (E5" + (SLM ? ", E6)." : ").")),
  P("Before any language model is asked, the rules do well on whole descriptions: the splitter recovered the exact food set for **19 of 20** descriptions (F1 0.987; it missed \"soft boiled eggs\"). On unknown names, however, the fuzzy lookup was right for only 7 of 15 and **confidently wrong for 4** (sugarcane juice → orange juice, curry chicken → chicken breast, mung bean soup → consommé, fishball soup → fried bee hoon). Because the language model is only consulted when the lookup returns nothing, these wrong matches currently bypass it; Section 7 proposes the fix."),
  ...(slmRows ? TABLE(`Local language model on the deployment server (E6): ${SLM.model}, ${SLM.tokens_per_s ? SLM.tokens_per_s.mean + " tokens/s" : ""}`, ["Task", "Language model", "Rule baseline", "p50 / p95 ms"], slmRows, [2200, 3626, 1900, 1300])
    : [P("**E6 results pending.** The benchmark (app/tools/slm_eval.py) runs the four language-model tasks above on fixed inputs with known answers, read-only, on the deployment server. This table will be completed from that run.", { shading: { fill: "FDF2E7", type: ShadingType.CLEAR, color: "auto" } })]),
  ...(SLM ? [P("The result is clear and not flattering to the language model. On every task with a rule baseline, the **rules were better**: description parsing F1 0.987 against 0.732 (19 against 9 exact sets), and on unknown names the model was right 4 times in 15 and **wrong 6 times**, against the fuzzy lookup's 7 right and 4 wrong. Rewording advisor drafts is where it helps: **7 of 8** rewordings passed the validator and could be shown; the eighth fell back to the rule answer. Its meal explanations were the weakest: only **1 of 6** used only numbers from the facts."),
    P("That last result exposed a gap. Advisor replies passed through the validator before they were shown, but meal explanations were displayed **without that check**, so an explanation could state a number the system never computed. **Fixed in v0.13.13**: explanations now pass the same validator, and one that fails is not shown (the rule-based results remain; the check is stored for audit). With this model most explanations will now be withheld, which is the right trade-off for a health app. The general lesson is the design's premise: a 1.5-billion-parameter model is useful for wording, not for facts, and every model output needs a deterministic check.")] : []),
  ...TABLE("Language model in real use on the deployment server (inference log, all calls since it was enabled)", ["Task", "Calls", "Completed", "Mean ms", "p50 / p95 ms"], [
    ["Meal explanation", "24", "100%", "1,515", "1,465 / 3,299"],
    ["Meal Advisor reply", "3", "100%", "4,735", "5,304 / 5,314"],
  ], [2600, 1200, 1500, 1500, 2226]),
  P("Every call returned a valid answer within its timeout. That is a small sample (27 calls) and measures availability and speed, not quality. The rules answer in about 12 ms, so the model adds 1.5–5 seconds; this is why explanations are deferred (the result appears first) and the rules stay the fallback."),
  H2("6.5 Grounded advisor"),
  P("All 38 labelled questions passed (E4), across meal retrieval, carbohydrate arithmetic, explainability, food lookup, week summaries, safety (6/6), prompt injection (3/3), conversation (4/4) and user isolation, with **no unsupported claims** and a 12 ms median reply (18 ms p95) from the rule engine."),
  H2("6.6 Glucose model scenarios"),
  ...FIG("07_glucose_curves.png", 6.0, "Estimated meal glucose for one meal under three choices (E8)."),
  P("For chicken rice with teh tarik (95.6 g carbohydrate, GL 66.3), the model estimates that a 15-minute brisk walk 15 minutes after eating lowers the peak by only 2.3% and the area by 2.7% (it uses about 55 kcal, 7% of the meal's energy), while eating two-thirds of the rice lowers GL to 48.4 and the peak by about a quarter. The model therefore points users to the portion before the walk, consistent with GL arithmetic. These are population-level estimates, not measurements."),
  H2("6.7 Quality"),
  ...FIG("08_tests_growth.png", 5.6, "Automated tests over the project."),
  P("All 65 automated tests pass against a real PostgreSQL database; browser flows pass on phone and desktop sizes with no JavaScript errors; the acceptance run passed 9 of 9 checks, also with the internet disconnected, and data survived a restart."),
];

const findings = [
  H1("7. Findings and discussion"),
  H2("7.1 What worked"),
  ...BUL([
    "**Human in the loop beats a single answer.** With top-3 at 85.7% and one-tap correction, a wrong top-1 costs a tap, not a wrong log.",
    "**Grounding by construction.** Letting rules produce facts and the language model only produce wording gave zero unsupported claims in the advisor, and a safe fallback when the model is slow or offline. Where the check was missing (meal explanations), the model added numbers of its own in 5 of 6 cases; the benchmark found it, and the check now covers both.",
    "**Honest uncertainty is a feature.** Leaving an item unidentified (48% of missed steaks) is preferable to a confident wrong dish for someone counting carbohydrate.",
    "**Cheap to run.** Every model runs on one CPU server; the classifier takes ~12 ms and a full multi-food analysis ~0.26 s.",
  ]),
  H2("7.2 Limitations"),
  ...BUL([
    "**The small language model adds little**: rules beat it on parsing and matching, and 5 of 6 meal explanations contained a number of their own. Since v0.13.13 those are withheld, so most users will see the rule-based results without a model explanation. A larger or fine-tuned local model would need to be re-measured with the same benchmark.",
    "**Visually similar dishes** (steak vs sirloin, noodle soups, rice plates) remain the main confusion; scores are uncalibrated.",
    "**Portions** come from priors or area, not volume (±35–50%); entering grams is the accurate path. The proposal's portion error measure (MAE against weighed portions) has not been run.",
    "**Nutrition values are unverified** transcriptions (USDA- and HPB-style values) or recipe approximations (199 records); a verified import (HPB SG FoodID, USDA FDC) is required before clinical use.",
    "**Glucose estimates** use population physiology; they are not predictions for an individual and must never inform insulin dosing.",
    "**Accuracy evidence for E1 is reported**, not reproduced in this package; the multi-food set is synthetic; no real-user trial has been run.",
    "**Fuzzy lookup errors** (4 of 15 confident wrong matches) bypass the language model today.",
    "**Licence**: YOLO11n-seg is AGPL-3.0; serving publicly needs compatible terms or replacing the detector.",
  ]),
  H2("7.3 Recommendations"),
  ...NUM([
    "Ask the language model (or show the user a choice) when the fuzzy lookup is only a fuzzy match, not only when it finds nothing.",
    "Retrain with governed user data (consented, screened, frozen) through the model gate, prioritising confused groups.",
    "Replace the nutrition table with a verified Singapore source and record GI provenance per food.",
    "Calibrate scores (temperature scaling) so the review can show reliable confidence.",
  ], "num2"),
  H2("7.4 Trial plan"),
  P("The trial should also weigh a set of reference portions, to measure portion error as the proposal intended. A two-phase evaluation is proposed: five to eight moderated sessions (task success, time, one-question ease rating) followed by a two-week field trial with 15–30 people (System Usability Scale, UMUX-Lite, trust and comprehension items, willingness to pay for Plus). The app already logs the needed behaviour: accepted vs corrected foods, top-3 hits, drawn boxes, memory matches, portion edits and language-model use. Consent under Singapore's PDPA, training consent off by default and a clear not-medical-advice statement are prerequisites."),
  H1("8. Conclusion", false),
  P("MealSenseAI shows that a small, local, explainable system can make an unlabelled hawker plate legible: recognition good enough when paired with one-tap correction, glycaemic load for most local staples, a glucose estimate that favours sensible portions, and an advisor that cannot make up numbers. The next step is evidence from real users and verified nutrition data."),
];

const refs = [
  H1("References"),
  ...NUM([
    "Atkinson FS, et al. International tables of glycemic index and glycemic load values 2021: a systematic review. Am J Clin Nutr. 2021;114(5):1625–1632.",
    "Ainsworth BE, et al. 2011 Compendium of Physical Activities. Med Sci Sports Exerc. 2011;43(8):1575–1581.",
    "Png ME, et al. Current and future economic burden of diabetes among working-age adults in Asia: conservative estimates for Singapore from 2010–2050. BMC Public Health. 2016;16:153.",
    "Tan M, Le QV. EfficientNet: Rethinking model scaling for convolutional neural networks. ICML 2019.",
    "Bossard L, Guillaumin M, Van Gool L. Food-101: mining discriminative components with random forests. ECCV 2014.",
    "World Health Organization. Diabetes fact sheet (2022 figures), as cited in the project proposal.",
    "Ministry of Health, Singapore. National Population Health Survey (2023 figures), as cited in the project proposal.",
    "Health Promotion Board, Singapore. Healthy 365 meal log tool FAQ; My Healthy Plate.",
    "Reynolds AN, et al. Advice to walk after meals is more effective for lowering postprandial glycaemia in type 2 diabetes. Diabetologia. 2016;59(12):2572–2578.",
    "WHO. Guideline: Sugars intake for adults and children (2015); Sodium intake for adults and children (2012).",
  ], "ref"),
  H2("Appendix: evidence files"),
  ...BUL([
    "ml/models/exp002/model_card.json, evidence/onnx_parity.json, evidence/nutrition_coverage.json, evidence/train_finetune.py",
    "test-results/multifood_metrics.json, advisor_eval.json, acceptance_*.json; docs/TEST_REPORT.md",
    "backend/app/services (vision, portion, nutrition, insights, forecast, glucose_scale, advisor, memory, screening, gate)",
    "backend/app/tools/slm_eval.py (E6); demo/SOURCES.md; CHANGELOG.md",
  ]),
];

const num = (ref, fmt) => ({ reference: ref, levels: [{ level: 0, format: fmt, text: fmt === LevelFormat.BULLET ? "•" : "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] });
const doc = new Document({
  creator: "Dizon Joselito Villanueva", title: "MealSenseAI Final Report", description: "Final report, Individual project",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 34, bold: true, color: TEAL, font: "Calibri" }, paragraph: { spacing: { before: 120, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, color: "172B2A", font: "Calibri" }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: "Calibri" }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
      { id: "Caption", name: "Caption", basedOn: "Normal", run: { size: 18, color: INK2 } },
    ],
  },
  numbering: { config: [num("bul", LevelFormat.BULLET), num("num", LevelFormat.DECIMAL), num("num2", LevelFormat.DECIMAL), num("ref", LevelFormat.DECIMAL)] },
  sections: [
    { properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children: cover },
    { properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 }, pageNumbers: { start: 1 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run("MealSenseAI · Final Report", { size: 16, color: INK2 })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: INK2 })] })] }) },
      children: [...toc, ...summary, ...business, ...tools, ...design, ...dev, ...experiments, ...perf, ...findings, ...refs] },
  ],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(path.join(HERE, "MealSenseAI-Final-Report.docx"), b); console.log("written"); });
