"""Shared pytest fixtures.

A `TestClient` plus a `FakeLLM` that records every call and replies with
a canned MealPlan JSON. These are reused across test_plan.py and test_chat.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from agent.llm import LLM, Message
from agent.session import SessionStore
from src.app.dependencies import get_llm, get_session_store
from src.app.main import app


CANNED_PLAN_JSON = """
{
  "meals": [
    {
      "name": "Tapioca com queijo",
      "description": "Simple Brazilian breakfast.",
      "ingredients": [
        {"name": "tapioca flour", "calories": 250, "protein_g": 0, "carbs_g": 55, "fat_g": 0},
        {"name": "cheese",        "calories": 150, "protein_g": 15, "carbs_g": 0,  "fat_g": 12}
      ]
    },
    {
      "name": "Feijoada lite",
      "description": "Lightened feijoada.",
      "ingredients": [
        {"name": "black beans", "calories": 200, "protein_g": 15, "carbs_g": 35, "fat_g": 1},
        {"name": "pork",        "calories": 300, "protein_g": 25, "carbs_g": 0,  "fat_g": 19},
        {"name": "rice",        "calories": 200, "protein_g": 0,  "carbs_g": 45, "fat_g": 0}
      ]
    },
    {
      "name": "Grilled fish with farofa",
      "description": "Grilled tilapia with manioc farofa.",
      "ingredients": [
        {"name": "tilapia",       "calories": 250, "protein_g": 40, "carbs_g": 0,  "fat_g": 10},
        {"name": "cassava flour", "calories": 300, "protein_g": 2,  "carbs_g": 50, "fat_g": 5},
        {"name": "onion",         "calories": 50,  "protein_g": 3,  "carbs_g": 0,  "fat_g": 3}
      ]
    }
  ],
  "notes": "Balanced day."
}
"""


@dataclass
class FakeLLM:
    """Deterministic stand-in for GeminiLLM.

    Records every `chat` call so tests can assert on what was sent,
    and returns `canned_reply` each time.
    """

    canned_reply: str = CANNED_PLAN_JSON
    calls: list[dict] = field(default_factory=list)

    def chat(
        self,
        messages: list[Message],
        *,
        system: str,
        response_schema: type[BaseModel],
    ) -> str:
        self.calls.append(
            {
                "messages": list(messages),
                "system": system,
                "response_schema": response_schema,
            }
        )
        return self.canned_reply


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(fake_llm: FakeLLM) -> Iterator[TestClient]:
    """TestClient with the LLM and SessionStore overridden.

    Each test gets its OWN SessionStore so tests don't leak state.
    """
    fresh_store = SessionStore()

    app.dependency_overrides[get_llm] = lambda: fake_llm
    app.dependency_overrides[get_session_store] = lambda: fresh_store

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
