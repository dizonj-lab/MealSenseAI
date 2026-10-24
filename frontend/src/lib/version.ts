/** App version (kept in step with backend/app/version.py) and high-level release notes, newest first. */
export const APP_VERSION = '0.11.0'

export const CHANGELOG: { version: string; title: string; changes: string[] }[] = [
  { version: '0.11.0', title: 'Contact form and creator links', changes: [
    'Contact page now has a form; messages are saved and emailed to the creator',
    'Removed the draft notices from the Privacy, Terms and Contact pages',
    'Creator profile links to LinkedIn',
  ] },
  { version: '0.10.0', title: 'Glucose estimates in mmol/L', changes: [
    'Forecast and portion simulator charts now show glucose in mmol/L (or mg/dL from your profile) instead of a relative index',
    'Starts from your logged pre-meal reading; without one, the chart shows the estimated rise above your pre-meal level',
    'Population estimate with a wide range; after 3 meals with before and after readings it calibrates to your own response',
    'Always labelled an estimate, even with a known baseline; your measured readings are shown as dots for comparison',
  ] },
  { version: '0.9.0', title: 'A friendlier Meal Advisor', changes: [
    'Warm, witty personality that adapts its tone: playful for food chat, careful for diabetes topics, serious for urgent ones',
    '“You missed my sausage!” offers a one-tap Add button; the meal updates when you tap it',
    'Handles “is this too much rice?”, “can I eat pizza?”, mystery dishes and questions it cannot answer, honestly',
    'Remembers the food you are talking about: “Is nasi lemak healthy?” → “What if I skip the rice?” → “What about adding an egg?”',
  ] },
  { version: '0.8.0', title: 'Minimal design, grounded conversations', changes: [
    'New minimalist landing, sign-in and register pages; Privacy, Terms and Contact pages (drafts)',
    'Onboarding is now enforced by the server; age range, other goals and a “why we ask” note added',
    'Meal Advisor rebuilt: every fact is traced to you, the photo model, the food table or approved guidance',
    'Follow-up questions, “what if I remove the rice?” (never saved), how a food was identified, low-confidence checks',
    'Replies from the local language model are checked against your data; urgent and medication questions handled safely',
    'Conversations are kept on the server for 30 days and can be cleared',
  ] },
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
