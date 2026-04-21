"""End-to-end tests for POST /chat.

The point of these tests: prove that on the second turn, the LLM sees
the FULL history — not just the new message. If history weren't being
forwarded, the agent would forget the previous meal plan, and 'make
lunch lighter' wouldn't make any sense.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import FakeLLM


def test_chat_uses_session_and_forwards_history(
    client: TestClient, fake_llm: FakeLLM
) -> None:
    plan_response = client.post(
        "/plan",
        json={
            "goal": "maintain",
            "calorie_target": 2000,
            "cuisine_preference": "Brazilian",
        },
    )
    session_id = plan_response.json()["session_id"]

    chat_response = client.post(
        "/chat",
        json={"session_id": session_id, "message": "make lunch lighter"},
    )

    assert chat_response.status_code == 200, chat_response.text

    second_call = fake_llm.calls[1]
    messages = second_call["messages"]

    # We should see: initial user message, model's first reply, new user turn.
    assert len(messages) == 3
    assert messages[0].role == "user"
    assert messages[1].role == "model"
    assert messages[2].role == "user"
    assert messages[2].content == "make lunch lighter"


def test_chat_rejects_unknown_session(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"session_id": "does-not-exist", "message": "hi"},
    )

    assert response.status_code == 404


def test_chat_rejects_empty_message(client: TestClient) -> None:
    plan_response = client.post(
        "/plan",
        json={"goal": "maintain", "calorie_target": 2000},
    )
    session_id = plan_response.json()["session_id"]

    response = client.post(
        "/chat",
        json={"session_id": session_id, "message": ""},
    )

    assert response.status_code == 422
