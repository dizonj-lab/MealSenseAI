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
  new Paragraph({ spacing: { after: 80 }, children: [run("Final draft · 29 October 2026 · system version v0.13.17 · follows the proposal of 30 September 2026", { size: 22, color: INK2 })] }),
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
    ["Food recognition", "EfficientNet-B0, 320 classes, 45,800 test images: **70.6% top-1, 85.7% top-3**, macro-F1 66.7%; calibration error 2.35%", "training evidence (Buddy)"],
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
  P("The scenario is the one from my proposal and is not a forecast. It counts adults with diabetes only and so excludes users without a condition. The 50% operating-cost assumption has not been validated; the build shows only that the compute cost is low, since all models run on one CPU server without a paid AI service. I will measure willingness to pay in the trial (Section 7.4)."),
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
  P("I developed the system iteratively, in versioned releases from v0.1 to v0.13.17 (about 55 commits between 23 and 29 October 2026, after the proposal of 30 September). I tested each release, recorded it in the changelog and test report, and deployed it to my home server (\"Buddy\"). The code base has about 6,800 lines of Python in the backend, 3,700 lines of TypeScript in the frontend and 2,000 lines of machine-learning tooling, with 10 test modules."),
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
  H2("7.1 What worked"),
  ...BUL([
    "**Top-3 with correction**: with the correct class in the top three for 85.7% of photos, a wrong first guess is usually fixed with one tap.",
    "**Rules for facts, model for wording**: the advisor gave no unsupported claims in testing and falls back to rules when the model is slow or offline. Meal explanations, which were not validated, contained unsupported numbers in 5 of 6 cases; they are validated from v0.13.13.",
    "**Unidentified rather than wrong**: 48% of steaks were left unidentified for the user to name instead of being given a wrong label, which is safer when carbohydrate is being counted.",
    "**Low running cost**: all models run on one CPU server; classification takes about 12 ms and a multi-food analysis about 0.26 s.",
  ]),
  H2("7.2 Limitations"),
  ...BUL([
    "**Limited value from the small language model**: the rules performed better on parsing and matching, and 5 of 6 meal explanations contained a number of their own. Since v0.13.13 those are withheld, so most users will see the rule-based results without a model explanation. A larger or fine-tuned local model would need to be re-measured with the same benchmark.",
    "**Visually similar dishes** (local noodle and rice dishes, steak cuts, dumplings) remain the main confusion; 45 of 320 classes have F1 below 50%.",
    "**Portions** come from priors or area, not volume (±35–50%); entering grams is more accurate. I have not yet measured portion error (MAE against weighed portions) as proposed.",
    "**Nutrition values are unverified** transcriptions (USDA- and HPB-style values) or recipe approximations (199 records); a verified import (HPB SG FoodID, USDA FDC) is required before clinical use.",
    "**Glucose estimates** use population physiology; they are not predictions for an individual and must never inform insulin dosing.",
    "**Test conditions**: E1 uses dataset photos, which are cleaner than photos taken at a hawker stall; the calibration result may not hold for real use. The multi-food set is synthetic, and no real-user trial has been run.",
    "**Fuzzy lookup errors** (4 of 15 confident wrong matches) bypass the language model today.",
    "**Licence**: YOLO11n-seg is AGPL-3.0; serving publicly needs compatible terms or replacing the detector.",
  ]),
  H2("7.3 Recommendations"),
  ...NUM([
    "Ask the language model (or show the user a choice) when the fuzzy lookup is only a fuzzy match, not only when it finds nothing.",
    "Retrain with governed user data (consented, screened, frozen) through the model gate, prioritising confused groups.",
    "Replace the nutrition table with a verified Singapore source and record GI provenance per food.",
    "Check accuracy and calibration on photos taken by users, and train for more epochs, since validation scores were still rising at epoch 5.",
  ], "num2"),
  H2("7.4 Trial plan"),
  P("I plan a two-phase evaluation. Phase 1 is five to eight moderated sessions measuring task success, time and ease. Phase 2 is a two-week field trial with 15–30 participants, measuring the System Usability Scale, UMUX-Lite, trust, comprehension and willingness to pay. I will weigh reference portions to measure portion error (MAE), as set out in the proposal. The application already logs the required behaviour: accepted and corrected foods, top-3 selections, drawn boxes, memory matches, portion edits and language-model use. Participation requires PDPA consent; training consent is off by default, and the application states that it does not give medical advice."),
  H1("8. Conclusion", false),
  P("MealSenseAI estimates the nutrition and glycaemic effect of a hawker meal from a photo, using models that run locally on a CPU server. Recognition reaches 85.7% top-3 with one-tap correction, GL can be calculated for 135 of 286 foods, and the advisor's answers contain only numbers from the system's own data. My next steps are a trial with real users and a verified nutrition source."),
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
