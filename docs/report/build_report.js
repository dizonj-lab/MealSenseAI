// MealSenseAI final report (Word). Every figure is from the repository's evidence files or a cited source.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, ImageRun, PageBreak, TableOfContents, Footer, Header, PageNumber, LevelFormat, TabStopType,
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
  s.split(/(\[\[[^\]]+\]\]|\*\*[^*]+\*\*|\*[^*]+\*)/).forEach((part) => {
    if (!part) return;
    if (part.startsWith("[[")) out.push(run(part.slice(2, -2), { highlight: "yellow" }));
    else if (part.startsWith("**")) out.push(run(part.slice(2, -2), { bold: true }));
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
             ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false)) }))] }),
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
  new Paragraph({ spacing: { after: 80 }, children: [run("Final draft · 29 October 2026 · system version v0.13.18 · follows the proposal of 30 September 2026", { size: 22, color: INK2 })] }),
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
  P("MealSenseAI is a web application that estimates the foods, portions and nutrition of a meal from one photo, and from these the meal's likely effect on blood glucose, its glycaemic load (GL) and a suggested next step. Each estimate is labelled with its type and range and can be corrected by the user. The application can be used by anyone; the user's profile sets the health condition, if any, and the goals that the guidance follows. As in my proposal, the first target group is people with Type 1 and Type 2 diabetes in Singapore."),
  ...TABLE("Headline results (all measured unless marked)", ["Area", "Result", "Evidence"], [
    ["Food recognition", "EfficientNet-B0, 320 classes, 45,800 test images: **70.6% top-1, 85.7% top-3**, macro-F1 66.7%; calibration error 2.35%", "overall_metrics.json, derived_summary.json"],
    ["Runtime fidelity", "ONNX export gives the **same top-3 on 601 of 601 images**; 11.8 ms per photo on CPU", "onnx_parity.json"],
    ["Multi-food plates", "Detection **precision 74.7%, recall 68.4%**; 262 ms median per plate", "multifood_metrics.json"],
    ["Grounded advisor", "**38/38** test questions passed, **0%** unsupported claims, 12 ms median (rule engine)", "advisor_eval.json"],
    ["Coverage", "247 of 320 classes map exactly to a nutrition record; GL now estimable for **135 of 286** foods (57 published GI + 78 borrowed)", "nutrition_coverage.json, v0.13.8"],
    ["Quality", "**65** automated tests passing; 9/9 acceptance checks, also offline; data kept across restart", "TEST_REPORT.md"],
    ["Language model", SLM ? `qwen2.5:1.5b on Buddy: ${SLM.rewrite.passed_validator} rewordings passed the validator; ${SLM.explain.grounded} explanations grounded` : "Benchmark ready (app/tools/slm_eval.py); **results pending** the run on the deployment server", "slm_eval.json"],
  ], [1900, 5026, 2100]),
  P("The main limitations are confusion between similar dishes (steak was correctly identified in 11% of matched cases), portion estimates of ±35–50% from a photo, nutrition values that have not been verified against an official source, and the absence of a trial with real users. These are discussed in Section 7."),
];

const business = [
  H1("1. Business case and market research"),
  H2("1.1 The problem"),
  P("Packaged food in Singapore carries nutrition labels; hawker food does not. In a typical hawker meal the carbohydrate is spread across rice, sauce and a sweetened drink, portion sizes differ between stalls, and mixed dishes are difficult to break down. People who need to manage carbohydrate therefore estimate by eye, and manual food logging is commonly abandoned because it takes too long."),
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
  P("The Nutri-Grade study indicates that making nutrition visible changes purchasing. Labelling, however, covers packaged drinks and foods only; meals bought from hawker stalls remain unlabelled."),
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
  P("The existing products support calorie counting and food search. None of them estimates the effect of a specific local meal on blood glucose together with the uncertainty of that estimate, which is the gap MealSenseAI addresses. In the proposal I positioned the product on features at a competitive price rather than on the lowest price."),
  H2("1.4 Value proposition and users"),
  ...BUL([
    "**From photo to nutrition**: foods, portions and nutrients, with Singapore dishes among the 320 classes and a local nutrition table.",
    "**Glucose context**: likely glucose impact, glycaemic load, a portion simulator and an activity what-if, available before eating.",
    "**Labelled outputs**: each value is marked as a model prediction, estimate, guidance or user input, with its range and source; nothing is saved until the user confirms.",
    "**Users**: anyone who wants to understand their food, with or without a health condition. The profile records a condition (none, prediabetes, Type 1, Type 2, gestational, or not disclosed) and goals (general wellness, carbohydrate or calorie awareness, weight management, balanced nutrition, diabetes-friendly, heart health); personalised notes follow them, for example salt and saturated fat against WHO limits for heart health, or energy density for weight.",
    "**First focus (MVP, as proposed)**: people with Type 1 and Type 2 diabetes in Singapore, where carbohydrate and portion awareness matter most; **also**: families and carers; **later**: organisations that support members. For Type 1 diabetes the app supports awareness only and is never a basis for insulin dosing.",
    "**Market focus**: Singapore first, scaling to Southeast Asia; aligned with UN SDG 3 (good health and well-being).",
  ]),
  H2("1.5 Pricing and market scenario"),
  P("In the proposal I set a freemium model with a subscription of S$3.99 a month in Singapore and S$2.99 a month in other ASEAN markets. In the built application I kept meal logging and nutrition free; glucose impact, the Meal Advisor and the simulators form the subscription."),
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
  P("The scenario is the one from my proposal and is not a forecast. It counts adults with diabetes only and so excludes users without a condition. The 50% operating-cost assumption has not been validated; the build shows only that the compute cost is low, since all models run on one CPU server without a paid AI service. I will measure willingness to pay in the trial (Section 7.3)."),
];

const tools = [
  H1("2. Tools and techniques"),
  ...TABLE("Tools and techniques used, and why", ["Area", "Tool / technique", "Why"], [
    ["Food recognition", "EfficientNet-B0 (torchvision), two-stage transfer learning in PyTorch 2.11 on an RTX 5060 Ti; ONNX Runtime for inference", "Accurate for its size; trains in about 40 minutes; runs in ~12 ms on CPU"],
    ["Data preparation", "Class-name normalisation, SHA-256 duplicate audit, exclusion of conflicting labels, stratified split", "No duplicate image in more than one split"],
    ["Food regions", "YOLO11n-seg (COCO), mask and box regions", "Finds several foods and containers on one plate"],
    ["Portions", "Typical-serving priors, mask-area ratio to plate or bowl, user grams; uncertainty bands", "A photo gives no weight; the bands state the error"],
    ["Nutrition", "286-record table with provenance; exact / proxy / none mapping; difflib fuzzy lookup", "Each value traceable to a record"],
    ["Glycaemic load", "Published GI (Atkinson 2021) plus rule-based GI borrowing from the staple", "Covers local dishes without inventing values"],
    ["Glucose estimate", "One-compartment mass-balance ODE, OGTT anchor, per-user median-ratio calibration", "Interpretable; errs on the high side"],
    ["Language model", "Ollama with Qwen 2.5 1.5B, JSON-schema output, temperature control", "Runs locally on CPU; used for wording only"],
    ["Grounding", "Rule engine draft → SLM rewrite → validator (numbers ±2%, food names, unsafe phrases)", "No unsupported number reaches the user (advisor replies and, from v0.13.13, meal explanations)"],
    ["Personal memory", "Class-probability fingerprints, cosine similarity ≥ 0.70 with a 0.05 margin", "Recognises a user's own foods without retraining"],
    ["Data governance", "Per-sample consent, 11 screening checks, perceptual hashes, frozen dataset versions, model gate with shadow mode", "Controlled use of user photos for training"],
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
  P("The system runs as four containers on one server (Figure 1). The browser connects only to nginx, which serves the web application and forwards /api requests to the FastAPI backend. The backend loads the models, rules and advisor in one process and stores data in PostgreSQL; photos and model packages are kept in a volume. An optional local language model runs in a separate container. No cloud AI service is used."),
  ...FIG("09_architecture.png", 6.2, "Deployment architecture."),
  H2("3.2 The ten-stage pipeline"),
  P("The pipeline uses the ten stages I defined in the proposal: meal capture, image pre-processing, food instance detection, food classification, portion estimation, nutrition mapping, meal aggregation, AI contextualisation with the user's context, recommendations and application output (Figure 2). The result of each stage is shown to the user, and each output is tagged as a model prediction, an estimate, guidance or user input."),
  ...FIG("10_pipeline.png", 6.2, "Inference pipeline; colour shows the kind of output."),
  H2("3.3 Data"),
  P("I used the two datasets named in the proposal: FoodSG-233 (209,861 images, 233 Singapore food classes in 13 food groups) and Food-101 (101,000 images, 101 classes), 310,861 images in total. I normalised the 334 original class names to 324 and then merged them into a taxonomy of 320 classes. A SHA-256 audit of every file found 2,040 groups of identical images: 2,019 groups carried conflicting labels and 728 groups crossed a split boundary. I excluded 4,193 images (4,172 with conflicting labels and 21 exact duplicates), which left 306,668 images; after the exclusion no duplicate image remained in more than one split."),
  P("For Food-101 I kept the official test set and took 10% of the official training set for validation; FoodSG-233 was split 80/10/10, stratified by class, with seed 42. This differs from the 70/15/15 split stated in the proposal and in ml/training/config.yaml: keeping Food-101's official test set makes the results comparable with published work. The final sets were 232,713 training, 28,155 validation and 45,800 test images. Augmentation was applied to the training set only. Each class is mapped to a nutrition record or marked for the user to choose (Section 3.6)."),
  H2("3.4 Recognition model"),
  P("I trained the classifier in two stages on my home server (\"Buddy\"; NVIDIA RTX 5060 Ti, 16 GB, PyTorch 2.11 with CUDA 12.8). EXP-001 trained only a new 320-class head on a frozen ImageNet EfficientNet-B0 (learning rate 1e-4, 5 epochs) and reached a validation macro-F1 of 57.7%. EXP-002 started from that checkpoint and also trained the last three feature blocks, raising validation macro-F1 to 66.3% (Figure 3). Each stage took about 20 minutes. Validation scores were still rising at epoch 5, so more epochs may help."),
  ...FIG("11_training_curves.png", 6.0, "Training curves for the two stages (EXP-001 epochs 1–5, EXP-002 epochs 6–10)."),
  ...TABLE("EXP-002 training configuration (training evidence: config.json, environment.json)", ["Setting", "Value"], [
    ["Backbone", "EfficientNet-B0, initialised from the EXP-001 checkpoint (ImageNet weights, 320-class head)"],
    ["Classes", "320 (Food-101 and FoodSG, harmonised)"],
    ["Strategy", "Partial fine-tuning: last 3 feature blocks and the classifier head trainable"],
    ["Optimiser", "AdamW; learning rate 1e-5 (backbone), 5e-5 (head); weight decay 1e-4"],
    ["Schedule", "5 epochs, batch 32, seed 42, image 224 px; 20.4 min on the GPU (about 975 training images/s)"],
    ["Data", "232,713 training and 28,155 validation images; test set of 45,800 held out"],
    ["Augmentation", "RandomResizedCrop (0.8–1.0), horizontal flip 0.5, rotation 20°, colour jitter (0.2, 0.2, 0.2, hue 0.05)"],
    ["Deployment", "ONNX (opset 17) on ONNX Runtime CPU; preprocessing bit-identical to training (max abs diff 0.0)"],
  ], [2200, 6826]),
  P("I configured the model for a CPU server: a compact backbone, partial fine-tuning to limit over-fitting, lower learning rates for the pretrained layers than for the head, and export to ONNX. I did not apply a separate calibration step; on the test set the softmax confidence is already close to the observed accuracy (Section 6.1). Items scoring below 0.20 are not added automatically, and items between 0.20 and 0.50 are marked for the user to check."),
  H2("3.5 Several foods on a plate"),
  P("YOLO11n-seg proposes regions for foods and containers. Each region is cropped from the original photo and classified separately. Regions with low scores are listed as \"Unidentified food\" with the model's top three classes, and small or nested regions are kept as hidden suggestions. Since v0.13.2 the user can also draw a box around a food that was missed; the box is classified in the same way."),
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
  P("A rule engine drafts each answer from the user's meals, profile and the food table, and each statement is tagged with its source. When the local language model is available it rewrites the wording of the draft. A validator then checks that every number in the rewrite is within ±2% of a number in the facts, that no new food names were added, and that there are no unsafe statements such as dosing or diagnosis. If any check fails, the rule-based answer is shown. Questions about medication or urgent symptoms are answered by rules only."),
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
  P("I developed the system iteratively, in versioned releases from v0.1 to v0.13.18 (about 55 commits between 23 and 29 October 2026, after the proposal of 30 September). I tested each release, recorded it in the changelog and test report, and deployed it to my home server (\"Buddy\"). The code base has about 6,800 lines of Python in the backend, 3,700 lines of TypeScript in the frontend and 2,000 lines of machine-learning tooling, with 10 test modules."),
  H2("4.2 From proposal to build"),
  ...TABLE("Proposed design (30 September 2026) and what was built", ["Proposed", "Built", "Why"], [
    ["Web UI with a webcam; smartphone later", "Phone-first responsive web app (camera or upload) plus desktop", "Capture happens at the table, so the phone came first"],
    ["Reverse proxy, web app, application API", "nginx, React app, FastAPI", "As proposed"],
    ["Redis job queue and a separate ML worker", "One backend process; Redis optional as a cache", "A full analysis takes ~0.26 s on CPU, so a queue added complexity without benefit"],
    ["Vision inference service (YOLO-Seg, CNN)", "YOLO11n-seg + EfficientNet-B0 on ONNX Runtime, inside the backend", "Loaded once; ~12 ms per classification"],
    ["Local object storage (MinIO)", "A Docker volume for photos and model packages", "One server; no S3 API needed yet"],
    ["Model registry (MLflow)", "Model updates location, model gate with shadow mode, admin promotion and rollback", "Gate decisions are part of the app and audited"],
    ["ML development environment (Jupyter / PyTorch)", "PyTorch training and evaluation scripts on Buddy's GPU, with logged configuration, environment and history", "Each run leaves its evidence files"],
    ["Split 70/15/15", "Food-101 official test + 10% of train for validation; FoodSG-233 80/10/10 (232,713 / 28,155 / 45,800)", "Keeps Food-101's standard test set"],
    ["Nutrition reference store", "286-record table with provenance, plus users' custom foods", "As proposed"],
    ["Local SLM (Ollama); optional frontier LLM", "Ollama with Qwen 2.5 1.5B; no external LLM", "Data stays on the server; no paid AI service"],
    ["Portion from plate/bowl dimensions (open challenge)", "Typical-serving priors, plate/bowl area ratio, reference objects, user grams, with bands", "Volume from a single 2D photo is not solved; ranges are shown"],
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
  ...TABLE("Model configuration in the admin area (defaults; changes apply without a code change and are audited)", ["Setting", "Value", "Basis"], [
    ["Whole-photo suggestion threshold", "0.20", "Below it, top-1 accuracy on the test set is 17.4%, so the user picks from the top three"],
    ["Identify threshold (plate regions)", "0.45", "Weaker regions are listed as unidentified instead of guessed"],
    ["Auto-accept score", "0.50", "At or above it, top-1 accuracy on the test set is 85.7%"],
    ["Personal memory match", "cosine ≥ 0.70, margin 0.05", "The classifier's 320-value output serves as the embedding; 94 of 120 held-out matches, all correct"],
    ["Local language model", "Qwen 2.5 1.5B on Ollama", "Runs on CPU at about 56 tokens/s; used for rewording only (Section 6.4)"],
    ["Temperature", "0.1", "Consistent wording between calls"],
    ["Time limits", "15 s per call; 60 s for the advisor", "After the limit, the rule engine answers"],
    ["Prompts", "versioned", "Each change is saved as a new version and can be activated or rolled back"],
  ], [2600, 2200, 4226]),
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
    ["E1", "Classifier quality", "EXP-002 on the held-out test set of 45,800 images (Food-101 official test + FoodSG-233 test), run on Buddy's GPU", "Top-1, top-3, macro precision/recall/F1, per class and per dataset; confusion matrix; calibration"],
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
    ["Classification: confusion matrix, accuracy, precision, recall, F1", "Top-1 70.6%, top-3 85.7%; macro precision 66.9%, recall 67.9%, F1 66.7% on 45,800 test images; 320 × 320 confusion matrix and per-class F1", "Measured (E1, E3)"],
    ["Portion / nutrition: MAE or % error against known reference portions", "Not measured: no weighed reference portions yet; estimates carry ±15–50% bands", "Gap, planned with the trial"],
    ["Recommendations: factuality, relevance, safety", "38/38 labelled questions passed, 0% unsupported claims, safety 6/6, injection 3/3", "Measured (E4)"],
  ], [2900, 4126, 2000]),
  P("I ran E1 on Buddy's GPU as part of training, E2–E5, E7 and E8 on a 4-vCPU environment, and E6 on Buddy's CPU. The E1 evidence (configuration, training history, predictions, classification report, confusion matrix and calibration) is in ml/models/exp002/evidence/training; the image datasets themselves are not redistributed."),
];

const perf = [
  H1("6. System performance"),
  H2("6.1 Recognition"),
  ...FIG("01_model_metrics.png", 5.8, "Classifier quality on the held-out test set (E1)."),
  P("On the 45,800 test images the classifier placed the correct class first for 70.6% and within the top three for 85.7%, with macro precision 66.9%, recall 67.9% and F1 66.7%. Results were similar for the two sources: Food-101 72.1% top-1 and 86.9% top-3, FoodSG-233 68.8% and 84.2%. Because the correct class is in the top three far more often than first, the review screen always shows three candidates. The ONNX model used by the application ranked classes identically to the PyTorch model on all 601 images checked (E2), with logits differing by at most 1.35 × 10⁻⁴."),
  ...FIG("13_per_class_f1.png", 5.8, "Distribution of F1 over the 320 classes (E1)."),
  ...TABLE("Most frequent confusions on the test set (true class → predicted class)", ["True class", "Predicted as", "Images"], [
    ["dumpling", "xiao long bao", "70"], ["steak", "filet mignon", "49"], ["donuts", "bagel & croissant", "47"], ["sweets", "chocolate", "31"],
    ["paella", "paella seafood", "28"], ["ice cream", "ice cream chocolate", "28"], ["filet mignon", "steak", "27"], ["ramen", "miso ramen, with fishcake", "26"],
  ], [3300, 3726, 2000]),
  P("Performance varies by class. The median class F1 was 68.5%; 80 classes reached 80% or more and 45 were below 50%. The weakest were mostly local noodle and rice dishes that look alike, such as fried mee siam (0%), soto bee hoon (15%), bee hoon (23%), mee kuah (24%) and yam rice (25%). The most frequent confusions are between closely related dishes (dumpling and xiao long bao, steak and filet mignon), which usually have similar nutrition."),
  ...FIG("12_calibration.png", 3.8, "Top-1 confidence against observed accuracy, 10 bins (E1)."),
  P("The model's confidence was close to its observed accuracy, with an expected calibration error of 2.35% over ten bins; where it deviates, it is slightly under-confident. This supports the thresholds used in the application: the 4.6% of test images scored below 0.20 had a top-1 accuracy of 17.4%, the 25.8% scored between 0.20 and 0.50 had 39.4%, and the 69.6% scored at 0.50 or above had 85.7%."),
  ...FIG("02_multifood_outcomes.png", 6.0, "What happened to each true item on multi-food plates (E3)."),
  P("On the 100 multi-food plates, detection found 180 of 263 items (recall 68.4%) and produced 61 false regions (precision 74.7%; AP50 0.59). Of the matched items, 56.1% were classified correctly first and 75.0% within the top three. Results varied by food: pizza was correct in 86% of cases, steak in 11%; a further 29% of steaks were labelled as close variants such as sirloin, which have similar nutrition, and 48% were left as unidentified."),
  H2("6.2 Speed"),
  ...FIG("03_latency.png", 5.8, "Response times on CPU."),
  H2("6.3 Nutrition and glycaemic coverage"),
  ...FIG("04_coverage.png", 5.8, "Mapping coverage: classes to nutrition records, foods to GI."),
  ...FIG("05_gi_borrowing.png", 5.4, "Where borrowed GI values come from (78 foods)."),
  P("Before v0.13.8, 57 of the 286 foods had a published GI, so GL could not be calculated for most hawker meals. With rule-based borrowing, 135 foods (47%) have a GI value. Most of the remaining 151 foods are meat, vegetables, kueh and fruit, for which no single staple applies."),
  H2("6.4 Language and text matching"),
  ...FIG("06_text_matching.png", 5.6, "Matching food names that the table does not list verbatim (E5" + (SLM ? ", E6)." : ").")),
  P("The rule-based parser returned the exact set of foods for 19 of 20 meal descriptions (F1 0.987); it missed \"soft boiled eggs\". The fuzzy lookup matched 7 of 15 unknown food names correctly and 4 incorrectly (sugarcane juice to orange juice, curry chicken to chicken breast, mung bean soup to consommé, fishball soup to fried bee hoon). Because the language model is consulted only when the lookup finds no match, these incorrect matches are not checked by it (Section 7.3)."),
  ...(slmRows ? TABLE(`Local language model on the deployment server (E6): ${SLM.model}, ${SLM.tokens_per_s ? SLM.tokens_per_s.mean + " tokens/s" : ""}`, ["Task", "Language model", "Rule baseline", "p50 / p95 ms"], slmRows, [2200, 3626, 1900, 1300])
    : [P("**E6 results pending.** The benchmark (app/tools/slm_eval.py) runs the four language-model tasks above on fixed inputs with known answers, read-only, on the deployment server. This table will be completed from that run.", { shading: { fill: "FDF2E7", type: ShadingType.CLEAR, color: "auto" } })]),
  ...(SLM ? [P("On every task that had a rule baseline, the rules performed better than the language model: description parsing F1 0.987 against 0.732 (19 against 9 exact sets), and unknown-name matching 7 correct and 4 wrong against 4 correct and 6 wrong. For rewording advisor drafts, 7 of 8 outputs passed the validator. Only 1 of 6 meal explanations used numbers that were all present in the facts."),
    P("Meal explanations were displayed without validation, so an explanation could include a number the system had not calculated. From v0.13.13 they pass the same validator as advisor replies, and an explanation that fails is not shown; the check result is stored. With this model most explanations will be withheld. From these results I conclude that a 1.5-billion-parameter model is suitable for rewording but not as a source of facts, and that its output needs to be checked.")] : []),
  ...TABLE("Language model in real use on the deployment server (inference log, all calls since it was enabled)", ["Task", "Calls", "Completed", "Mean ms", "p50 / p95 ms"], [
    ["Meal explanation", "24", "100%", "1,515", "1,465 / 3,299"],
    ["Meal Advisor reply", "3", "100%", "4,735", "5,304 / 5,314"],
  ], [2600, 1200, 1500, 1500, 2226]),
  P("All 27 calls returned a valid answer within the timeout. The sample is small and shows availability and speed, not answer quality. The language model added 1.5 to 5 seconds per call, compared with about 12 ms for the rules, which is why the explanation is requested after the results are displayed."),
  H2("6.5 Grounded advisor"),
  P("All 38 labelled questions passed (E4), covering meal retrieval, carbohydrate arithmetic, explanations, food lookup, weekly summaries, safety (6/6), prompt injection (3/3), conversation (4/4) and user isolation. No answer contained an unsupported claim. The median response time was 12 ms (18 ms p95)."),
  H2("6.6 Glucose model scenarios"),
  ...FIG("07_glucose_curves.png", 6.0, "Estimated meal glucose for one meal under three choices (E8)."),
  P("For chicken rice with teh tarik (95.6 g carbohydrate, GL 66.3), the model estimates that a 15-minute brisk walk starting 15 minutes after the meal lowers the peak by 2.3% and the area under the curve by 2.7%; the walk uses about 55 kcal, 7% of the meal's energy. Eating two-thirds of the rice lowers GL to 48.4 and the peak by about 23%. In this example the portion has a larger effect than the walk. The values are population-level estimates, not measurements."),
  H2("6.7 Quality"),
  ...FIG("08_tests_growth.png", 5.6, "Automated tests over the project."),
  P("All 65 automated tests pass against a real PostgreSQL database. Browser tests pass at phone and desktop sizes without JavaScript errors. The acceptance run passed 9 of 9 checks, including with the internet disconnected, and data was retained after a restart."),
];

const findings = [
  H1("7. Findings and discussion"),
  H2("7.1 Findings"),
  ...BUL([
    "**Top-3 with correction works**: the correct class is in the top three for 85.7% of test photos, so a wrong first guess is usually corrected with one tap.",
    "**The model's confidence is usable**: calibration error is 2.35%, and the thresholds in the application separate likely-correct guesses (85.7% correct at 0.50 or above) from unlikely ones (17.4% below 0.20).",
    "**Local dishes are harder than Western ones**: 72.1% top-1 on Food-101 against 68.8% on FoodSG-233; the weakest classes are visually similar noodle and rice dishes.",
    "**Rules for facts, model for wording**: the advisor gave no unsupported claims in testing; the small language model was weaker than the rules on parsing and matching, and its meal explanations added numbers in 5 of 6 cases until they were validated (v0.13.13).",
    "**Unidentified rather than wrong**: 48% of steaks on multi-food plates were left for the user to name instead of being given a wrong label.",
    "**Portion matters more than activity** in the glucose estimate for a typical hawker meal: two-thirds of the rice lowers the peak by about 23%, a 15-minute walk by 2.3%.",
    "**Low running cost**: all models run on one CPU server; classification takes about 12 ms and a multi-food analysis about 0.26 s.",
  ]),
  H2("7.2 Trade-offs and threats to validity"),
  ...TABLE("Design trade-offs", ["Choice", "Gained", "Given up"], [
    ["EfficientNet-B0, partial fine-tuning", "Runs on CPU in ~12 ms; trains in ~40 minutes", "Accuracy of larger backbones; validation was still rising at epoch 5"],
    ["One backend process instead of a job queue (proposal: Redis + ML worker)", "Simpler deployment; analysis in ~0.26 s", "Horizontal scaling for many simultaneous users"],
    ["Small local language model (1.5B)", "Data stays on the server; no paid AI service", "Wording quality; facts must come from rules"],
    ["Portion from priors and plate area", "Works from one photo", "Accuracy (±35–50%); volume is not measured"],
    ["Top-3 review before saving", "Errors corrected by the user", "One extra step per meal"],
  ], [2800, 3113, 3113]),
  P("Threats to validity:"),
  ...BUL([
    "**Test images are dataset photos**, cleaner and better framed than photos taken at a stall; accuracy and calibration on real use are not yet measured.",
    "**Single training run** with one seed; no variance across runs is reported.",
    "**The multi-food evaluation is synthetic** (100 plates composed from Food-101 test images).",
    "**Small samples** for the language model (20, 15, 6 and 8 items; 27 logged calls).",
    "**Nutrition values are unverified** (204 approximations), so nutrient and GL figures carry an error that is not quantified.",
    "**Portion error was not measured**; the proposal's MAE against weighed portions is still open.",
    "**Internal validity of the classifier test is protected** by the duplicate audit: no identical image appears in both training and test.",
  ]),
  H2("7.3 Implications for the MVP"),
  ...BUL([
    "**Keep the human in the loop**: top-3 review and drawn boxes stay central, since one in seven photos does not have the right food in the top three.",
    "**Keep the language model on wording only**, behind the validator; re-evaluate a larger local model with the same benchmark before giving it more scope.",
    "**Replace the nutrition table** with a verified Singapore source before any clinical or commercial use.",
    "**Ask the user when a text match is fuzzy**, not only when it fails (4 of 15 confident wrong matches).",
    "**Run the planned trial** before scaling: 5–8 moderated sessions, then a two-week field trial with 15–30 participants (SUS, UMUX-Lite, trust, comprehension, willingness to pay), plus weighed reference portions for portion MAE, under PDPA consent.",
    "**Licence**: YOLO11n-seg is AGPL-3.0; a commercial MVP needs compatible terms or another detector.",
  ]),
  H1("8. Conclusion and future work", false),
  P("MealSenseAI estimates the nutrition and glycaemic effect of a hawker meal from a photo, using models that run locally on a CPU server. I trained the classifier on 306,668 de-duplicated images from Food-101 and FoodSG-233; it reaches 70.6% top-1 and 85.7% top-3 accuracy on 45,800 test images, with well-calibrated confidence. GL can be calculated for 135 of 286 foods, and the advisor's answers contain only numbers from the system's own data."),
  P("Future work:"),
  ...NUM([
    "Measure accuracy, calibration and portion error on photos taken by users in the planned trial.",
    "Retrain with governed user data (consented, screened, versioned) through the model gate, focusing on the confused local dishes, and train for more epochs.",
    "Import a verified Singapore nutrition source and record GI provenance per food.",
    "Evaluate larger local language models with the same benchmark.",
    "Extend from diabetes to other diet-related goals already in the profile, such as weight and heart health, with their own evaluation.",
  ], "num2"),
];

const appendices = [
  H1("Appendix A. Project Proposal"),
  P("I submitted the project proposal on 30 September 2026 as a slide deck with speaker notes; the proposal document is also in the repository as 01-PRS_Project_Prposal.pdf. [[Attach the proposal file with this report if the submission requires it.]] Its main points:"),
  ...TABLE("Summary of the proposal", ["Item", "Proposal"], [
    ["Problem", "Hawker meals carry no nutrition label; people with diabetes estimate carbohydrate and portions by eye"],
    ["Users", "People with Type 1 and Type 2 diabetes in Singapore (MVP), then Southeast Asia; SDG 3"],
    ["Solution", "Photo-based food recognition, portion estimation, nutrition mapping and AI contextualisation with recommendations"],
    ["Pipeline", "Ten stages from meal capture to application output (Figure 2)"],
    ["Data", "FoodSG-233 and Food-101, harmonised, de-duplicated and split for training, validation and test"],
    ["Infrastructure", "Web UI, reverse proxy, API, Redis job queue and ML worker, MinIO, MLflow, Jupyter, local SLM on Ollama, optional frontier LLM"],
    ["Validation", "Segmentation mAP; classification confusion matrix, accuracy, precision, recall, F1; portion MAE; recommendation factuality, relevance and safety"],
    ["Business model", "Freemium; subscription S$3.99/month (Singapore), S$2.99/month (ASEAN)"],
  ], [2200, 6826]),
  P("Section 4.2 compares the proposed design with what was built, and Section 5 maps the proposed validation measures to the results."),
  H1("Appendix B. Mapped Functionalities to Modular Courses"),
  P("The table maps MealSenseAI's functions to the three courses of the graduate certificate. [[Check the topic names against the official course outlines.]]"),
  ...TABLE("Intelligent Sensing and Sense Making", ["Topic area", "MealSenseAI function", "Section"], [
    ["Image acquisition and pre-processing", "Phone camera or upload; EXIF orientation; resizing and normalisation identical to training (verified on 601 images)", "3.2, 6.1"],
    ["Object detection and instance segmentation", "YOLO11n-seg finds food and container regions on a plate; each region is classified separately", "3.5, 6.1"],
    ["Measurement from images", "Portion from the food mask's area relative to a detected plate or bowl, or a reference object, with an uncertainty band", "3.6"],
    ["Sense making from several sources", "Combining model output, user corrections and the user's glucose readings into meal-level meaning: GL, glucose estimate, personal calibration", "3.6, 3.7"],
  ], [2700, 4826, 1500]),
  ...TABLE("Pattern Recognition and Machine Learning Systems", ["Topic area", "MealSenseAI function", "Section"], [
    ["Data preparation", "Class harmonisation (334 → 320), SHA-256 duplicate audit, exclusion of conflicting labels, stratified split", "3.3"],
    ["Supervised learning with CNNs and transfer learning", "EfficientNet-B0: frozen-backbone stage, then partial fine-tuning with discriminative learning rates and augmentation", "3.4"],
    ["Model evaluation", "Top-1/top-3 accuracy, macro precision, recall and F1, per-class F1, confusion matrix, calibration (ECE)", "6.1"],
    ["Similarity-based recognition", "Personal food memory: classifier output as an embedding, cosine similarity ≥ 0.70 with a margin", "3.9"],
    ["Deploying and maintaining models", "ONNX export with parity check; screening of training samples; model gate with shadow mode", "3.9, 6.1"],
  ], [2700, 4826, 1500]),
  ...TABLE("Problem Solving using Pattern Recognition", ["Topic area", "MealSenseAI function", "Section"], [
    ["Problem formulation", "Business case, users and pricing; proposal success measures", "1, Appendix A"],
    ["End-to-end system design", "Ten-stage pipeline from capture to output, deployed as containers on one server", "3.1, 3.2, 4"],
    ["Hybrid reasoning", "Rules for nutrition mapping, GI borrowing and advice; a local language model for wording, checked by a validator", "3.6, 3.8, 6.4"],
    ["Modelling", "Glucose response as a one-compartment mass-balance model with activity uptake", "3.7, 6.6"],
    ["Evaluation in context", "Multi-food plates, advisor grounding, language-model benchmark, acceptance tests", "5, 6"],
  ], [2700, 4826, 1500]),
  H1("Appendix C. Installation Guide and User Guide"),
  H2("Installation Guide"),
  ...TABLE("Prerequisites", ["Item", "Requirement"], [
    ["Operating system", "Ubuntu 22.04/24.04, macOS 13+, or Windows 11 with WSL2"],
    ["Docker", "Docker Engine 24+ with Compose v2.24+, or Docker Desktop"],
    ["Hardware", "2 CPU cores, 4 GB RAM, 5 GB free disk; no GPU needed"],
    ["Network", "Only to build the images the first time; the application runs offline"],
  ], [2200, 6826]),
  P("Install and run, from the project folder:"),
  new Paragraph({ spacing: { after: 0, line: 252 }, indent: { left: 360 }, children: [run("./scripts/start.sh --demo   # first run builds the images (5–10 min)", { font: "Consolas", size: 18 })] }),
  new Paragraph({ spacing: { after: 0, line: 252 }, indent: { left: 360 }, children: [run("# open http://localhost:8080  (demo@mealsense.ai / demo12345)", { font: "Consolas", size: 18 })] }),
  new Paragraph({ spacing: { after: 0, line: 252 }, indent: { left: 360 }, children: [run("./scripts/acceptance.sh     # acceptance tests (add --offline)", { font: "Consolas", size: 18 })] }),
  new Paragraph({ spacing: { after: 0, line: 252 }, indent: { left: 360 }, children: [run("./scripts/stop.sh           # stop; data is kept", { font: "Consolas", size: 18 })] }),
  P(""),
  ...BUL([
    "**Optional local language model**: start with the slm profile and set OLLAMA_URL=http://ollama:11434 in .env; the model qwen2.5:1.5b is pulled automatically.",
    "**Optional GPU**: ./scripts/start.sh --gpu (NVIDIA driver and Container Toolkit required); without CUDA the backend falls back to CPU.",
    "**Admin role**: docker compose exec backend python -m app.tools.admin grant <email>.",
    "**Configuration** (.env): HTTP_PORT (default 8080), JWT_SECRET, POSTGRES_PASSWORD, INFERENCE_DEVICE, REDIS_URL, OLLAMA_URL.",
    "**Troubleshooting**: docs/INSTALL_AND_TROUBLESHOOTING.md in the repository.",
  ]),
  H2("User Guide"),
  ...NUM([
    "**Register and onboard**: create an account, then fill in the optional profile: personal details, health condition (stored only with consent), glucose unit and readings, and goals.",
    "**Capture a meal**: take or upload a photo; optionally describe the food or choose a plate or bowl as a reference; tap Analyze meal and follow the ten stages.",
    "**Review**: each food shows the model's top three; tap another candidate to switch, search the food list, enter grams, remove an item, or add a missed food by dragging a box on the photo. Low scores are marked for checking; below 0.20 nothing is added automatically.",
    "**Understand the meal**: glucose impact and GL, energy and nutrients against the day's goals, meal composition, recommendations, and the portion and activity what-if.",
    "**Save and review history**: choose the meal type and confirm; meals appear in Meal History, the Dashboard and Nutrition Insights.",
    "**Ask the Meal Advisor** about meals, carbohydrate, foods or the week; answers show where each fact comes from.",
    "**Optional learning**: named foods are remembered for the account; corrected crops can be shared for training in Settings, with consent that can be withdrawn.",
    "**Administrators**: the Admin menu holds training-data review, dataset versions, the model gate, model settings, prompts and the audit log.",
  ], "num3"),
  P("MealSenseAI gives educational estimates. It does not diagnose or replace advice from a doctor, dietitian or diabetes care team. The full guide is docs/USER_GUIDE.md."),
];

const declarations = [
  H1("Appendix D. AI Tool Declaration"),
  P("This appendix declares the AI tools I used, the datasets and other third-party sources, and my own scope of work. Text highlighted in yellow is for me to confirm before submission."),
  H2("D.1 AI tools used"),
  ...TABLE("AI tools used in the project", ["Tool", "How I used it", "What it produced"], [
    ["Claude (Anthropic), through Claude Code, a coding assistant with access to the repository and a cloud container", "I described features, defects and decisions in conversation; it wrote and changed code, ran tests in its container, and drafted documents. It had no access to my home server (\"Buddy\")", "Most of the application source code (backend, frontend, Docker configuration), the automated tests, the evaluation scripts, the documentation, the charts, this report's draft text, the two slide decks and the demo-video scripts"],
    ["ChatGPT (OpenAI), which I refer to as \"Lisa\"", "[[Assistant while I prepared the data and trained the model on Buddy: describe exactly what Lisa wrote or advised, e.g. the cleaning, split, training and evaluation scripts]]", "[[e.g. dataset cleaning and audit scripts; EXP-001/EXP-002 training and evaluation scripts]]"],
    ["[[Any other AI tool, e.g. for the proposal of 30 September 2026, or none]]", "[[ ]]", "[[ ]]"],
  ], [2400, 3326, 3300]),
  P("The repository records the extent of the assistance: 53 of its 54 commits (23–29 October 2026) carry a \"Co-Authored-By: Claude\" line and a link to the Claude Code session that produced them. The one commit without it is my upload of the proposal on 15 September 2026."),
  P("The local language model in the product (Qwen 2.5 1.5B, run by Ollama) is a component of the application, not a tool used to write it. It is evaluated in Section 6.4."),
  P("I checked AI output by running it rather than by trusting it. Every number in this report comes from an evidence file in the repository or a cited source, and the evaluation scripts can be re-run. Where AI-written text or code was wrong, I found it in use and had it corrected, for example:"),
  ...BUL([
    "a drawn box on the photo could not be selected or dragged on a phone (fixed in v0.13.2);",
    "the photo hint was unreadable in light mode;",
    "the report and slides did not follow my submitted proposal (pricing, users, pipeline names) until I asked for them to be aligned (v0.13.12);",
    "the documents described a group project and a diabetes-only product; I corrected both (v0.13.14, v0.13.15);",
    "the report presented the classifier results as reported by a developer; I supplied my own training evidence, which also showed that the data split was not 70/15/15 as written (v0.13.17).",
  ]),
  H2("D.2 Datasets and third-party sources"),
  ...TABLE("Datasets, pre-trained models and other sources", ["Source", "Used for", "Terms and citation"], [
    ["Food-101 (ETH Zürich): 101 classes, 101,000 images", "Training and testing the food classifier", "Research use; images remain the property of their owners. Bossard, Guillaumin and Van Gool, ECCV 2014 [5]"],
    ["FoodSG-233 (NUS FoodLG): 233 Singapore classes, 209,861 images", "Training and testing the food classifier", "Non-commercial research and education; access granted by the authors on request. Zheng et al., arXiv:2301.03829, 2023 [11]"],
    ["ImageNet-1k weights for EfficientNet-B0 (torchvision)", "Starting point for transfer learning", "Tan and Le, ICML 2019 [4]; Deng et al., CVPR 2009 [12]; torchvision weights, BSD-3-Clause code"],
    ["YOLO11n-seg (Ultralytics), trained on COCO", "Finding food regions on a plate", "AGPL-3.0; Jocher and Qiu, Ultralytics YOLO11, 2024 [13]; COCO: Lin et al., ECCV 2014 [14]"],
    ["Qwen 2.5 1.5B Instruct (Alibaba), run with Ollama", "Rewording advisor answers; meal explanations", "Apache-2.0; Qwen Team, Qwen2.5 Technical Report, 2024 [15]"],
    ["USDA FoodData Central", "62 nutrition records", "Public domain (U.S. Government) [16]"],
    ["Singapore HPB Energy & Nutrient Composition of Food", "20 nutrition records", "Health Promotion Board, Singapore [17]"],
    ["International Tables of Glycemic Index (2021)", "Published GI values", "Atkinson et al., 2021 [1]"],
    ["Compendium of Physical Activities", "MET values for the activity what-if", "Ainsworth et al., 2011 [2]"],
    ["Wikimedia Commons meal photos", "Demo video and examples only, not training", "Free licences; credited per photo in demo/SOURCES.md"],
  ], [2700, 2626, 3700]),
  P("The remaining 204 nutrition records are approximations I added so that most classes have a value; they are labelled as such in the application and are not verified. The datasets are not redistributed with the project; only the trained model and its evaluation results are included."),
  H2("D.3 My scope of work"),
  P("I am the sole author of this project. My work covered the following; the evidence column points to where it can be checked."),
  ...TABLE("Statement of my own work", ["Area", "What I did", "Evidence"], [
    ["Problem and proposal", "Chose the problem, researched the market and competitors, defined the users, pricing and market scenario, designed the ten-stage pipeline and the infrastructure, and set the validation measures. [[State whether any AI tool helped with the proposal.]]", "Proposal deck (30 September 2026); 01-PRS_Project_Prposal.pdf in the repository (15 September 2026)"],
    ["Product specification", "Decided every feature and its behaviour, and the priorities between them, for example top-3 correction, marking a missed food on the photo, choosing among unidentified items, collapsing insights to reduce clutter, borrowing GI for local dishes, and the safety rule that model text must never introduce its own numbers", "Session transcripts linked from each commit; CHANGELOG.md"],
    ["Data and model training", "Selected Food-101 and FoodSG-233, obtained access, prepared and audited the data (310,861 images, 4,193 excluded), defined the split, and trained and evaluated EXP-001 and EXP-002 on my own GPU server, with Lisa's assistance as declared in D.1", "ml/models/exp002/evidence/training (configuration, environment, training history and evaluation, dated 23 October 2026)"],
    ["Infrastructure and operations", "Built and run the home server \"Buddy\" (GPU, Docker, Ollama); deployed every release; ran the acceptance tests, the language-model benchmark and the inference-log queries; managed the GitHub repository and access", "Results I supplied: slm_eval.json, inference-log figures (Section 6.4), acceptance runs (TEST_REPORT.md)"],
    ["Testing and review", "Used the application on phone and desktop, reported defects with screenshots, accepted or rejected each change, and approved changes that affect safety (v0.13.13)", "Session transcripts; TEST_REPORT.md"],
    ["Positioning and presentation", "Set the positioning (for anyone, diabetes first), the individual-project framing, and the content of both presentations; I record the narration and camera segments of the video myself", "Slide decks; demo/RECORDING-SCRIPT.md"],
    ["[[Anything else, e.g. hours spent, user interviews, research]]", "[[ ]]", "[[ ]]"],
  ], [2000, 4626, 2400]),
  P("I did not write most of the application code by hand; Claude did, under my direction, as declared in D.1. I am responsible for the system's design, its data and model, the decisions recorded above, and the accuracy of what is reported here."),
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
    "Zheng K, Nguyen T, Chong JHS, Goh CE, Herschel M, Lee HH, Liu C, Ooi BC, Wang W, Yip J. From Plate to Prevention: A Dietary Nutrient-aided Platform for Health Promotion in Singapore. arXiv:2301.03829, 2023.",
    "Deng J, Dong W, Socher R, Li LJ, Li K, Fei-Fei L. ImageNet: A large-scale hierarchical image database. CVPR 2009.",
    "Jocher G, Qiu J. Ultralytics YOLO11, version 11.0.0. 2024. https://github.com/ultralytics/ultralytics (AGPL-3.0).",
    "Lin TY, et al. Microsoft COCO: Common objects in context. ECCV 2014.",
    "Qwen Team. Qwen2.5 Technical Report. arXiv:2412.15115, 2024.",
    "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central. https://fdc.nal.usda.gov/",
    "Health Promotion Board, Singapore. Energy & Nutrient Composition of Food. https://focos.hpb.gov.sg/",
  ], "ref"),
  H2("Evidence files"),
  ...BUL([
    "ml/models/exp002/evidence/training (EXP-001 and EXP-002 configuration, environment, training history, evaluation, per-class F1, derived summary); docs/report/derive_training_evidence.py",
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
  numbering: { config: [num("bul", LevelFormat.BULLET), num("num", LevelFormat.DECIMAL), num("num2", LevelFormat.DECIMAL), num("ref", LevelFormat.DECIMAL), num("num3", LevelFormat.DECIMAL)] },
  sections: [
    { properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children: cover },
    { properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 }, pageNumbers: { start: 1 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(HERE, "nus_iss_logo.png")), transformation: { width: 158, height: 40 }, altText: { title: "NUS ISS", description: "National University of Singapore, Institute of Systems Science", name: "NUS ISS logo" } })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.CENTER, position: W / 2 }, { type: TabStopType.RIGHT, position: W }], children: [run("MealSenseAI · Final Report", { size: 16, color: INK2 }), run("\t© National University of Singapore", { size: 16, color: INK2 }), new TextRun({ children: ["\t", PageNumber.CURRENT], size: 18, color: INK2 })] })] }) },
      children: [...toc, ...summary, ...business, ...tools, ...design, ...dev, ...experiments, ...perf, ...findings, ...refs, ...appendices, ...declarations] },
  ],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(path.join(HERE, "MealSenseAI-Final-Report.docx"), b); console.log("written"); });
