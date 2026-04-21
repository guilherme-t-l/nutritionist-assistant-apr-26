# POST /chat — multi-turn refinement of an existing meal plan.
#
# Each call re-sends the ENTIRE conversation history. Gemini therefore sees
# the plan it previously produced plus the user's new refinement request
# ("make lunch lighter"), and returns an updated full MealPlan.
#
# We always return a full plan (never a diff) because partial updates are
# harder to validate and to render.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from agent.llm import LLM, Message
from agent.prompts import build_system_prompt
from agent.schemas import MealPlan
from agent.session import SessionStore
from src.app.dependencies import get_llm, get_session_store


router = APIRouter()


# The JSON shape the frontend sends to /chat.
class ChatRequest(BaseModel):
    session_id: str
    # `min_length=1` blocks empty strings; `max_length=1000` caps payload
    # size. Both enforced by Pydantic before our handler even runs.
    message: str = Field(min_length=1, max_length=1000)


# The JSON shape /chat returns — just the updated plan (the frontend already
# has the session_id from /plan).
class ChatResponse(BaseModel):
    plan: MealPlan


# Handler for POST /chat. Called by FastAPI whenever the user types a
# refinement after having already called /plan at least once.
#
# Flow, in order:
#   1. Body is parsed into ChatRequest (Pydantic enforces 1..1000 chars).
#   2. FastAPI injects `llm` and `store` via Depends(...).
#   3. We LOAD the session by id. If missing -> 404 (user never called /plan).
#   4. We build the conversation: session.history + [new user turn].
#   5. We call llm.chat(...) with the same system prompt as /plan so the
#      agent keeps its personality + constraints across turns.
#   6. We re-validate the reply into a MealPlan; 502 if malformed.
#   7. We append both turns to session.history for the NEXT /chat call.
#   8. We return { plan }.
@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    llm: LLM = Depends(get_llm),
    store: SessionStore = Depends(get_session_store),
) -> ChatResponse:
    session = store.get(request.session_id)
    # `is None` — use `is` (identity) for None checks, not `== None`. Faster,
    # and safer against weird classes that override `__eq__`.
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id. Call /plan first.")

    user_turn = Message(role="user", content=request.message)
    # `list + list` returns a NEW list — `session.history` isn't mutated here.
    # We only append to history below, AFTER the LLM reply validates cleanly.
    conversation = session.history + [user_turn]

    raw_reply = llm.chat(
        messages=conversation,
        system=build_system_prompt(session.profile),
        response_schema=MealPlan,
    )

    try:
        plan = MealPlan.model_validate_json(raw_reply)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned an invalid MealPlan: {exc}",
        ) from exc

    session.history.append(user_turn)
    session.history.append(Message(role="model", content=raw_reply))

    return ChatResponse(plan=plan)
