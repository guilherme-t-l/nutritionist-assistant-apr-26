"""Metric: how well does the plan reflect the user's stated cuisine(s)?

Uses a *second* LLM call as the judge. The judge sees the user's cuisine
preferences and the plan, and rates 1 to 5. The score is normalized to [0, 1].

Why use an LLM as a judge here? Because "is this plan Bahian?" is fuzzy —
no rule-based check would distinguish "moqueca + acarajé + cocada" (very
Bahian) from "feijoada + caesar salad + cheesecake" (Brazilian-ish but not
Bahian). LLMs are decent at fuzzy semantic judgments. They also
introduce noise — Phase 4 will look at whether real food data shifts this
score in the expected direction, which would partly validate the metric.

To keep the metric *unit-testable without network*, we accept any LLM-shaped
object (anything with a `.chat(...)` method matching the `LLM` Protocol).
The runner injects the real Gemini client; tests inject a fake.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from agent.llm import LLM, Message
from agent.schemas import MealPlan, UserProfile
from evals.metrics import MetricResult


class _JudgeReply(BaseModel):
    """Structured shape we ask the judge LLM to fill in.

    `score` is the integer 1-5 rating; `reason` is a one-sentence
    explanation we surface in `details`. Asking for both forces the LLM to
    justify the number, which empirically reduces "always 4" laziness.
    """

    score: int = Field(ge=1, le=5)
    reason: str


_JUDGE_SYSTEM = (
    "You are an expert on world cuisines. You receive a user's cuisine "
    "preferences and a daily meal plan. You rate how well the plan reflects "
    "the requested cuisines on a scale of 1 to 5:\n"
    "  1 = no recognizable connection to the requested cuisines\n"
    "  2 = vaguely related, mostly generic\n"
    "  3 = clearly inspired by them but with weak signals\n"
    "  4 = solid representation of the requested cuisines\n"
    "  5 = an authentic, expert-level expression of the requested cuisines\n"
    "Reply ONLY in the JSON shape requested."
)


def score(plan: MealPlan, profile: UserProfile, judge: LLM) -> MetricResult:
    """Ask the judge LLM to rate cuisine relevance, normalize to [0, 1]."""

    cuisines = ", ".join(profile.cuisine_preferences) or "Brazilian"
    plan_text = _summarize_plan_for_judge(plan)
    user_message = (
        f"User's requested cuisines: {cuisines}.\n\n"
        f"Plan:\n{plan_text}\n\n"
        "Rate the plan 1 to 5 with a one-sentence reason."
    )

    try:
        raw = judge.chat(
            messages=[Message(role="user", content=user_message)],
            system=_JUDGE_SYSTEM,
            response_schema=_JudgeReply,
        )
        verdict = _JudgeReply.model_validate_json(raw)
    except (ValidationError, ValueError, RuntimeError) as exc:
        # Judge failures shouldn't crash the whole eval run — log a 0
        # with the reason so we can investigate.
        return MetricResult(
            score=0.0,
            passed=False,
            details=f"judge call failed: {exc}",
        )

    # Normalize 1-5 to [0, 1] linearly: 1→0.0, 3→0.5, 5→1.0.
    normalized = (verdict.score - 1) / 4
    # `passed` defined as "the judge gave at least 4/5" — Phase 4 needs to
    # show this number going up, so the bar is set explicitly here.
    return MetricResult(
        score=normalized,
        passed=verdict.score >= 4,
        details=f"judge: {verdict.score}/5 — {verdict.reason}",
    )


def _summarize_plan_for_judge(plan: MealPlan) -> str:
    """Compact text representation of a plan to feed to the judge.

    We don't send the raw JSON — meal names + ingredient lists is enough to
    judge cuisine, and shorter prompts are cheaper and lower-variance.
    """
    lines: list[str] = []
    for i, meal in enumerate(plan.meals, start=1):
        ingredients = ", ".join(food.name for food in meal.ingredients)
        lines.append(f"  {i}. {meal.name} — {ingredients}")
    return "\n".join(lines)
