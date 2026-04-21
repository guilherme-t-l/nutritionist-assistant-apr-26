# Nutri Assistant

AI nutritionist agent, built phase by phase (see `DEVELOPMENT_PLAN.md`).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager (`brew install uv`).
- A free Gemini API key from <https://aistudio.google.com/apikey>.

## Setup

```bash
uv sync   # installs dependencies from pyproject.toml into .venv/
```

Put your real Gemini key in `.env`:

```
GEMINI_API_KEY=your-real-key-here
```

## Run the server

```bash
uv run uvicorn src.app.main:app --reload
```

Then open <http://localhost:8000/> to fill in the onboarding form and chat with the agent.

Health check: <http://localhost:8000/health> — should return `{"status": "ok"}`.

## Run the tests

```bash
uv run pytest
```

Tests never call the real Gemini API — they swap in a `FakeLLM` via FastAPI's
dependency overrides (see `tests/conftest.py`).

## Endpoints (Phase 1)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Onboarding form (HTML) |
| `GET` | `/health` | Smoke check |
| `POST` | `/plan` | Profile in → first `MealPlan` out + a `session_id` |
| `POST` | `/chat` | `{session_id, message}` → updated `MealPlan` |

## Project layout

```
nutri-assistant/
├── pyproject.toml              Python dependency list
├── uv.lock                     pinned exact versions (commit this)
├── .env                        secrets (never commit)
├── agent/                      core agent logic — ZERO HTTP code lives here
│   ├── schemas.py              Pydantic contracts: UserProfile, Meal, MealPlan
│   ├── llm.py                  the ONE file that talks to Gemini (swap-here)
│   ├── prompts.py              builds the system prompt from a UserProfile
│   └── session.py              in-memory store of each guest's chat history
├── src/app/                    FastAPI HTTP layer — stays thin
│   ├── main.py                 app entry point, wires routes + serves /
│   ├── dependencies.py         DI providers for the LLM and session store
│   ├── routes/
│   │   ├── plan.py             POST /plan — profile in, meal plan out
│   │   └── chat.py             POST /chat — multi-turn refinement
│   └── templates/
│       └── onboarding.html     the form + chat UI
└── tests/                      mirrors the source layout
    ├── conftest.py             shared fixtures: FakeLLM, TestClient
    ├── test_health.py
    ├── test_schemas.py
    ├── test_prompts.py
    ├── test_plan.py
    └── test_chat.py
```

Later phases add `tools/`, `evals/`, and a React `frontend/`.
