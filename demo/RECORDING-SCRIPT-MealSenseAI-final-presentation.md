# Recording script: MealSenseAI-final-presentation

Record every line as its own video, named by its number: `01.mp4`, `02.mp4` … (mp4 or mov, landscape).
"Full screen" lines are shown as you recorded them. "Corner" lines play your video small in the bottom-right
corner over the demo, so frame yourself centred, head and shoulders, against a plain background.
Same place, light and distance for every take. In corner lines, pause about a second before and after you speak:
the silence is trimmed automatically. Redo a line rather than editing it. Corner lines time the demo, so read
them at the pace you want the screen to move.

## Opening

**01 · The unlabelled plate** — on camera, full screen, file `01.mp4`, about 26 s

A packet of biscuits tells you exactly how much sugar is inside. A plate of chicken rice from a hawker stall tells you nothing. There's no label and no portion size, and the carbohydrate hides in the rice, the sauce and the drink on the side. So people guess. I built MealSenseAI to take the guessing out of it.

**02 · Why it matters** — on camera, full screen, file `02.mp4`, about 24 s

This matters. About one adult in twelve in Singapore lives with diabetes, and a national study put the yearly cost of diabetes to Singapore at about one billion dollars in 2010, rising to two and a half billion by 2050. Diabetes is managed one meal at a time, and most of those meals have no label.

**03 · What MealSenseAI is** — on camera, full screen, file `03.mp4`, about 41 s

MealSenseAI turns one photo of a meal into the foods, their portions and their nutrients, and then into meaning: the likely effect on blood sugar, the glycaemic load and a practical next step. Every estimate shows its range and where it came from, and nothing is saved until you confirm it. It's for anyone who wants to understand their food, and I start with people with Type 1 and Type 2 diabetes, where the need is sharpest. Logging is free, and the subscription is three ninety-nine a month. Let me show you the current version.

## Demo

**04 · Profile and dashboard** — on camera, shown in a corner over the demo, file `04.mp4`, about 22 s

This is Wei Ming, a fictional user with type two diabetes. His profile sets the context: his condition, his goals and a daily carbohydrate target, all optional, and health details are stored only with his consent. The dashboard shows today's calories and carbohydrate against those goals, and the last seven days.

**05 · Capture** — on camera, shown in a corner over the demo, file `05.mp4`, about 30 s

At lunch he takes a photo of his plate. When he taps Analyze, the photo goes through ten stages: checking the image, finding each food, naming it, estimating the portion, matching it to the nutrition table and working out what it means. Each stage shows what it did and how long it took. It all runs on an ordinary CPU, in well under a second, with no cloud service.

**06 · Review and correct** — on camera, shown in a corner over the demo, file `06.mp4`, about 49 s

Then he checks the result. Each food shows the model's top three guesses with their scores, and if the first one is wrong, one tap switches it. On my test set the right food is in the top three almost nine times in ten, so one tap fixes most mistakes. He can open Why to see how the portion and nutrients were estimated, rename a food, or enter the grams if he knows them. And if the model missed something, he drags a box around it on the photo. The app classifies just that region, offers its best guesses, and remembers his choice, so next time it recognises that food without retraining.

**07 · What the meal means** — on camera, shown in a corner over the demo, file `07.mp4`, about 30 s

Now the meaning. Key takeaways summarise the meal in plain words. The glucose impact shows a level and the glycaemic load. Where a local dish has no published glycaemic index, the app borrows the value of its main staple, for chicken rice that's white rice, and labels it as borrowed, so the estimate is honest about where it came from. The meal advisory lists practical tips, each with its source.

**08 · Try before eating** — on camera, shown in a corner over the demo, file `08.mp4`, about 30 s

He can try changes before he eats. In the portion simulator he drags the rice down to about two thirds and sees the carbohydrate, the glycaemic load and the estimated glucose curve come down. The activity what-if compares sitting at his desk with a fifteen-minute walk. For this meal, eating less rice lowers the estimated peak about ten times more than the walk does. Then he saves the meal.

**09 · Meal Advisor** — on camera, shown in a corner over the demo, file `09.mp4`, about 28 s

The Meal Advisor answers questions about his meals. Here he asks how his week went. The answer is built by rules from his own records and the food table, and each point shows its source. A small local language model may reword it, but a validator checks every number against the facts. If anything can't be checked, the plain rule answer is shown instead.

**10 · Trends** — on camera, shown in a corner over the demo, file `10.mp4`, about 8 s

Nutrition Insights shows his trends over seven and thirty days, so he can see patterns rather than single meals.

## Evaluation

**11 · How I evaluated it** — on camera, shown in a corner over the demo, file `11.mp4`, about 26 s

So how do I know it works? I ran eight experiments. Each has fixed inputs with known answers, a method, a saved result file and a number. Together they cover recognition of single foods and full plates, the advisor, text matching, the local language model, the glucose model and the full deployment, and any of them can be run again.

**12 · Data and training** — on camera, shown in a corner over the demo, file `12.mp4`, about 37 s

First, the data and the model. I used Food-101 and the Singapore dataset FoodSG-233, three hundred and ten thousand images. A checksum audit found two thousand groups of identical files, so I removed about forty-one hundred images with conflicting labels or duplicates, and no image appears in both training and test. I then trained EfficientNet-B0 in two stages on my own GPU: first a new head on a frozen backbone, then the last three blocks as well. Validation macro-F1 rose from fifty-eight to sixty-six percent.

**13 · Recognition results** — on camera, shown in a corner over the demo, file `13.mp4`, about 55 s

On forty-five thousand eight hundred test images it had never seen, the model's first guess is right seventy-one percent of the time, and the right food is in its top three eighty-six percent of the time. That gap is why the app always shows three choices. Results are similar for both datasets, slightly lower for the Singapore dishes. Per class, the median F1 is sixty-eight percent, and forty-five classes fall below fifty, mostly local noodle and rice dishes that look alike. The model's confidence also matches its accuracy to within about two percent. Below a score of point two its first guess is right only seventeen percent of the time, so the app doesn't add it; above point five it's right eighty-six percent of the time.

**14 · Several foods on a plate** — on camera, shown in a corner over the demo, file `14.mp4`, about 26 s

For plates with several foods, I tested a hundred plates holding two hundred and sixty-three foods. Detection found sixty-eight percent of them, and three quarters of what it found were real foods. On this plate it named the sushi, but left the pizza and the steak as unidentified, with pizza as its first guess. It asks rather than guesses.

**15 · Language and text** — on camera, shown in a corner over the demo, file `15.mp4`, about 43 s

For text, I compared the local language model with simple rules. The rules were better at reading meal descriptions, an F1 of zero point nine nine against zero point seven three, and at matching food names. A TF-IDF nearest-neighbour matcher did best of all: sixty-seven percent of held-out names, against twenty-three for the current lookup. The benchmark also found a real gap: the model's meal explanations were shown unchecked, and five of six contained numbers it had made up. I fixed that in version zero point thirteen point thirteen, and explanations now pass the same validator as the advisor.

**16 · Advisor, glucose model and quality** — on camera, shown in a corner over the demo, file `16.mp4`, about 26 s

The Meal Advisor passed all thirty-eight labelled test questions, including safety and prompt-injection tests, with no unsupported claims, in about twelve milliseconds. The glucose model, for chicken rice and teh tarik, shows the portion mattering far more than the walk. And the whole system passes sixty-five automated tests and all nine acceptance checks, including with the internet switched off.

## System design

**17 · Architecture** — on camera, shown in a corner over the demo, file `17.mp4`, about 41 s

Now the system design. Everything runs in containers on one CPU server. The browser talks only to nginx, which serves the app and passes requests to a FastAPI backend. The backend loads the detection and classification models once, together with the rules and the advisor, and stores its data in PostgreSQL; photos sit in a volume. The local language model runs beside it in Ollama. Compared with my proposal, I simplified where the measurements allowed: an analysis takes about a quarter of a second, so a job queue and a separate worker weren't needed.

**18 · The ten-stage pipeline** — on camera, shown in a corner over the demo, file `18.mp4`, about 20 s

Every photo follows the ten stages from my proposal: capture, pre-processing, detection, classification, portion, nutrition mapping, meal aggregation, AI contextualisation, recommendations and output. Each output is tagged as a model prediction, an estimate, guidance or the user's own input, so it's always clear which is which.

**19 · Grounded by design** — on camera, shown in a corner over the demo, file `19.mp4`, about 17 s

The advisor is grounded by design. Rules produce the facts, the language model only words them, and the validator decides what is shown. If the model is slow, offline or wrong, the user still gets a correct answer.

**20 · Learning safely** — on camera, shown in a corner over the demo, file `20.mp4`, about 27 s

It also learns safely. A food the user names is remembered straight away. Photos are shared for training only with consent, screened by eleven automatic checks, and reviewed by a person when flagged. A new model must match the current one on a fixed test set, do no worse on safety foods, and agree with it in shadow mode before it goes live.

**21 · Configuring the models** — on camera, shown in a corner over the demo, file `21.mp4`, about 24 s

And the models are configured in the admin area, without code changes: the recognition thresholds, backed by the calibration results; the personal-memory match, a cosine similarity of at least point seven; and the language model, Qwen 2.5 with one and a half billion parameters, at a temperature of point one, with time limits and versioned prompts.

## Close

**22 · Limits and next steps** — on camera, full screen, file `22.mp4`, about 24 s

There are limits. Similar local dishes still confuse the model. Portions from a photo carry a margin of up to fifty percent, and I haven't yet measured portion error against weighed food. The nutrition values still need verifying against an official source. My next step is a trial with real users, which will measure all three.

**23 · Close** — on camera, full screen, file `23.mp4`, about 13 s

MealSenseAI gives educational estimates, not medical advice. It puts the information on the plate, at the moment the choice is made. Understand your food. Make healthier choices. Thank you.

About 11 minutes of speech at 138 words a minute.
