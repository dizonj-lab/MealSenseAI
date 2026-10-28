# MealSenseAI — User guide

Open **http://localhost:8080**, or from a phone on the same Wi-Fi, `http://<computer-IP>:8080`. A demo account
(`demo@mealsense.ai` / `demo12345`) exists if the app was started with `./scripts/start.sh --demo`.

## 1. Register and onboard
1. **Create account** with your name, e-mail and a password (at least 8 characters).
2. **Onboarding (4 short steps, every field optional):**
   - **Personal:** age, sex, height, weight, activity level, diet preferences.
   - **Health:** tick the consent box to store health data, then set diabetes status, allergies and restrictions.
     Without consent, diabetes details are not saved.
   - **Diabetes context:** glucose unit (mmol/L or mg/dL), latest HbA1c, CGM use, known readings, targets given by
     your clinician. The app never sets targets itself.
   - **Goals:** carbohydrate or calorie awareness, weight management, balanced nutrition, diabetes-friendly choices,
     plus optional daily calorie, carbohydrate and protein goals.
3. You can change all of this later under **Health Profile**.

## 2. Capture a meal
1. Tap the camera button, then **Take photo** or **Upload** for the top view. A side view is optional.
2. Optionally describe the food (e.g. "chicken rice and kopi"), choose a reference object (plate or bowl), or add a
   serving note ("half plate", "2 pieces").
3. Tap **ANALYZE MEAL** and watch the 10 pipeline stages complete. The classifier takes well under a second on a CPU.

## 3. Review: confirm or override
Each food card shows:
- **Model prediction:** the top-3 candidates with raw model scores. The highlighted one is in use. **Tap another
  candidate to switch.** A "low confidence — please check" note means the top score was below 0.50.
- If the model was very unsure (top score below 0.20), no food is added automatically. A box asks **"Is it one of
  these?"**; tap the right one, or use **Add missing food**.
- **Food:** search the nutrition table if the right food is not among the candidates.
- **Portion:** enter grams if you know them. The value is then tagged **Your input**, otherwise **Estimate**, and
  the uncertainty band shrinks.
- **Remove** deletes a wrong item. **Add missing food** adds what the model missed: **Mark it on the photo** (drag a box
  around the food with a mouse, finger or pen; the model names what is inside) or **Search the food list**. An item
  without a box has **Show where it is on the photo**.
- "≈ *food name*" means the nutrition comes from the **closest available food** (a proxy). Correct it if you know better.

## 4. Nutrition and diabetes-aware insights
- **Potential Glucose Impact:** carbohydrate, sugar and fibre, glycaemic load when supported, and a
  LOW/MODERATE/HIGH/UNCERTAIN level. Based on food composition; not your personal glucose response.
- **Energy & Nutrition:** calories, macronutrient split, and share of your daily goals.
- **Meal composition:** the meal's calories and nutrients, where its energy comes from, each nutrient against your
  day (your goals, the WHO sodium limit, a fibre guideline; amber when the meal alone passes its share of a limit),
  what its carbohydrate is made of, and, for meals with several foods, which food contributes what.
- **Practical Recommendations** and **Meal advisory** (tagged *Unvalidated guidance*).
- **Forecast & what-if:** see how a walk, cycling, running or rowing session at a chosen time after the meal changes
  the relative glucose curve and energy use. Includes safety cautions and references.

## 5. Save, history and dashboard
- Choose breakfast, lunch, dinner or snack, then **Confirm & save meal**.
- **Meal History:** filter by date, see daily totals, open a meal to view or edit it (**Edit**), or delete it.
- **Dashboard:** today's totals, goal progress, 7-day calories, macro split and recent meals.
- **Nutrition Insights:** 7- and 30-day trends.
- **AI Model Insights:** which models are active (CPU or GPU), reported accuracy and its source, runtime parity
  evidence, and how often you corrected the model.

## 6. Helping improve food recognition (optional)
- When you name or correct a food, MealSenseAI remembers it for your account. In **Settings → Learning from your
  corrections** you can also share those corrected photo crops to train the next model: only the food region, never
  the whole photo, and without your name or email.
- Settings shows how many you shared, how many were accepted and how many are in review. Every shared crop is checked
  automatically and may be reviewed by a person before any model learns from it.
- Confirm your email (Settings → **Send the link**) so your shared photos can be used.
- Switching sharing off withdraws everything you shared from all future training sets.

## 7. For administrators
The **Admin** menu (admins only) holds training-data review, contributors, dataset versions, the model gate and model
updates, model settings, prompts and the audit log. See [ADMIN.md](ADMIN.md).

## Important
MealSenseAI gives **educational estimates**. It does not diagnose, predict your blood glucose, or replace advice from
your doctor, dietitian or diabetes care team. If you use insulin or sulfonylureas, follow your care plan around meals
and exercise.
