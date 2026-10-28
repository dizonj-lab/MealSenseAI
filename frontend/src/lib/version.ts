/** App version (kept in step with backend/app/version.py) and high-level release notes, newest first. */
export const APP_VERSION = '0.13.8'

export const CHANGELOG: { version: string; title: string; changes: string[] }[] = [
  { version: '0.13.8', title: 'Glycaemic load for more local dishes', changes: [
    'A dish with no published GI, such as chicken rice, char kway teow, roti prata or teh tarik, now borrows the GI of its main carbohydrate',
    'Shown with ≈ and the food it was borrowed from; foods with no clear staple still say "not estimated"',
    'The borrowing follows fixed rules, never the language model',
  ] },
  { version: '0.13.7', title: 'Name unidentified foods from the Meal Advisor', changes: [
    'Ask the Meal Advisor about the unidentified items: it lists its guesses for each, and one tap names the item',
    'It also offers regions it spotted but was unsure about, and Mark it on the photo, which opens marking mode on the meal page',
    '"You missed something" now offers Mark it on the photo as well',
  ] },
  { version: '0.13.6', title: 'Readable marking hint', changes: [
    'The "Drag a box around the food" hint is readable in light and dark mode, and sits above the photo instead of over it',
  ] },
  { version: '0.13.5', title: 'Pick or remember missed foods', changes: [
    'Mark it on the photo also shows the regions the app found but did not list, as dotted outlines: tap + Add to add one, then name it',
    'A box you draw is recognised from your own earlier labels, the same way the app recognises regions it finds itself',
  ] },
  { version: '0.13.4', title: 'A calmer meal page', changes: [
    'Every insight, including Key takeaways and Ask the Meal Advisor, is now a one-line row under Insights; tap to open',
    'Each row still shows its key point, such as the glucose impact, kcal and carbs, or whether the meal needs attention',
    'Allergy warnings stay open. Detailed view still opens everything',
  ] },
  { version: '0.13.3', title: 'Safer side-by-side installs', changes: [
    'A second copy of the app on the same server (for example a test run) no longer replaces the images the live app uses',
  ] },
  { version: '0.13.2', title: 'Mark a food on the photo', changes: [
    'Add missing food: drag a box around it on the photo, with a mouse, finger or pen; the model names what is inside and estimates the portion',
    'Foods added by name or description can be shown on the photo too (Show where it is on the photo)',
    'Marked foods are kept when a meal is analysed again; you can still rename them or change the portion',
  ] },
  { version: '0.13.1', title: 'Clearer meal composition', changes: [
    'Meal composition redesigned: the meal at a glance, where its energy comes from, and each nutrient against your day',
    'Amber shows when one meal alone goes past its share of a limit (carbohydrate goal, the WHO sodium limit, saturated fat)',
    'Food-by-food comparison by carbs, kcal or sodium for meals with several foods; missing values are shown as missing',
  ] },
  { version: '0.13.0', title: 'Safer learning from your photos', changes: [
    'Sharing corrected photos for training is now tracked per photo; switching it off withdraws everything you shared from future training',
    'Settings shows what you shared, what was accepted and what is in review',
    'Confirm your email to let your shared photos be used',
    'Every shared photo is checked automatically, and suspicious ones are reviewed by a person before any model learns from them',
  ] },
  { version: '0.12.0', title: 'Watch the demo', changes: [
    'A four-minute narrated tour, from the landing page (beside Get Started and in the top bar) and from About MealSenseAI',
    'Plays in a window over the page, with subtitles; Escape or a click outside closes it',
  ] },
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
