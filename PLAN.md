# Lift & Fuel build plan

First working goal: tell Zoro what you ate → confirm the food and portion → save the meal → see Today update.

Everything below serves that goal first. Workouts come after the meal loop works end to end. Treat milestones as checkpoints, not weekly deadlines.

## What Lift & Fuel does (v1)

Lift & Fuel is the app. Zoro is its chat assistant.

| Feature | What it does |
| --- | --- |
| Profile | Stores goal, calorie and protein targets, dietary preferences, equipment, training days, usual session length |
| Meal logging | Reads a food description, asks for missing portions, shows a meal card to confirm or edit |
| Today | Calories and protein logged against the user's targets, plus today's workout |
| Workouts | Builds a workout from a template, the user's equipment, and the time available |

Example:

> **You:** Zoro, I ate two eggs and 200 grams of cooked rice.
> **Zoro:** Here's my estimate. Save it? *(meal card: 2 large eggs, 100 g · 200 g white rice, cooked · ≈ 403 kcal · 18 g protein · Save / Edit / Discard)*
> **You:** Yes. I also only have 30 minutes to train today.
> **Zoro:** Saved. Here's a 30-minute version of today's workout. *(workout card · Use this / Discard)*

Numbers in the example are illustrative; the real ones come from `foods.db`.

## Screens

1. **Today**: calorie and protein progress against targets, list of today's meals, today's workout (planned / done / skipped).
2. **Chat**: conversation with Zoro. Meal and workout proposals appear as cards with buttons.
3. **History**: meals and workouts grouped by day. Edit and delete.
4. **Profile**: goal, targets, dietary preferences, equipment, training days, session length, workout template. "Load demo data" button.

## Data model

App database (SQLite in dev, Postgres when deployed):

- `profiles`: device_id (pk), display_name, goal (`lose` | `maintain` | `gain` | `strength`), calorie_target, protein_target_g, diet_prefs (json list), equipment (json list), training_days (json list of weekday numbers), session_minutes, template_id, timezone, created_at
- `meals`: id, device_id, eaten_at (UTC), local_date (from the user's timezone), label (`breakfast` | `lunch` | `dinner` | `snack` | null), source (`chat` | `manual`), created_at
- `meal_items`: id, meal_id, fdc_id (nullable), custom_food_id (nullable), food_name, portion_text (e.g. "2 large"), grams, kcal, protein_g, carbs_g, fat_g
- `custom_foods`: id, device_id, name, kcal_100g, protein_100g, carbs_100g, fat_100g, serving_name (nullable), serving_grams (nullable)
- `proposals`: id (uuid), device_id, kind (`meal` | `meal_edit` | `workout`), payload (json), status (`pending` | `confirmed` | `discarded`), prompt_version, created_at, resolved_at
- `workouts`: id, device_id, local_date, template_id, minutes_planned, status (`planned` | `done` | `skipped`), exercises (json), created_at
- `chat_messages`: id, device_id, role (`user` | `zoro`), text, proposal_id (nullable), created_at

Food reference database (`foods.db`, read-only, rebuilt from committed CSVs at startup if missing):

- `foods`: fdc_id, description, data_type, category, kcal_100g, protein_100g, carbs_100g, fat_100g
- `portions`: fdc_id, amount, unit_name, modifier, gram_weight
- `foods_fts`: FTS5 index over description
- `aliases`: phrase → fdc_id, loaded from `aliases.csv`

## Milestone 0: Skeleton

- Create the repo layout from CLAUDE.md.
- `GET /api/health` returns `{"ok": true}`.
- Vite app with the four routes and the navigation (bottom bar on phones, left rail on wider screens). Placeholder content is fine.
- `device.js` creates the device id; `api.js` sends it on every request.
- GitHub Actions workflow running `pytest` and `npm run build`.
- `.env.example` files, `.gitignore` covering `.env`, `*.db`, `backend/data/raw/`, `node_modules`, `.venv`.

**Done when**

- [ ] Backend and frontend run locally and the frontend shows the health check result.
- [ ] Navigation works at 375px and 1024px widths.
- [ ] CI is green on the first push.

## Milestone 1: Profile, Today, manual meals

- Profile form with backend validation (target ranges from CLAUDE.md). Timezone is taken from the browser and stored.
- Manual meal entry: food name, grams, kcal, protein typed by hand (food search replaces this in Milestone 2).
- `GET /api/today?date=YYYY-MM-DD` returns totals, targets, and the day's meals.
- Today screen: two progress bars (calories, protein), meals list.
- History: meals grouped by `local_date`, newest first; edit and delete.

**Done when**

- [ ] Set targets, add two meals, Today shows correct totals.
- [ ] Refresh keeps everything. Deleting a meal updates Today.
- [ ] Test: a meal at 23:30 local time counts toward that local day, not the UTC day.
- [ ] Test: a second device id cannot read or delete the first device's meals.

## Milestone 2: Food data

- Download the USDA FoodData Central "Foundation Foods" and "SR Legacy" CSV zips into `backend/data/raw/`. Data is public domain (CC0), no key needed for downloads.
- `scripts/build_food_data.py` writes `foods.csv` and `portions.csv`:
  - Nutrients: protein 1003, fat 1004, carbohydrate 1005, energy 1008. Foundation foods often lack 1008; fall back to 2047, then 2048. Confirm these ids against `nutrient.csv` before relying on them.
  - Portions from `food_portion.csv` joined with `measure_unit.csv`. Keep amount, unit name, modifier, and gram weight.
  - Skip foods with no energy value.
- On startup, the backend builds `foods.db` from the CSVs if it does not exist, including the FTS5 index.
- `aliases.csv`: about 60 hand-picked phrases for common foods (egg, rice, chicken breast, oats, banana, milk, bread, lentils, yogurt, peanut butter...) mapped to the right fdc_id. Aliases are checked before full-text search.
- `GET /api/foods/search?q=` returns the top 8 matches with their portions. Custom foods for this device are included.
- `services/portions.py`: (food, quantity, unit) → grams.
  - `g`, `kg`, `oz`, `lb` convert directly.
  - Household units (`large`, `slice`, `cup`, `tbsp`, ...) use the food's portion rows. Match on unit name or modifier, case-insensitive, singular/plural.
  - `ml` only if the food has a volume portion to derive density from; otherwise ask for grams.
  - If no rule applies, return "needs portion" instead of guessing.
- Manual entry becomes: search food → pick a portion or type grams → see the estimate → save.
- "My foods": add a custom food with per-100 g values. USDA data is US-centric and misses many home-cooked and regional dishes, so this matters.

**Done when**

- [ ] "egg" + "2 large" resolves to grams through the portion table, and the totals equal grams × the per-100 g values in `foods.db`.
- [ ] Unit tests for every conversion path, using small fixture CSVs (not the full dataset).
- [ ] A custom food can be logged and shows up in search.
- [ ] Search for "rice" lists cooked white rice in the top 3.

## Milestone 3: Connect Zoro

The meal loop through chat. This is the core of the project.

**Interpreter**

- `services/llm/base.py` defines `Interpreter.interpret(message, context) -> Interpretation`. `context` holds whether a proposal is pending and a short summary of it.
- Gemini implementation: structured JSON output with a schema, temperature 0, 15-second timeout, one retry if the JSON fails validation.
- Groq implementation behind the same interface, selected by `LLM_PROVIDER`.
- `Interpretation` is a list of actions (one message can hold more than one):
  - `log_meal`: items `[{food, quantity, unit}]` (quantity and unit may be null), optional meal label
  - `confirm_pending`, `discard_pending`
  - `correct`: changes to the pending proposal, or to the last saved meal if nothing is pending
  - `plan_workout`: minutes (nullable), focus (nullable). Handled in Milestone 4; until then Zoro says workouts are coming.
  - `out_of_scope`: medical, injury, or other topics Zoro shouldn't advise on
  - `chat`: short reply for anything else fitness- or food-related
- `prompts.py` holds the system prompt, 6 to 8 few-shot examples, and `PROMPT_VERSION`, which is saved on each proposal.

**Pipeline** (`POST /api/chat`)

1. Rate-limit by device id (`CHAT_LIMIT_PER_HOUR`).
2. Run `safety.py` keyword check first; if it matches, return the fixed reply and skip the LLM.
3. Interpret the message.
4. For each `log_meal` item: alias lookup, then FTS search (top 5). Convert the portion to grams. If the quantity is missing or can't be converted, mark the item "needs portion" and attach portion choices from `foods.db` (for example "1 cup (158 g)", "100 g").
5. Create a `meal` proposal and return it with Zoro's one-line reply.
6. A typed "yes" or "save it" maps to `confirm_pending` and does the same thing as the Save button.

**Cards**

- Meal card: one row per item (food name with a dropdown of the other matches, portion, grams, ≈ kcal, protein), totals, Save / Edit / Discard. Items that need a portion show quick-pick chips and the Save button stays disabled until every item has grams.
- Duplicate guard: if the same food and grams were saved in the last 15 minutes, the card says when, and asks before saving again.
- Correction: "actually it was 150 g of rice" updates the pending card, or opens an edit card for the last saved meal.

**When the model fails**

- Timeout, 429, or invalid JSON twice: Zoro says it couldn't read that one and shows the manual entry form with the message text in the search box. Chat never dead-ends.

**Evals**

- `evals/meal_cases.jsonl`: about 40 hand-written cases, each with the message and the expected actions, items, quantities, units, and acceptable fdc_ids. Cover: single item, several items, missing quantity, household units, typos, regional dish names, a correction, "yes" plus a new request in one message, an out-of-scope message.
- `evals/run_meal_evals.py` calls the real model and prints: intent accuracy, item count accuracy, food match rate, quantity/unit accuracy. Results are written to `evals/results/<date>.md` with the prompt version. Run by hand only; not in CI.

**Done when**

- [ ] The first working goal works end to end at phone width.
- [ ] "I had rice for lunch" produces a card asking how much, with portion chips.
- [ ] Confirming the same proposal twice (double tap, or button then "yes") saves one meal.
- [ ] With the API key removed, chat falls back to the manual form instead of erroring.
- [ ] A baseline eval run is saved. Look at the worst-scoring category, fix it once (prompt, aliases, or matching), and save a second run.

## Milestone 4: Workouts

- `scripts/curate_exercises.py` reads `exercises.json` from free-exercise-db and keeps a hand-written list of about 60 exercises. Adds two fields per exercise: `pattern` (squat, hinge, lunge, push_horizontal, push_vertical, pull_horizontal, pull_vertical, core, carry) and `seconds_per_set`.
- `workout_templates.json`: 3 or 4 templates, for example Full Body A, Full Body B, Upper/Lower, Bodyweight Quick. Each template is an ordered list of slots: pattern, sets, rep range per goal, rest seconds, priority.
- `services/workout_gen.py` takes (template, equipment, minutes, goal, date):
  - Fills each slot with an exercise the user's equipment allows. Rotates choices by date so the same template varies week to week, but the result is deterministic for a given date (testable).
  - Estimated time = warm-up 5 min + Σ sets × (seconds_per_set + rest).
  - Over the limit: drop the lowest-priority slots first, then cut sets down to a minimum of 2.
- Today shows the planned workout on training days with Done / Skip.
- Chat: "I only have 30 minutes" → `plan_workout` → workout card → "Use this" replaces today's planned workout.
- Templates are edited in the JSON file for v1. No template editor screen.

**Done when**

- [ ] 20, 30, 45, and 60 minute versions of the same template differ sensibly.
- [ ] Test: a bodyweight-only profile never gets an exercise that needs equipment.
- [ ] Test: estimated time ≤ requested minutes for every template at every length from 15 to 90 in steps of 5.
- [ ] Test: same inputs and date give the same workout.

## Milestone 5: Mobile experience and deploy

- `vite-plugin-pwa`: manifest (name "Lift & Fuel", green theme color, off-white background color, 192 and 512 px icons plus a maskable icon, apple-touch-icon), service worker that caches the app shell. Chat shows "You're offline" without network.
- Check layouts at 360, 390, 768, and 1024 px. Test add-to-home-screen on one Android phone and one iPhone or iPad.
- Add Alembic before switching to Postgres. Create the initial migration from the current models.
- Deploy:
  - Database: Neon free plan (Postgres). Don't use Render's free Postgres; it expires after 30 days.
  - API: Render free web service. It sleeps after 15 minutes idle and its disk is wiped on restart, which is why the app DB is Neon and `foods.db` is rebuilt from committed CSVs at startup.
  - Frontend: Render static site. CORS on the API allows only that origin.
- Cold start: if the first API call takes more than 3 seconds, the frontend shows "Starting the server. This can take up to a minute on the free plan."
- "Load demo data" on Profile seeds a week of meals and workouts for the current device, so a recruiter can see a filled-in app in one tap.

**Done when**

- [ ] The live URL installs to the home screen on Android and iOS and opens without browser chrome.
- [ ] Chrome DevTools → Application shows the manifest with no errors and an active service worker.
- [ ] A fresh device on the live site can log a meal through chat.

## Milestone 6: Portfolio

- README, in this order:
  1. What Lift & Fuel does, in three sentences, with one screenshot.
  2. Screenshots: Today, Chat with a meal card, workout card, History.
  3. How a message becomes a meal: message → interpretation JSON → food match → grams → card → confirm. One small diagram.
  4. Decisions and tradeoffs: why the model doesn't do math, why USDA data is local, why confirm-before-save, why no login.
  5. Eval results table (baseline vs after the fix) and what changed.
  6. Known limitations.
  7. Run it locally.
  8. Data sources and credits: "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central. fdc.nal.usda.gov." and yuhonas/free-exercise-db.
  9. Privacy note: messages go to the Gemini API free tier; don't enter personal health information.
- A 60 to 90 second demo video: the first working goal, the 30-minute workout, installing to the home screen.
- Write the README and resume bullets in your own words, using the real eval numbers.

## Test checklist

- [ ] Missing portion ("I had rice")
- [ ] Unit the food has no portion for ("a cup of chicken")
- [ ] Wrong match corrected by picking another option on the card
- [ ] Same proposal confirmed twice
- [ ] Duplicate meal within 15 minutes
- [ ] Correction to a pending card and to the last saved meal
- [ ] Meal near midnight in the user's timezone
- [ ] LLM returns invalid JSON twice
- [ ] LLM returns 429 or times out
- [ ] Out-of-scope message never reaches the LLM and never produces a workout
- [ ] Device isolation (one device can't see another's data)
- [ ] Target validation at the range edges
- [ ] Workout time limit and equipment filter

## Later (not in v1)

Food-photo recognition, voice chat, smartwatch sync, notifications, grocery lists, barcode scanning, branded foods through the USDA API, Canadian Nutrient File as a second food source, accounts and login, dark mode, a template editor screen.
