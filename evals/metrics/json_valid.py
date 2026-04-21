"""Metric: did the LLM's reply parse as a valid MealPlan?

This is the most basic metric — if it fails, every other metric is moot
because there's no plan to inspect. Binary: 1.0 = parseable, 0.0 = not.
"""

from __future__ import annotations

from pydantic import ValidationError

from agent.schemas import MealPlan
from evals.metrics import MetricResult


def score(raw_reply: str) -> MetricResult:
    """Try to parse `raw_reply` as a MealPlan. Return pass/fail with reason."""
    try:
        # `model_validate_json` does JSON parse + Pydantic validation in one
        # step. If anything's off — bad JSON, missing fields, wrong types —
        # it raises ValidationError with details.
        MealPlan.model_validate_json(raw_reply)
    except ValidationError as exc:
        # `str(exc)[:200]` truncates noisy multi-line errors so the summary
        # table stays readable. Full error is still in the trace row.
        return MetricResult(score=0.0, passed=False, details=str(exc)[:200])
    except ValueError as exc:
        # `model_validate_json` raises ValueError for malformed JSON
        # (it's a JSONDecodeError subclass). Catch it separately so the
        # message in the summary table is meaningful.
        return MetricResult(score=0.0, passed=False, details=f"bad JSON: {exc}")
    return MetricResult(score=1.0, passed=True, details="parsed cleanly")
