// Thin typed wrappers around the FastAPI endpoints.
//
// Every network call in the app goes through here. The URLs are relative
// ("/plan", not "http://localhost:8000/plan") because Vite's dev-server
// proxy rewrites them to the Python backend. See frontend/vite.config.ts.
//
// Keeping this file as the single place the frontend talks to HTTP mirrors
// the "one file talks to Gemini" rule on the backend (agent/llm.py).

import type { ChatResponse, PlanResponse, UserProfile } from "./types";

// FastAPI returns { detail: "..." } on 4xx/5xx. This unwraps that cleanly
// so callers can `catch (err) { err.message }` and show it in the UI.
async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      // Response wasn't JSON; fall back to statusText we already have.
    }
    throw new Error(detail);
  }

  return (await res.json()) as T;
}

export function createPlan(profile: UserProfile): Promise<PlanResponse> {
  return postJson<PlanResponse>("/plan", profile);
}

export function sendChat(
  sessionId: string,
  message: string,
): Promise<ChatResponse> {
  return postJson<ChatResponse>("/chat", {
    session_id: sessionId,
    message,
  });
}
