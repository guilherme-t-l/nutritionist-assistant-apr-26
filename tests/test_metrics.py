"""Unit tests for the four eval metrics.

These tests use hand-built MealPlan / UserProfile objects so the metrics
can be exercised without any LLM call. The cuisine_relevance metric, which
DOES need an LLM, is tested with a minimal in-file fake.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from agent.llm import Message
from agent.schemas import Food, Meal, MealPlan, UserProfile
from evals.metrics import allergen_leak, cuisine_relevance, json_valid, target_accuracy


# ---------- helpers ------------------------------------------------------------

def _make_food(name: str, kcal: int, p: int = 0, c: int = 0, f: int = 0) -> Food:
    return Food(name=name, quantity="1 portion", calories=kcal, protein_g=p, carbs_g=c, fat_g=f)


def _plan_2000_kcal() -> MealPlan:
    """A simple 3-meal plan whose foods sum to exactly 2000 kcal, 100g protein."""
    return MealPlan(
        meals=[
            Meal(
                name="Café da manhã",
                description="Tapioca com queijo",
                ingredients=[
                    _make_food("tapioca flour", 250, p=0, c=55, f=0),
                    _make_food("cheese", 250, p=20, c=2, f=18),
                ],
            ),
            Meal(
                name="Almoço",
                description="Grilled chicken with rice and beans",
                ingredients=[
                    _make_food("grilled chicken", 400, p=50, c=0, f=10),
                    _make_food("rice", 250, p=4, c=55, f=1),
                    _make_food("black beans", 200, p=12, c=35, f=1),
                ],
            ),
            Meal(
                name="Jantar",
                description="Tilapia with sweet potato",
                ingredients=[
                    _make_food("tilapia", 350, p=50, c=0, f=12),
                    _make_food("sweet potato", 300, p=4, c=70, f=1),
                ],
            ),
        ],
        notes="Plan that sums to 2000 kcal and 100g protein.",
    )


# ---------- json_valid ---------------------------------------------------------


def test_json_valid_passes_on_well_formed_plan() -> None:
    plan_json = _plan_2000_kcal().model_dump_json()
    result = json_valid.score(plan_json)
    assert result.passed is True
    assert result.score == 1.0


def test_json_valid_fails_on_malformed_json() -> None:
    result = json_valid.score("{not actually json")
    assert result.passed is False
    assert result.score == 0.0


def test_json_valid_fails_on_wrong_shape() -> None:
    result = json_valid.score('{"meals": []}')
    assert result.passed is False
    assert result.score == 0.0


# ---------- allergen_leak ------------------------------------------------------


def test_allergen_leak_passes_when_no_allergies_declared() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2000)
    result = allergen_leak.score(_plan_2000_kcal(), profile)
    assert result.passed is True
    assert "no allergies" in result.details


def test_allergen_leak_passes_when_clean() -> None:
    profile = UserProfile(
        goal="maintain", calorie_target=2000, allergies=["shrimp"]
    )
    result = allergen_leak.score(_plan_2000_kcal(), profile)
    assert result.passed is True


def test_allergen_leak_fails_on_ingredient_match() -> None:
    profile = UserProfile(
        goal="maintain", calorie_target=2000, allergies=["chicken"]
    )
    result = allergen_leak.score(_plan_2000_kcal(), profile)
    assert result.passed is False
    assert "chicken" in result.details.lower()


def test_allergen_leak_fails_on_description_match() -> None:
    profile = UserProfile(
        goal="maintain", calorie_target=2000, allergies=["tilapia"]
    )
    result = allergen_leak.score(_plan_2000_kcal(), profile)
    assert result.passed is False


def test_allergen_leak_is_case_insensitive() -> None:
    profile = UserProfile(
        goal="maintain", calorie_target=2000, allergies=["RICE"]
    )
    result = allergen_leak.score(_plan_2000_kcal(), profile)
    assert result.passed is False


# ---------- target_accuracy ----------------------------------------------------


def test_target_accuracy_full_pass_within_tolerance() -> None:
    profile = UserProfile(
        goal="maintain",
        calorie_target=2000,
        protein_g_target=140,
        carbs_g_target=217,
        fat_g_target=43,
    )
    result = target_accuracy.score(_plan_2000_kcal(), profile)
    assert result.passed is True
    assert result.score == 1.0


def test_target_accuracy_partial_credit_when_one_macro_off() -> None:
    profile = UserProfile(
        goal="maintain",
        calorie_target=2000,
        protein_g_target=200,  # plan has 140 → 30% off, fails
    )
    result = target_accuracy.score(_plan_2000_kcal(), profile)
    assert result.passed is False
    # 1 of 2 checks pass (calories yes, protein no) → 0.5
    assert result.score == 0.5
    assert "OFF" in result.details


def test_target_accuracy_unset_macros_are_skipped() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2000)
    result = target_accuracy.score(_plan_2000_kcal(), profile)
    assert result.passed is True
    # Only one check (calories) ran → score is 1.0 not partial.
    assert result.score == 1.0


def test_target_accuracy_calorie_just_inside_5_percent() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2100)  # plan = 2000, off 4.76%
    result = target_accuracy.score(_plan_2000_kcal(), profile)
    assert result.passed is True


def test_target_accuracy_calorie_just_outside_5_percent() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2200)  # plan = 2000, off 9.1%
    result = target_accuracy.score(_plan_2000_kcal(), profile)
    assert result.passed is False


# ---------- cuisine_relevance --------------------------------------------------


@dataclass
class _FakeJudge:
    """Returns a canned JSON reply matching the _JudgeReply schema."""

    canned_score: int = 4
    canned_reason: str = "Solid Bahian dishes throughout."
    calls: list[dict] = field(default_factory=list)

    def chat(
        self,
        messages: list[Message],
        *,
        system: str,
        response_schema: type[BaseModel],
    ) -> str:
        self.calls.append({"messages": list(messages), "system": system})
        return f'{{"score": {self.canned_score}, "reason": "{self.canned_reason}"}}'


def test_cuisine_relevance_normalizes_score() -> None:
    profile = UserProfile(
        goal="maintain", calorie_target=2000, cuisine_preferences=["Bahian"]
    )
    judge = _FakeJudge(canned_score=5)
    result = cuisine_relevance.score(_plan_2000_kcal(), profile, judge)
    assert result.score == 1.0
    assert result.passed is True


def test_cuisine_relevance_low_score_fails() -> None:
    profile = UserProfile(
        goal="maintain", calorie_target=2000, cuisine_preferences=["Japanese"]
    )
    judge = _FakeJudge(canned_score=2, canned_reason="Mostly generic.")
    result = cuisine_relevance.score(_plan_2000_kcal(), profile, judge)
    assert result.score == 0.25  # (2-1)/4
    assert result.passed is False


def test_cuisine_relevance_includes_cuisines_in_prompt() -> None:
    profile = UserProfile(
        goal="maintain",
        calorie_target=2000,
        cuisine_preferences=["Bahian", "Mineira"],
    )
    judge = _FakeJudge()
    cuisine_relevance.score(_plan_2000_kcal(), profile, judge)
    sent = judge.calls[0]["messages"][0].content
    assert "Bahian" in sent and "Mineira" in sent


def test_cuisine_relevance_handles_judge_failure() -> None:
    @dataclass
    class _BrokenJudge:
        def chat(self, messages, *, system, response_schema):  # type: ignore[no-untyped-def]
            raise RuntimeError("API down")

    profile = UserProfile(
        goal="maintain", calorie_target=2000, cuisine_preferences=["Bahian"]
    )
    result = cuisine_relevance.score(_plan_2000_kcal(), profile, _BrokenJudge())
    assert result.score == 0.0
    assert result.passed is False
    assert "judge call failed" in result.details
