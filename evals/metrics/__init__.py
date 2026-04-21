"""Eval metrics. One file per metric so each can evolve independently.

All metrics return a `MetricResult`:
  - score: a float in [0.0, 1.0] (continuous metrics) or {0.0, 1.0} (binary).
  - passed: bool — convenience flag for the summary table.
  - details: short human-readable string explaining the score.

Keeping the contract uniform means the runner can iterate over metrics
without special-casing each one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetricResult:
    """One metric's verdict on one (profile, plan) pair."""

    score: float
    passed: bool
    details: str


__all__ = ["MetricResult"]
