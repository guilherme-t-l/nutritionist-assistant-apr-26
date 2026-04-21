# Development Plan — Nutritionist AI Agent

Five phases, smallest first. Each phase ends with something you can run and show someone.

You don't need to understand the later phases yet. Focus on Phase 0 and Phase 1. The rest is there so you can see where we're going.

---

## The big picture in one paragraph

A **backend** (Python) receives requests from a **frontend**, turns them into a prompt, sends that prompt to an **LLM** (Gemini, free tier), and returns the reply. In Phase 3 we give the LLM **tools** — specifically, the ability to look up real food data in a Brazilian database. In Phase 4 we build **evals** — automated tests that measure *quality* of the LLM's answers, not just whether the code runs.

One rule: the code that talks to Gemini lives in exactly one file (`agent/llm.py`). If we ever want to swap Gemini for OpenAI or Claude, that file is the only one that changes.

---

## Phase 0 — Get a blank app running &nbsp;·&nbsp; ✅ Done

**Goal:** a Python web server running on your laptop that says "ok" when you visit a URL. Nothing more.

**Why this first:** you can't learn on code you can't run. Phase 0 exists so every later phase has something to add *to*.

**Steps:**

1. Install `uv` (Python's modern package manager — think npm for Python).
2. Run `uv init` in the project folder. This creates a `pyproject.toml` — the file that lists which libraries we depend on.
3. Add these libraries, with a one-line reason next to each:
   - `fastapi` — the web framework (handles HTTP requests)
   - `uvicorn` — runs the FastAPI app
   - `pydantic` — validates data going in and out
   - `python-dotenv` — loads API keys from a `.env` file
   - `pytest` — test runner
   - `httpx` — used to call external APIs and also by tests
4. Create `src/app/main.py` with one endpoint: `GET /health` returns `{"status": "ok"}`.
5. Run `uvicorn src.app.main:app --reload` and open `http://localhost:8000/health` in a browser.
6. Create `tests/test_health.py` with one test that calls `/health` and asserts it returns 200.
7. Create `.env` with `GEMINI_API_KEY=your-key-here`. Add `.env` to `.gitignore` so it's never committed.

**After Phase 0 your folder looks like this:**

```
nutri-assistant/                  ← the whole project lives here
├── pyproject.toml                ← list of Python libraries we depend on
├── .env                          ← secrets like GEMINI_API_KEY (never commit)
├── .gitignore                    ← tells git which files to skip (incl. .env)
├── src/                          ← all backend Python code lives under src/
│   └── app/                      ← the FastAPI web application
│       └── main.py               ← creates the app, defines GET /health
└── tests/                        ← automated tests live here
    └── test_health.py            ← first test: asserts /health returns 200
```

**How you know it works:** `/health` returns `{"status": "ok"}` in the browser, and `pytest` prints `1 passed`.

---

## Phase 1 — First working agent &nbsp;·&nbsp; ✅ Done

**Goal:** fill out a form (your goal, allergies, calorie target, cuisine preference) → get a meal plan back as structured JSON → chat to refine it ("make lunch lighter", "more Bahian food").

**What we're actually building, in plain words:**

- A form page.
- When you submit it, Python builds a message that says to Gemini: *"You are a nutritionist. The user wants X, is allergic to Y, targets Z calories. Reply with a meal plan in this exact JSON shape."*
- Gemini's reply is checked against that shape. Malformed replies are rejected.
- A session ID is stored in a cookie so follow-up messages remember the earlier turns.

**New files this phase adds and what each one is for:**

| File | What lives in it |
|---|---|
| `agent/schemas.py` | The shapes of a `UserProfile`, a `Food`, a `Meal`, and a `MealPlan`. This is the contract everyone agrees on. Meal macros are *computed* from foods so the LLM cannot claim "500 kcal" while the ingredients add up to 700. |
| `agent/llm.py` | The one function that talks to Gemini (`GeminiLLM.chat`). Swap-provider-here file. Also defines the `LLM` Protocol that lets tests plug in a `FakeLLM`. |
| `agent/prompts.py` | Turns a `UserProfile` into the text instructions we send to the LLM. |
| `agent/session.py` | A Python dictionary that remembers each user's conversation history, keyed by session ID. |
| `src/app/routes/plan.py` | The `/plan` endpoint. Profile in → first `MealPlan` out + a `session_id`. |
| `src/app/routes/chat.py` | The `/chat` endpoint. Receives a user message, calls the agent, returns the reply. |
| `src/app/dependencies.py` | **The seam.** Two tiny functions (`get_llm`, `get_session_store`) that FastAPI injects into routes. Tests override these to swap in a `FakeLLM` and a fresh in-memory store — no monkey-patching, no network. Phase 2 adds tool providers here too. |
| `src/app/templates/onboarding.html` | The form page the user sees first + the inline JS that calls `/plan` then `/chat`. |
| `tests/conftest.py` | Shared pytest fixtures: `FakeLLM` (records calls, returns a canned plan) and a `TestClient` with DI overrides wired. Reused by `test_plan.py` and `test_chat.py`. |

**Steps (in order):**

1. Write `schemas.py` first. No LLM yet — just Pydantic classes and a unit test. This forces you to decide what a "meal plan" *is* before an AI hands you one.
2. Write `agent/llm.py` with a `chat(messages, *, system, response_schema)` method on a `GeminiLLM` class, plus an `LLM` Protocol so tests can stub it. `response_schema` pins Gemini to structured JSON that parses cleanly into a `MealPlan` — no prompt-engineering-the-braces.
3. Write `prompts.py` — plain functions that take a `UserProfile` and return strings. Unit-testable without any network.
4. Add `src/app/dependencies.py` with `get_llm` and `get_session_store` providers. Every route imports from here, tests override here.
5. Wire 1+2+3+4 together in a `POST /plan` endpoint. No conversation yet, just: profile in, meal plan out.
6. Add `session.py` and a `POST /chat` endpoint that appends each turn to the session's history.
7. Add `tests/conftest.py` with a `FakeLLM` fixture, then write end-to-end tests for `/plan` and `/chat` that never touch the real Gemini API.
8. Add the HTML form (served at `GET /`). Submit it, chat with the result.

**After Phase 1 your folder looks like this:**

```
nutri-assistant/
├── pyproject.toml                ← dependency list (now also has google-genai + jinja2)
├── .env                          ← secrets (unchanged)
├── .gitignore                    ← unchanged
├── src/                          ← backend Python code (HTTP layer only)
│   └── app/                      ← the FastAPI app
│       ├── main.py               ← app entry point, wires routes + serves /
│       ├── dependencies.py       ← DI providers: get_llm, get_session_store (tests override these)
│       ├── routes/               ← one file per group of endpoints
│       │   ├── plan.py           ← POST /plan — profile in, meal plan out (one-shot)
│       │   └── chat.py           ← POST /chat — multi-turn refinement
│       └── templates/            ← HTML pages served to the browser
│           └── onboarding.html   ← the form + inline JS that calls /plan and /chat
├── agent/                        ← core agent logic (zero HTTP code here)
│   ├── schemas.py                ← Pydantic shapes: UserProfile, Food, Meal, MealPlan
│   ├── llm.py                    ← the ONLY file that talks to Gemini (+ the LLM Protocol)
│   ├── prompts.py                ← builds the system prompt from a UserProfile
│   └── session.py                ← in-memory store of each user's chat history
└── tests/                        ← mirrors the code layout above
    ├── conftest.py               ← shared fixtures: FakeLLM + TestClient w/ DI overrides
    ├── test_health.py            ← Phase 0 health check (still passing)
    ├── test_schemas.py           ← validates Pydantic classes with good/bad input
    ├── test_prompts.py           ← pure-function tests on build_system_prompt
    ├── test_plan.py              ← end-to-end /plan test with a fake LLM
    └── test_chat.py              ← end-to-end /chat test (asserts full history is forwarded)
```

**How you know it works:** you fill the form, get a coherent meal plan back, then say *"replace breakfast with something lighter"* and see the plan actually change in the next turn.

---

## Phase 1.5 — Richer user profile &nbsp;·&nbsp; ⏭ Next

**Goal:** expand `UserProfile` so the agent has enough context to produce genuinely personalized plans — multiple cuisines, flavor preferences, full macro targets, disliked-but-not-dangerous ingredients, and a meal count that actually shapes the response.

**Why this before Phase 2:** once the agent starts calling real food databases it will generate plans against whatever profile we give it. If the profile is thin, the output is thin — no tool-calling loop fixes that. Fixing the inputs now pays off for every phase after.

**What we're actually building, in plain words:**

- The form grows: users tick several cuisines (Bahian + Japanese), several flavor profiles (savory + spicy), list ingredients they simply don't like (separate from the ones that would send them to the ER), and set real macro targets — not just calories.
- They also pick how many meals they eat per day. A "3 meals" person gets three meals. A "5 meals" person gets five. `MealPlan` stops hardcoding three named meals and becomes an ordered list.
- The prompt gets richer and — crucially — splits into two distinct rules: *"these are safety constraints, never include them"* for allergies, and *"these are strong preferences, avoid them"* for dislikes. One line each, not one merged list.
- No new endpoints, no new agent files. The shape of the data changes; everything downstream (`/plan`, `/chat`, the LLM call, the session store) keeps working because it already flows typed objects, not bespoke fields.

**Changed files this phase and what changes in each:**

| File | What changes |
|---|---|
| `agent/schemas.py` | `UserProfile` gains `cuisine_preferences: list[str]` (replaces `cuisine_preference`), `flavor_profiles: list[Literal[...]]`, optional `protein_g_target` / `carbs_g_target` / `fat_g_target`, `disliked_ingredients: list[str]`, and `meals_per_day: int`. `MealPlan` becomes `meals: list[Meal]` (ordered) instead of fixed `breakfast`/`lunch`/`dinner`/`snacks`; `total_calories` sums over that list. |
| `agent/prompts.py` | `build_system_prompt` renders the new fields. Allergies and dislikes are emitted as two distinct rules so the LLM treats one as safety and one as preference. Meal count and macro targets are stated explicitly. |
| `src/app/templates/onboarding.html` | The form grows matching inputs: multi-select checkboxes for cuisines and flavor profiles, optional number fields for protein/carbs/fat, a free-text list for dislikes, and a small integer input for meals per day. The inline JS that builds the request body is updated to the new `UserProfile` shape. |
| `tests/test_schemas.py` | New cases: `meals_per_day` is a positive int, `flavor_profiles` only accepts the allowed literals, dislikes and allergies stay as separate lists, macro targets are optional but reject negatives, `MealPlan` accepts a variable-length `meals` list. |
| `tests/test_prompts.py` | Asserts the prompt mentions cuisines *plural*, lists dislikes separately from allergies, includes macro targets when set and omits them when not, and states the meal count. |
| `tests/test_plan.py` | Sends the richer profile and asserts the returned plan has `len(plan.meals) == profile.meals_per_day`. |

**Seam to respect:** no new files outside this list. No new route, no new agent module, no changes to `dependencies.py`, `llm.py`, `session.py`, `routes/plan.py`, or `routes/chat.py`. If a change wants to live somewhere else, that's a signal this phase is doing too much.

**Steps (in order):**

1. Edit `agent/schemas.py` first. Add the new `UserProfile` fields and flip `MealPlan` to `meals: list[Meal]`. Rewrite `total_calories` to sum over that list.
2. Update `tests/test_schemas.py` for the new validation cases. Run them red, make them green.
3. Update `agent/prompts.py` to render the new fields, keeping the safety-vs-preference split crisp in the wording.
4. Update `tests/test_prompts.py` to lock that wording in.
5. Update `src/app/templates/onboarding.html`: add the new controls and update the inline JS that builds the JSON body so it matches the new `UserProfile` shape.
6. Update `tests/test_plan.py` to send the richer profile through `/plan` and assert the plan has the expected number of meals.
7. Run the app, fill the real form, sanity-check that a 5-meal Bahian+Japanese savory+umami plan comes back looking like something a real person would eat.

**After Phase 1.5 your folder looks like this** (only changes from Phase 1 shown — no new files, only edits):

```
nutri-assistant/
├── agent/
│   ├── schemas.py                ← CHANGED: richer UserProfile; MealPlan is now a list of meals
│   ├── prompts.py                ← CHANGED: renders new fields; splits allergies vs dislikes
│   ├── llm.py                    ← unchanged
│   └── session.py                ← unchanged
├── src/app/
│   ├── templates/
│   │   └── onboarding.html       ← CHANGED: multi-cuisine, flavors, macros, dislikes, meal count
│   ├── routes/                   ← unchanged (plan.py, chat.py)
│   └── dependencies.py           ← unchanged
└── tests/
    ├── test_schemas.py           ← CHANGED: covers the new fields and their constraints
    ├── test_prompts.py           ← CHANGED: asserts dislikes vs allergies are distinct in the prompt
    └── test_plan.py              ← CHANGED: richer profile in, correct meal count out
```

**How you know it works:** you fill the form picking Bahian *and* Japanese, tick savory + umami, set 2500 kcal / 180g protein, put "cilantro" in dislikes and "shellfish" in allergies, and ask for 5 meals — the returned plan has exactly 5 meals, no shellfish *at all*, no cilantro *in practice*, and reads like something a person from Bahia who also likes Japanese food would actually eat.

---

## Phase 2 — Real UI &nbsp;·&nbsp; ⏭ Next

**Goal:** chat on the left, live meal-plan card on the right, looks like a real product.

Up to now the UI was a plain HTML form. Here we replace it with a small React app (a proper frontend). Everything in `agent/` and `src/app/routes/` keeps working unchanged — the new frontend just calls the same endpoints.

**After Phase 2 your folder looks like this** (only changes shown):

```
nutri-assistant/
├── ...                           ← all Python code unchanged
└── frontend/                     ← NEW: React app (totally separate from Python)
    ├── package.json              ← JS dependency list (npm's pyproject.toml)
    ├── index.html                ← entry HTML, mounts the React app
    └── src/                      ← React components live here
        ├── ChatPane.tsx          ← left side: the chat UI
        └── MealPlanPane.tsx      ← right side: the live meal-plan card
```

**How you know it works:** it looks good enough that you'd show it to a friend without caveats.

(If React feels like too big a detour when we get here, we can stay in HTML/HTMX instead. We'll decide at the start of this phase.)

---

## Phase 3 — Measure whether the agent is actually any good &nbsp;·&nbsp; ⏭ Planned

**Goal:** answer *"did my last prompt change make things better or worse?"* with numbers, not vibes — *before* we add the next big piece of complexity (tools), so we can tell whether that piece actually helped.

**Why this first, before 3.5 and 4:** without a measurement system in place, every later change is a leap of faith — you'd believe the refine loop (3.5) helps because it "should," and you'd believe tools (4) help because they "should." Evals first means you get a *rough baseline* on the simplest possible agent, then each subsequent phase has to earn its place by moving the numbers. That's the difference between *engineering* and *guessing*.

**Honest expectation for the baseline:** scores here will look mediocre. The agent has no tools (it's guessing calorie counts per food) and no refine loop (it's not even checking its own totals). That's the *point* — it's the floor, not the ceiling. Phase 3.5 and Phase 4 will each move numbers up measurably.

**New pieces:**

- Every LLM call is saved to a small SQLite database (`traces.db`) — inputs, outputs, timestamps. (Phase 3.5 adds refine-loop iteration counts to the same schema; Phase 4 adds tool-call rows.)
- A new `evals/` folder with:
  - 10–20 synthetic user profiles covering tricky cases (celiac + vegetarian, multiple allergies, strict calorie targets, regional cuisine, high-protein with no meat).
  - A script that runs the agent against each profile and scores the result on four metrics:
    - **JSON valid** — does the reply parse as a `MealPlan`?
    - **Allergen leak** — does the plan contain any ingredient the user asked to avoid?
    - **Calorie & macro accuracy** — does the plan's actual total (summed from its foods) land within ±5% of the calorie target and ±10% of each macro target? Self-contained math inside the metric file; Phase 3.5 will add a runtime version of this logic for the refine loop.
    - **Cuisine relevance** — a second Gemini call rates "how Brazilian is this plan?" 1 to 5.

**After Phase 3 your folder looks like this** (only changes from Phase 2 shown):

```
nutri-assistant/
├── traces.db                     ← NEW: SQLite file, one row per LLM call
├── agent/
│   ├── ...                       ← earlier agent files unchanged
│   └── tracing.py                ← NEW: writes rows to traces.db
└── evals/                        ← NEW folder: measuring the agent's quality
    ├── runner.py                 ← runs all profiles through the agent, scores each
    ├── datasets/                 ← inputs we feed the agent during evals
    │   └── profiles.json         ← ~15 synthetic user profiles (hard cases)
    └── metrics/                  ← one file per quality metric
        ├── json_valid.py         ← does the reply parse as a MealPlan?
        ├── allergen_leak.py      ← does the plan mention a forbidden ingredient?
        ├── target_accuracy.py    ← sums plan totals, reports % within tolerance
        └── cuisine_relevance.py  ← second LLM call: "how Brazilian is this?"
```

**How you know it works:** you tweak one sentence in `prompts.py`, run `python -m evals.runner`, and within ~2 minutes see a table showing which metric went up, which went down, and on which profiles. You save the baseline scores — they're what Phases 3.5 and 4 will each be measured against.

---

## Phase 3.5 — Self-check loop: the agent verifies its own numbers &nbsp;·&nbsp; ⏭ Planned

**Goal:** the agent stops replying with plans that miss the user's calorie and macro targets. Before the response ever leaves the server, Python checks the plan's actual totals against the profile. If they're off, the agent is asked to fix it — and it keeps being asked, up to a cap, until it's within tolerance or we give up and flag it.

**Why this between Phase 3 and Phase 4:** Phase 3's evals just gave you a rough baseline — likely a lot of off-target plans. The refine loop is the first *intervention*: add it, re-run evals, watch `target_accuracy` jump. This is the phase where you get to say "the loop improved calorie-within-tolerance from 35% to 80%" with numbers on a page. Separately, building the loop *before* tools means when real food data arrives in Phase 4, the verification mechanism is already debugged — tools and refine get measured independently, not as a bundle.

**What we're actually building, in plain words:**

- After the LLM returns a `MealPlan`, Python does two things: (1) computes the actual `total_calories` and total macros by summing the foods in the plan, and (2) compares those totals to the user's `calorie_target` and macro targets from their profile.
- If the deltas are inside tolerance (calories within ±5%, each macro within ±10% when the target is set), the plan is returned as-is.
- If they're outside tolerance, the agent builds a short correction message — *"your plan totals 2180 kcal but the target is 2500 (short by 320). Protein is 160 g vs 180 g target. Return the full `MealPlan` adjusted to hit these numbers."* — appends it to the conversation, and asks the LLM again.
- This loops at most **3 times** (configurable). If the third attempt is still off, we return the closest attempt and include a warning field in the response so the UI can show it. We do *not* loop forever — cost and latency would blow up.
- The same loop wraps `/chat` responses whenever the turn produces a new `MealPlan`, so adaptations can't silently drift off-target either.

**New and changed files this phase and what each does:**

| File | What lives in it / what changes |
|---|---|
| `agent/validators.py` (NEW) | Pure functions. `compute_plan_totals(plan) -> PlanTotals` sums calories and macros across `plan.meals`. `check_targets(totals, profile, tolerances) -> ValidationReport` returns a structured result: which targets are met, which are off, by how much. No LLM calls, no IO — fully unit-testable. The eval metric `target_accuracy.py` from Phase 3 can optionally be refactored to import from here, but doesn't have to be. |
| `agent/refine.py` (NEW) | The loop. One function: `refine_until_on_target(llm, messages, profile, initial_plan, *, max_iterations=3) -> RefineResult`. Each iteration: validate → if on-target, stop; else append a correction turn to `messages`, call `llm.chat` with the same `response_schema=MealPlan`, re-validate. Returns the final plan plus metadata (iterations used, final report, converged y/n). |
| `agent/prompts.py` (CHANGED) | Adds `build_refinement_prompt(report: ValidationReport) -> str` — turns the diff into a terse instruction to the LLM. Kept as a pure function so `test_prompts.py` can lock the wording. |
| `agent/schemas.py` (CHANGED) | Adds two small models: `ValidationReport` (per-metric status and deltas) and `RefineResult` (final plan, iterations, converged flag, last report). No changes to `UserProfile` or `MealPlan`. |
| `agent/tracing.py` (CHANGED) | Records refine-loop iteration count and converged flag alongside each request's trace row, so evals can see *why* scores changed. |
| `src/app/routes/plan.py` (CHANGED) | After the first `llm.chat` call, wrap the result with `refine_until_on_target`. Response body gains an optional `warnings` field populated when `converged` is false. |
| `src/app/routes/chat.py` (CHANGED) | Same treatment: if the turn's reply includes a new `MealPlan`, run it through `refine_until_on_target` before responding. |
| `src/app/dependencies.py` (CHANGED) | Adds `get_refinement_config` (tolerances + `max_iterations`) as a DI provider. Tests override it to force a loose or strict regime; production uses the defaults. |
| `tests/test_validators.py` (NEW) | Pure tests: exact targets pass; 5.001% over fails on calories; unset macro targets are skipped; negative deltas (over-target) are reported the same as positive ones. |
| `tests/test_refine.py` (NEW) | Uses a `FakeLLM` scripted to return an off-target plan first, then an on-target one. Asserts: loop stops after 2 iterations, `converged=True`, the final plan is the corrected one. A second test scripts three off-target plans and asserts `converged=False`, `iterations=3`, the best attempt is returned. |
| `tests/test_prompts.py` (CHANGED) | New case: `build_refinement_prompt` mentions the actual deltas and the word "MealPlan". |
| `tests/test_plan.py` and `tests/test_chat.py` (CHANGED) | The existing FakeLLM is extended so the first scripted response is deliberately low on calories; tests assert the refine loop fires and the final response matches target. |

**Seam to respect:** no changes to `agent/llm.py` (it already accepts a message list, so the loop just grows the list), no changes to `agent/session.py` (the correction turns are not persisted into session history — they're internal to a single request). If a change wants to live in `llm.py` or `session.py`, that's a signal this phase is leaking past the seam.

**Why this shape over obvious alternatives (one sentence each):**

- *"Just ask the LLM to be more accurate in the system prompt"* — tried in spirit in Phase 1.5; works sometimes, fails silently when it doesn't. Verification in Python is cheap and deterministic.
- *"Have the LLM self-critique in a single call"* — mixes two jobs (generate, judge) in one turn and makes failures hard to debug. Separating them means we can log exactly when and why a correction happened.
- *"Loop until converged, no cap"* — one bad profile could spend $$ and minutes. A hard cap with a warning is the grown-up choice.

**How data flows through one refined request:**

1. `POST /plan` → builds prompt → `llm.chat()` returns `MealPlan #1`.
2. `refine.refine_until_on_target` → `validators.compute_plan_totals(plan1)` → `validators.check_targets(totals, profile, tolerances)`.
3. Report says calories are 320 short → `prompts.build_refinement_prompt(report)` produces the correction text → appended to `messages` → `llm.chat()` again → `MealPlan #2`.
4. Re-validate. If on-target, return; else repeat up to `max_iterations`.
5. Route returns the final plan, plus a `warnings` list if we gave up before converging.

**Steps (in order):**

1. Add `ValidationReport` and `RefineResult` to `agent/schemas.py` and unit tests for them in `tests/test_schemas.py`.
2. Write `agent/validators.py` with `compute_plan_totals` and `check_targets`. Write `tests/test_validators.py` exhaustively — this is the quietly-important file; get its math right.
3. Add `build_refinement_prompt` to `agent/prompts.py` and a test in `tests/test_prompts.py` for its wording.
4. Write `agent/refine.py`. Keep it tiny: one function, one loop, no hidden state.
5. Write `tests/test_refine.py` using a FakeLLM scripted with multiple canned replies. Cover both the converge and the give-up paths.
6. Add `get_refinement_config` to `src/app/dependencies.py` with sensible defaults.
7. Wire the loop into `src/app/routes/plan.py`, then `src/app/routes/chat.py`. Update `test_plan.py` and `test_chat.py` to cover the new behavior.
8. Extend `agent/tracing.py` to record iteration count + converged flag.
9. Run the real app against a tight profile (e.g. 2500 kcal / 180 g protein) and confirm you can see one correction turn in the server logs when the first plan is off.
10. Re-run `python -m evals.runner` and compare against the Phase 3 baseline — `target_accuracy` should visibly improve. This is the payoff; save the new numbers.

**After Phase 3.5 your folder looks like this** (only changes from Phase 3 shown):

```
nutri-assistant/
├── agent/
│   ├── schemas.py                ← CHANGED: adds ValidationReport, RefineResult
│   ├── prompts.py                ← CHANGED: adds build_refinement_prompt
│   ├── tracing.py                ← CHANGED: records refine iterations + converged
│   ├── validators.py             ← NEW: compute_plan_totals + check_targets (pure)
│   ├── refine.py                 ← NEW: the loop — validate → correct → re-ask, with a cap
│   ├── llm.py                    ← unchanged
│   └── session.py                ← unchanged
├── src/app/
│   ├── dependencies.py           ← CHANGED: adds get_refinement_config
│   └── routes/
│       ├── plan.py               ← CHANGED: wraps LLM call in refine loop
│       └── chat.py               ← CHANGED: same, for replies that include a new plan
└── tests/
    ├── test_schemas.py           ← CHANGED: covers the two new models
    ├── test_prompts.py           ← CHANGED: locks refinement-prompt wording
    ├── test_validators.py        ← NEW: tolerance math, edge cases
    ├── test_refine.py            ← NEW: converges / gives up with warning
    ├── test_plan.py              ← CHANGED: asserts refine loop fires on /plan
    └── test_chat.py              ← CHANGED: asserts refine loop fires on adaptations
```

**How you know it works:** you set a profile of 2500 kcal / 180 g protein / 250 g carbs / 70 g fat and submit. The first LLM reply, left alone, would have totaled 2180 kcal and 160 g protein. Instead the response comes back at ~2475 kcal and ~178 g protein, and the server log shows *one* correction round-trip. You then say *"make breakfast lighter"* in chat — the adapted plan still lands near the same targets, because the loop ran again. If you deliberately set an impossible profile (say 2500 kcal at 250 g protein with no meat), the response comes back with a `warnings` field saying targets weren't hit after 3 tries — not silence, not a lie. And when you re-run evals, `target_accuracy` is measurably higher than the Phase 3 baseline.

---

## Phase 4 — Give the agent a food database &nbsp;·&nbsp; ⏭ Planned

**Goal:** the LLM stops guessing calorie numbers and starts looking them up in a real database — and your evals from Phase 3 confirm this actually improves quality, not just complexity.

**The one concept this phase is about:** the LLM can say *"I want to call a function called `food_search` with the argument `feijoada`"*. Our code runs that function, sends the result back to the LLM, and the LLM continues its reply. That back-and-forth loop is what makes this an "agent" in the strongest sense of the word, not just a chatbot.

**Heads-up on two loops that will coexist:** Phase 3.5 introduced `agent/refine.py` — a loop that says *"the totals are off, regenerate."* Phase 4 introduces `agent/loop.py` — a different loop that says *"the LLM asked for a food lookup, run it and feed the result back."* They're orthogonal: the tool-call loop runs *inside* a single LLM turn (until the LLM stops asking for tools); the refine loop wraps the whole thing and may trigger another full turn. Keep the names distinct in your head.

**New files:**

| File | What lives in it |
|---|---|
| `tools/food_search.py` | Reads TACO (a Brazilian food CSV we commit). Falls back to the free USDA API for foods TACO doesn't have. |
| `tools/registry.py` | The list of all tools the LLM is allowed to use, with names and argument shapes. |
| `agent/loop.py` | The tool-call loop: ask LLM → if it requests a tool, run it → send result back → repeat until LLM gives a final answer. |

**Seam to reuse, not reinvent:** `src/app/dependencies.py` already has DI providers for the LLM, the session store, and (from Phase 3.5) the refinement config. Add a `get_tool_registry` provider here so routes — and tests — can inject a real or fake registry the same way they inject the LLM today. Also: extend `agent/tracing.py` from Phase 3 to record tool calls in the same `traces.db`.

**After Phase 4 your folder looks like this** (only changes from Phase 3.5 shown):

```
nutri-assistant/
├── agent/
│   ├── ...                       ← schemas, llm, prompts, session, refine, validators, tracing (unchanged)
│   └── loop.py                   ← NEW: ask-LLM → run-tool → send-result → repeat (tool-calling)
└── tools/                        ← NEW folder: everything the LLM can call
    ├── registry.py               ← list of tools the LLM is allowed to use
    ├── food_search.py            ← TACO lookup + USDA API fallback
    └── data/                     ← committed data files used by tools
        └── taco.csv              ← Brazilian food composition table (~600 foods)
```

**How you know it works:** you ask *"give me a 2000 kcal day of typical food from Bahia"* and in the server logs you can see the LLM call `food_search` several times. The returned meal plan's calorie total lands within ~10% of 2000. Then you re-run `python -m evals.runner` and compare against the Phase 3 baseline — calorie/macro accuracy and cuisine relevance should both visibly improve. If they don't, that's a real signal that something's wrong with the tool integration, not a vibe.

---

## Tech debt backlog &nbsp;·&nbsp; ⏸ Whenever

Items we've deliberately left for later. Not blocking any phase, but good hygiene to pick up when there's breathing room. New items get appended at the bottom.

### 1. Deprecate the old HTML UI and make the React app the only UI

**Problem in plain words:** the repo currently ships *two* UIs that do the same job. `src/app/templates/onboarding.html` is served by `GET /` on FastAPI (the Phase 1 form). `frontend/` is the React/Vite app (added in Phase 2). They grew up side by side and the old one was never retired. New contributors can't tell which is "the real UI," the README still points at the HTML one, and `jinja2` sits in `pyproject.toml` purely to power a page nobody should be using.

**Why it's debt, not a feature:** every UI change has to be done twice or silently isn't done in one place. The `GET /` route is actively misleading — it tells you the product is an HTML form when it isn't anymore.

**Which files change and why:**

| File | What changes |
|---|---|
| `src/app/main.py` | Remove the `GET /` Jinja route, the `templates = Jinja2Templates(...)` setup, `_TEMPLATES_DIR`, and the now-unused imports (`HTMLResponse`, `Jinja2Templates`, `Request`, `Path`). Replace `GET /` with a small JSON service-info endpoint (`{"name": "Nutri Assistant API", "version": "0.1.0", "docs": "/docs"}`) so hitting the API root returns something useful instead of 404. |
| `src/app/templates/onboarding.html` | Delete. Delete the empty `templates/` folder with it. |
| `pyproject.toml` | Remove `"jinja2>=3.1.4"` from dependencies and update the comment that mentions it. Run `uv sync` afterward to regenerate `uv.lock`. |
| `frontend/vite.config.ts` | Add a `server.proxy` entry forwarding `/plan`, `/chat`, and `/health` to `http://127.0.0.1:8000`. This lets React keep calling relative paths (`fetch("/plan")`) in dev with no CORS configuration. |
| `README.md` | Update "Run the server" to describe two processes (uvicorn + `npm run dev`), change the landing URL to `http://localhost:5173`, drop the `GET /` row from the endpoints table, and update the project-layout tree to remove `templates/` and show `frontend/`. |
| `DEVELOPMENT_PLAN.md` | Phases 1 and 1.5 still mention `templates/onboarding.html` in their "after this phase" file trees. Leave the phase history intact — just note at the top of each that the file was removed in this tech-debt pass so the reader isn't misled. |

**Why a Vite dev proxy instead of CORS on FastAPI:** the proxy is simpler (React code keeps using relative paths, no hard-coded ports), and when we eventually deploy with FastAPI serving the built React app from the same origin, the same relative paths keep working unchanged. CORS would require whitelisting the frontend origin and risks silent misconfiguration.

**Automated testing to prove the change works (the must-have, not the nice-to-have):**

| Test | Where it lives | What it protects against |
|---|---|---|
| Existing `tests/test_health.py`, `tests/test_plan.py`, `tests/test_chat.py` | unchanged | They already use `FakeLLM` and never touched HTML. They **must still pass verbatim** — first signal nothing downstream broke. |
| `tests/test_root.py` (NEW) | `tests/` | One small test: `GET /` returns 200, `application/json` content-type, and a body containing a `docs` key. Locks in "the HTML root is gone" so it can't silently come back in a future merge. |
| Frontend unit tests with **Vitest + React Testing Library** (NEW) | `frontend/src/__tests__/` | One test per component: `OnboardingForm` builds the right JSON body on submit, `MealPlanPane` renders N meals correctly, `ChatPane` appends a turn when `/chat` returns. `fetch` is mocked. Catches React-logic bugs without needing a real browser. |
| One end-to-end test with **Playwright** (NEW) | `frontend/e2e/` | Happy path: boot uvicorn with `FakeLLM` injected via the existing DI overrides, boot Vite, open `http://localhost:5173`, fill the form, submit, assert the plan renders, send one chat message, assert the plan updates. This is the **only** test that exercises the Vite proxy end-to-end — without it, a broken proxy config would only surface in the browser. |

One rule for the tests: they must run in CI with zero network access to Gemini. The FastAPI side already has `FakeLLM` via DI overrides; the Playwright test reuses that same seam instead of inventing a new mock.

**How you know it's done:**

- `uv run pytest` — all backend tests pass, including the new `test_root.py`.
- `cd frontend && npm test` — the Vitest suite passes.
- `cd frontend && npm run e2e` — the Playwright happy path passes against a local uvicorn + Vite.
- Opening `http://localhost:8000/` returns JSON pointing at `/docs`; opening `http://localhost:5173/` shows the React UI and everything works — no HTML template involved anywhere.
- `rg -n "onboarding\.html|Jinja2Templates|jinja2" .` returns zero hits across the repo.

**Risks to flag on the day we do this:**

- Anyone (teammate, bookmark, CI script) who expects HTML at `http://localhost:8000/` will see JSON instead. Intentional — call it out in the commit message.
- First time the React app runs end-to-end against the real backend, small payload mismatches between the old inline JS and the new React code may surface. Fix each as a tiny follow-up; the E2E test is what will tell us.
- Deployment (single-origin vs split-origin) is a **separate** decision that belongs to its own future phase, not this tech-debt item.

---

## Why this order?

- **Phase 0 first** — you can't learn on code you can't run.
- **Phase 1 before 2** — debugging a broken agent with a fancy UI in the way is 10× harder than debugging a bare agent.
- **Phase 1.5 before 2** — a thin profile produces thin plans no matter how pretty the UI is around them.
- **Phase 3 before 3.5** — evals first, so the refine loop has to earn its place by actually moving `target_accuracy`. Measuring before intervening is how you avoid "I built a thing, surely it helps" thinking.
- **Phase 3.5 before 4** — get the plan-total pressure mechanism working (and measured) before layering on real food data. Two interventions in one phase would make it impossible to tell which one moved the numbers.
- **Phase 4 last** — tool integration is the biggest jump in agent complexity. Do it when everything around it is debugged and measurable.

---

## Explicitly not doing (until you decide otherwise)

No login, no user accounts, no production deployment, no Docker, no payments, no non-Brazilian cuisine, no mobile app. Each of these is a rabbit hole; none of them helps you learn the agent.
