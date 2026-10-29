# Lift & Fuel

Lift & Fuel is a small fitness and food-logging app with a chat assistant named Zoro, built as one responsive web app that installs to a phone or tablet home screen (PWA). The user tells Zoro what they ate or how much time they have to train. Zoro answers with a card (a proposed meal entry or a proposed workout). Nothing is saved until the user confirms the card.

The milestone plan is in PLAN.md. Work on one milestone at a time and stop when its "Done when" list passes.

## Stack

- Frontend: React + Vite, JavaScript, plain CSS (one `global.css` with CSS variables, plus one CSS file per component). React Router for the four screens. `vite-plugin-pwa` for the manifest and service worker. No UI kit, no Tailwind, no state library.
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, httpx, pytest.
- App database: SQLite in development, Postgres (Neon free plan) when deployed. Same code, switched by `DATABASE_URL`.
- Food reference data: a read-only SQLite file, `backend/data/foods.db`, built from the USDA FoodData Central download files (Foundation Foods + SR Legacy). The app does not call the live USDA API.
- Exercise data: a hand-picked subset of `yuhonas/free-exercise-db` (public domain), stored in `backend/data/exercises.json`.
- AI: Google Gemini API, free tier, a Flash-class model. The model name comes from `GEMINI_MODEL` so it can change without code changes. The provider sits behind a small interface so Groq (also free tier) can be swapped in with `LLM_PROVIDER=groq`.

## The core rule

The model reads text. Python does every number.

- The LLM returns structured JSON only: intents, food phrases, quantities, units, minutes available. It never returns calories, protein, or grams.
- Python matches foods in `foods.db`, converts portions to grams, calculates totals, and builds workouts from templates.
- Nothing is written to the app database until the user confirms a proposal. Each proposal has an id; confirming the same id twice saves once.
- Nutrition values are copied into `meal_items` when a meal is saved, so history never changes if `foods.db` is rebuilt.

## Repo layout

```
lift-and-fuel/
  CLAUDE.md
  PLAN.md
  README.md
  .github/workflows/ci.yml
  backend/
    app/
      main.py            # FastAPI app, CORS, routers
      config.py          # settings from env
      db.py              # engine/session for the app DB
      models.py          # SQLAlchemy tables
      schemas.py         # Pydantic request/response models
      deps.py            # device id dependency, rate limit
      routers/           # profile, meals, foods, chat, workouts, today
      services/
        food_search.py   # alias lookup + FTS5 search on foods.db
        portions.py      # (food, quantity, unit) -> grams
        nutrition.py     # grams -> kcal/protein/carbs/fat, day totals
        proposals.py     # create / confirm / discard / edit
        workout_gen.py   # template + equipment + minutes -> workout
        safety.py        # out-of-scope detection, fixed replies
        llm/
          base.py        # Interpreter interface
          gemini.py
          groq.py
          prompts.py     # system prompt + few-shot examples, PROMPT_VERSION
    data/
      foods.csv          # trimmed USDA data (committed)
      portions.csv       # trimmed USDA portions (committed)
      aliases.csv        # hand-written: common phrase -> fdc_id
      exercises.json     # curated exercises (committed)
      workout_templates.json
      raw/               # USDA zip contents (gitignored)
    scripts/
      build_food_data.py # raw USDA CSVs -> foods.csv, portions.csv
      curate_exercises.py
    evals/
      meal_cases.jsonl
      run_meal_evals.py
      results/
    tests/
    requirements.txt
    .env.example
  frontend/
    src/
      main.jsx
      App.jsx
      api.js             # fetch wrapper, adds X-Device-Id
      device.js          # create/read device id
      pages/             # Today, Chat, History, Profile
      components/        # BottomNav, MealCard, WorkoutCard, ProgressBar, ...
      styles/global.css
    public/icons/
    .env.example
```

## Commands

```
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_food_data.py      # only when raw USDA files change
uvicorn app.main:app --reload
pytest
python -m evals.run_meal_evals         # uses real API quota, run by hand

# frontend
cd frontend
npm install
npm run dev
npm run build
```

## Environment

`backend/.env` is never committed. Keep `backend/.env.example` in sync.

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=
GROQ_API_KEY=
GROQ_MODEL=
DATABASE_URL=sqlite:///./liftfuel.db
FRONTEND_ORIGIN=http://localhost:5173
CHAT_LIMIT_PER_HOUR=40
```

`frontend/.env`: `VITE_API_URL=http://localhost:8000`

API keys live only on the backend. The frontend never calls Gemini, Groq, or any other third-party API.

## Users (no login in v1)

On first load the frontend creates a random UUID, keeps it in localStorage, and sends it as `X-Device-Id` on every request. The backend creates a profile for an unknown id. Every query is scoped by device id. No passwords, no emails. (A header is used instead of a cookie because the frontend and API run on different domains when deployed.)

## Design rules

The app should look like a tool someone designed on purpose, not a template.

- Colors (CSS variables in `global.css`):
  - `--bg: #F7F6F2` off-white page
  - `--surface: #FFFFFF` cards
  - `--text: #1D1D1B`
  - `--muted: #6B6B66`
  - `--border: #E3E1DA`
  - `--accent: #2E7D4F` the only accent color
  - `--accent-soft: #E7F0EA`
  - `--danger: #B3261E` delete actions only
- No purple anywhere. No gradients, glassmorphism, glows, or shadows heavier than `0 1px 2px rgba(0,0,0,.06)`.
- Type: system font stack (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`). `font-variant-numeric: tabular-nums` on every number. Sizes 13 / 15 / 17 / 22 / 28 px.
- Cards: white surface, 1px border, 8px radius, 16px padding. Food entries and workout suggestions in chat are cards, not chat bubbles.
- Layout: bottom navigation under 768px, left rail at 768px and wider. Content max width 640px. Tap targets at least 44px. Respect iOS safe-area insets.
- Icons: inline SVG or `lucide-react`, outline style, 20px. No emoji in the UI. No sparkle or magic-wand "AI" icons.
- Copy: short and literal. Screen names are Today, Chat, History, Profile. No marketing words (unlock, supercharge, seamless, journey, empower, elevate). Zoro replies in one or two plain sentences, no emoji, at most one exclamation mark per conversation.
- Nutrition numbers are shown as estimates ("≈ 412 kcal") and every value on a card can be edited before saving.

## Code style

- Write code the way a careful student engineer would: small functions, clear names, no speculative abstractions. The LLM provider interface is the only base class.
- Comments explain why, never what. No banner comments, no docstrings that repeat the function name.
- No dead code, no commented-out code, no scattered TODOs. Deferred work goes in PLAN.md under "Later".
- Commit after each working step with a short, plain message, for example `add portion conversion from food_portion units`. No emoji, no words like "comprehensive" or "enhance".
- Do not add a dependency that is not listed here without saying why in the milestone summary.

## Testing

- Backend tests use pytest and must pass with no network and no API keys. The LLM is always mocked in tests.
- When a bug is found, add a test that reproduces it before fixing it.
- Required cases are listed in PLAN.md under "Test checklist".
- CI (GitHub Actions) runs `pytest` and `npm run build` on every push.

## Safety and scope

- Lift & Fuel is a fitness and food-logging app, not a medical tool. If a message mentions injury, pain, illness, medication, pregnancy, or disordered eating, Zoro gives no advice for that message. It replies with a short fixed message suggesting a doctor, physiotherapist, or other qualified professional, and does not generate a workout from that message. The fixed messages live in `services/safety.py`.
- Calorie target must be 1,200 to 5,000 kcal. Protein target must be 30 to 300 g. Validate on the backend and in the form.
- The Chat screen shows one line under the input: messages are processed by Google's Gemini API, so don't include personal health details.

## How to work

- At the start of a milestone, read PLAN.md and list the files you plan to create or change before writing code.
- Finish one milestone, run the tests and the frontend build, then stop and summarize: what changed, how to try it, and anything left open.
- If something is not covered here, pick the simplest option and mention it in the summary.
- Check current docs (Gemini structured output, vite-plugin-pwa, USDA download file format) instead of relying on memory. These change.
