/** App version (kept in step with backend/app/version.py) and high-level release notes, newest first. */
export const APP_VERSION = '0.7.0'

export const CHANGELOG: { version: string; title: string; changes: string[] }[] = [
  { version: '0.7.0', title: 'Meal Advisor, About page, easier saving', changes: [
    'Meal Advisor chat grounded in your meals, profile and the food table; medication questions declined',
    'Meal type and Save pinned at the top of the meal review',
    '“Can’t find it?” pinned at the top of the food picker; short help tips on key controls',
    'Appearance setting (system / light / dark); version shown next to the logo; About page with datasets, model and evaluation',
  ] },
  { version: '0.6.0', title: 'Your own foods and food memory', changes: [
    'Create foods that are not in the list, with portion and nutrients (unknowns stay blank)',
    'Foods you name are recognised again from your earlier labels',
    'Opt-in export of corrected photo regions for the next training cycle',
  ] },
  { version: '0.5.0', title: 'Clearer, calmer interface', changes: [
    'Landing page before login and a getting-started checklist for new accounts',
    'Simple / Detailed meal review with “Why?” explanations on every card',
    'Pipeline progress bar with a telemetry drawer; dark and light mode',
    'AI explanation no longer delays results',
  ] },
  { version: '0.4.0', title: 'Multi-food recognition and health intelligence', changes: [
    'Every food on the plate detected, numbered and editable (rename, merge, remove, add)',
    'Meal composition dashboard, portion simulator and glycaemic-load breakdown',
    'Measured glucose readings (mmol/L) and personalised insights by goal',
  ] },
  { version: '0.3.0', title: 'EXP-002 model and portable deployment', changes: [
    'EXP-002 EfficientNet-B0 (320 Food-101 + FoodSG classes) served on CPU via ONNX Runtime, top-3 suggestions',
    'One-command Docker deployment, offline mode and the NUS submission package',
  ] },
  { version: '0.2.0', title: 'Forecasts and infrastructure', changes: [
    'Educational energy and glucose forecast with activity what-ifs, citations and cautions',
    'Docker Compose stack, test environment and home-server hardening guide',
  ] },
  { version: '0.1.0', title: 'First MVP', changes: [
    'Sign-up, health onboarding, meal capture, food recognition, nutrition estimates, insights and history',
  ] },
]
