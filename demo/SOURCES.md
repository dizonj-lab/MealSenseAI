# Sources for the figures in the presentation video (narration-full.json)

| Figure | Source |
|---|---|
| ~830 million people living with diabetes | World Health Organization, 2022 (as cited in the project proposal) |
| About 1 in 12 adults in Singapore (8.5%) | Ministry of Health, Singapore, 2023 (as cited in the project proposal) |
| Up to 1 million residents by 2050 without effective prevention | MOH projection (as cited in the project proposal) |
| S$1 billion in 2010 → S$2.5 billion by 2050; most of it lost productivity | Png ME, et al. Current and future economic burden of diabetes among working-age adults in Asia: conservative estimates for Singapore from 2010–2050. *BMC Public Health* 2016;16:153. doi:10.1186/s12889-016-2827-1 |
| About 18% less household sugar from pre-packed drinks after Nutri-Grade | Nutri-Grade before-and-after study (as cited in the project proposal) |
| Photo calorie apps around US$30 a year | Cal AI published pricing (~US$29.99/year), 2026; third-party summaries, confirm in the App Store |
| Premium trackers around US$80 a year | MyFitnessPal Premium published pricing (US$79.99/year), 2026; confirm at myfitnesspal.com/premium |
| Pricing tiers (Free, Plus S$4.90/month or S$39/year, Care per member) | Proposed by the project; to be validated in the trial |
| 70.6% top-1, 85.7% top-3, 66.7% macro-F1 | EXP-002 developer evaluation (`ml/models/exp002/model_card.json`) |
| Same top 3 after ONNX export on 601 images; 11.8 ms per photo | Measured (`ml/models/exp002/evidence/onnx_parity.json`) |
| 74.7% precision, 68.4% recall, 262 ms median per plate | Measured on 100 synthetic multi-food plates (`test-results/multifood_metrics.json`) |
| 247 exact · 66 proxy · 7 none | `ml/models/exp002/evidence/nutrition_coverage.json` |
| 57 foods with a published GI, 78 borrowing their staple's | `datasets/nutrition/foods.json` and `services/nutrition.py` (v0.13.8) |
| 38 of 38 Meal Advisor test questions, 0% unsupported claims | `test-results/advisor_eval.json` (rule engine; language model off) |
| 64 automated tests; 9 acceptance checks, also offline | `docs/TEST_REPORT.md`, `test-results/acceptance_*.json` |
