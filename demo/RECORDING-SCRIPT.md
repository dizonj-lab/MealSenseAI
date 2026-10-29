# Recording script: MealSenseAI-presentation

Record each line as its own file, named by its number: `01.m4a`, `02.m4a` … (any common audio format).
Quiet room, same distance from the mic, half a second of silence before and after. Redo a line rather
than editing it. Camera lines may be one take for several lines, named by the range: `01-05.mp4`.
Voice-only lines time the demo, so read them at the pace you want the screen to move.

## Business

**01 · No label on the plate** — on camera (video + audio), file `01.mp4`, about 26 s

Three times a day, people living with diabetes make the same decision: what to eat, and how much. A packet of biscuits tells you its sugar. A plate of chicken rice from the hawker centre tells you nothing. There's no label and no serving size, and the carbohydrates hide in the rice, the sauce and the drink on the side.

**02 · So people guess** — on camera (video + audio), file `02.mp4`, about 21 s

So people guess. They guess what's on the plate, how big the portion is, and what it means for their blood sugar. Mixed dishes are hard to break down, portions change from stall to stall, and logging every meal by hand is tedious, so most people simply stop.

**03 · Why it matters** — on camera (video + audio), file `03.mp4`, about 34 s

And the stakes are high. The World Health Organization counts about eight hundred and thirty million people living with diabetes. In Singapore it's about one adult in twelve, and without effective prevention, up to a million residents could be living with it by twenty fifty. A national study put the cost of diabetes to Singapore at about one billion dollars in twenty ten, rising to two and a half billion by twenty fifty, most of it lost productivity.

**04 · The gap** — on camera (video + audio), file `04.mp4`, about 27 s

We know visibility works. After Nutri-Grade labels, household sugar from pre-packed drinks fell by about eighteen percent. But labels stop at the bottle and the box. Food apps help you count calories or search a food list. What's still hard is the moment at the stall: knowing what this plate may do to your glucose, and how sure that estimate is.

**05 · What MealSenseAI does** — on camera (video + audio), file `05.mp4`, about 18 s

That's the gap MealSenseAI fills. One photo becomes foods, portions and nutrition. The numbers become meaning: glucose impact, glycaemic load, and a practical next step. And every estimate is honest about its uncertainty, so the person stays in control of every number.

**06 · Meet Wei Ming** — voice only (over the app demo), file `06.m4a`, about 13 s

Let me show you. This is Wei Ming, a fictional user who lives with type two diabetes. His profile sets the context: his condition, his goals and a daily carbohydrate target.

**07 · Dashboard** — voice only (over the app demo), file `07.m4a`, about 12 s

His dashboard shows today against those goals, a week of hawker meals, and where his energy comes from. Every number traces back to a meal he logged.

**08 · Capture** — voice only (over the app demo), file `08.m4a`, about 22 s

It's lunchtime, and he's having chicken rice. One photo from above is enough. Behind the scenes, ten steps run in a moment. The image is checked, each food is located and recognised among three hundred and twenty foods, the portion is estimated, and every item is mapped to a nutrition record.

**09 · Review** — voice only (over the app demo), file `09.m4a`, about 20 s

Each food is numbered on the photo, with its portion, calories and carbohydrates, and an honest range, because a photo can't weigh food. When the model is unsure, it says so and shows its next best guesses. Nothing is saved until Wei Ming confirms it.

**10 · Mark a missed food** — voice only (over the app demo), file `10.m4a`, about 20 s

The model doesn't always see everything. When it misses a food, Wei Ming drags a box around it, with a mouse or a finger, and the model looks at just that part. Once he names a food, MealSenseAI remembers it, and recognises it in his next photos.

**11 · What it means** — voice only (over the app demo), file `11.m4a`, about 28 s

Then the part that matters: what it means. The meal's potential glucose impact and its glycaemic load, with practical tips, like less rice or more vegetables. Chicken rice has no published glycaemic index, so MealSenseAI borrows the value of its main carbohydrate, white rice, and says so. The meal advisory flags where the meal goes past public health reference points, and cites its sources.

**12 · Portion simulator** — voice only (over the app demo), file `12.m4a`, about 17 s

What if he asks for less rice? The portion simulator answers before he eats. Slide the portion down, and the carbohydrates, the glycaemic load and the estimated glucose curve all update. It's labelled as an estimate, never as a measurement.

**13 · What if I walk?** — voice only (over the app demo), file `13.m4a`, about 20 s

And what about a fifteen minute walk after lunch? The forecast compares an afternoon at his desk with the walk, and shows how much of the meal's energy it uses. When he logs his own glucose readings, the estimate adjusts to how his body responds.

**14 · Meal Advisor** — voice only (over the app demo), file `14.m4a`, about 22 s

Questions come up, so there's a Meal Advisor. Wei Ming asks how his week went. The answer is built from his own meals and the food table, and each point shows where it came from. It doesn't invent numbers, it never diagnoses, and it can fix a meal in one tap.

**15 · Nutrition Insights** — voice only (over the app demo), file `15.m4a`, about 12 s

Over time, Nutrition Insights turns meals into trends: carbohydrates, sugar, fibre and sodium, day by day. Habits become visible, and so do the small changes that work.

**16 · Pricing** — on camera (video + audio), file `16.mp4`, about 35 s

Here's how we propose to offer it, to be tested in our trial. A free tier, to log meals and see their nutrition. MealSenseAI Plus, at four ninety a month or thirty-nine dollars a year, adds the glucose estimates, the Meal Advisor and the simulators. That places it between photo calorie apps, at around thirty US dollars a year, and premium trackers, at around eighty. And MealSenseAI Care, licensed per member to clinics, employers and insurers who support people with diabetes.

## System design

**17 · System design** — on camera (video + audio), file `17.mp4`, about 27 s

Now, how it works. MealSenseAI runs as four containers on a single server. The browser talks to one web server, which serves the app and forwards requests to a FastAPI backend. The backend holds the models, the nutrition rules and the Meal Advisor, and keeps everything in PostgreSQL. A small language model runs locally beside it. No paid cloud AI is involved.

**18 · The ten-stage pipeline** — on camera (video + audio), file `18.mp4`, about 18 s

Every photo goes through ten stages, and each one is visible to the user: capture, preprocessing, detection, classification, portion, nutrition, aggregation, explanation, recommendations, and the editable review. Model outputs, estimates and guidance are labelled differently, so it's always clear which is which.

**19 · Recognising the food** — on camera (video + audio), file `19.mp4`, about 37 s

Recognition uses EfficientNet-B0, fine-tuned by transfer learning on Food-101 and a Singapore food dataset: three hundred and twenty classes. We trained the last three blocks and the classifier head with AdamW, with a smaller learning rate for the backbone than for the head, and with data augmentation. It reached seventy-one percent top-one and eighty-six percent top-three accuracy. Exported to ONNX, it gave the same top three answers as the original model on six hundred test images, in about twelve milliseconds per photo on a CPU.

**20 · Several foods on a plate** — on camera (video + audio), file `20.mp4`, about 25 s

Real plates have several foods. A YOLO segmentation model proposes regions, and each region is classified. On a hundred multi-food test plates, detection reached seventy-five percent precision and sixty-eight percent recall, at about a quarter of a second per plate. That's why the review stays human in the loop: a correction is one tap, or one dragged box.

**21 · Portions, nutrition and glycaemic load** — on camera (video + audio), file `21.mp4`, about 30 s

Each class maps to a nutrition record: two hundred and forty-seven exactly, sixty-six through the nearest food, and seven left for the user to choose. Portions come from typical servings, or from the food's area against the plate, always with an uncertainty band. Glycaemic load uses published GI values, and where a dish has none, fixed rules borrow the value of its staple. That covers seventy-eight more foods.

**22 · The glucose estimate** — on camera (video + audio), file `22.mp4`, about 25 s

The glucose estimate is a one-compartment mass-balance model. Glucose from the meal appears over time, is cleared at a rate set by the person's condition, and is used faster by working muscle during activity. It's anchored to typical glucose tolerance results, and after three meals with before and after readings, it calibrates to the person's own response.

**23 · A grounded Meal Advisor** — on camera (video + audio), file `23.mp4`, about 31 s

The Meal Advisor is grounded by design. A rule engine writes the answer from the user's own data first. The local language model, Qwen two point five, only rewords it, and a validator checks every number and food name against the facts before anything is shown. If the check fails, the rule-based answer is used. On thirty-eight test questions, covering arithmetic, safety and prompt injection, every answer passed, with no unsupported claims.

**24 · Learning safely** — on camera (video + audio), file `24.mp4`, about 28 s

It also learns safely. A food the user names is stored as a fingerprint and matched by cosine similarity, so it's recognised next time without retraining. Photos are shared for training only with consent. Each one is screened for poisoning patterns, and a new model must pass a gate on a fixed test set, then run in shadow mode, before it can go live.

**25 · Tested and deployable** — on camera (video + audio), file `25.mp4`, about 22 s

Quality is tested end to end, against a real database and a real browser: sixty-four automated tests, plus an acceptance run from sign-up to saved meal, which also passes with no internet, and keeps every record across a restart. It deploys with one Docker Compose command on a CPU server.

## Close

**26 · MealSenseAI** — voice only (over the app demo), file `26.m4a`, about 16 s

Diabetes is managed one meal at a time, and most of those meals have no label. MealSenseAI puts the information on the plate, at the moment the choice is made. MealSenseAI. Understand your food. Make healthier choices.

About 10 minutes of speech at 138 words a minute.
