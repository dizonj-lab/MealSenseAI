# Final report and its figures

- `make_charts.py`: the ten figures in `charts/`, from the repository's evidence files, `model_data.json` (glucose curves and
  GI counts computed with the app's own services) and `baselines.json` (rule-based text-matching baselines). If
  `slm_eval.json` (from `python -m app.tools.slm_eval` on the server) is placed here, the latency and text-matching
  charts gain the language model's results.
- `build_report.js`: the Word report (`npm i docx`, then `node build_report.js`); with `slm_eval.json` present, section
  6.4 is filled from it instead of being marked pending.
