"""Unit tests for prompt building.

Because `build_system_prompt` is a pure function, we can assert on the
exact phrases it emits — no LLM, no network, no fixtures.
"""

from __future__ import annotations

from agent.prompts import build_initial_user_message, build_system_prompt
from agent.schemas import UserProfile


def test_system_prompt_includes_allergies_loudly() -> None:
    profile = UserProfile(
        goal="lose_weight",
        allergies=["peanuts", "shellfish"],
        calorie_target=1800,
        cuisine_preferences=["Mineira"],
    )

    prompt = build_system_prompt(profile)

    assert "peanuts" in prompt
    assert "shellfish" in prompt
    assert "CRITICAL" in prompt


def test_system_prompt_omits_allergy_section_when_empty() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2000)

    prompt = build_system_prompt(profile)

    assert "no known food allergies" in prompt
    assert "CRITICAL" not in prompt


def test_system_prompt_mentions_calorie_target_and_cuisines_plural() -> None:
    profile = UserProfile(
        goal="gain_muscle",
        calorie_target=2800,
        cuisine_preferences=["Bahian", "Japanese"],
    )

    prompt = build_system_prompt(profile)

    assert "2800" in prompt
    assert "Bahian" in prompt
    assert "Japanese" in prompt
    # The phrasing is plural even when there could be one cuisine; this
    # locks in the "cuisines plural" wording.
    assert "Cuisine preferences" in prompt
    assert "gain muscle" in prompt


def test_system_prompt_keeps_allergies_and_dislikes_distinct() -> None:
    # The whole point of Phase 1.5: safety and preference must NOT be merged.
    profile = UserProfile(
        goal="maintain",
        calorie_target=2000,
        allergies=["shellfish"],
        disliked_ingredients=["cilantro"],
    )

    prompt = build_system_prompt(profile)

    assert "CRITICAL" in prompt
    assert "shellfish" in prompt
    assert "AVOID WHEN POSSIBLE" in prompt
    assert "cilantro" in prompt
    # And crucially — they should NOT appear on the same rule line. The
    # rough check: the CRITICAL block should NOT mention cilantro, and
    # the AVOID block should NOT mention shellfish.
    critical_start = prompt.index("CRITICAL")
    avoid_start = prompt.index("AVOID WHEN POSSIBLE")
    critical_block = prompt[critical_start:avoid_start]
    avoid_block = prompt[avoid_start:]
    assert "cilantro" not in critical_block
    assert "shellfish" not in avoid_block


def test_system_prompt_omits_dislikes_when_empty() -> None:
    profile = UserProfile(
        goal="maintain",
        calorie_target=2000,
        allergies=["peanuts"],
    )

    prompt = build_system_prompt(profile)

    assert "no strong ingredient dislikes" in prompt
    assert "AVOID WHEN POSSIBLE" not in prompt


def test_system_prompt_includes_macro_targets_when_set() -> None:
    profile = UserProfile(
        goal="gain_muscle",
        calorie_target=2800,
        protein_g_target=180,
        carbs_g_target=300,
        fat_g_target=80,
    )

    prompt = build_system_prompt(profile)

    assert "180" in prompt
    assert "300" in prompt
    assert "80" in prompt
    assert "protein" in prompt.lower()
    assert "carbs" in prompt.lower()
    assert "fat" in prompt.lower()


def test_system_prompt_omits_macro_targets_when_unset() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2000)

    prompt = build_system_prompt(profile)

    # None of the macro-target lines should appear when the user set none.
    assert "Target protein" not in prompt
    assert "Target carbs" not in prompt
    assert "Target fat" not in prompt


def test_system_prompt_includes_only_set_macro_targets() -> None:
    # Partial set: only protein. Prompt should mention it but NOT carbs/fat.
    profile = UserProfile(
        goal="gain_muscle",
        calorie_target=2500,
        protein_g_target=150,
    )

    prompt = build_system_prompt(profile)

    assert "150" in prompt
    assert "Target protein" in prompt
    assert "Target carbs" not in prompt
    assert "Target fat" not in prompt


def test_system_prompt_states_meal_count() -> None:
    profile = UserProfile(goal="maintain", calorie_target=2000, meals_per_day=5)

    prompt = build_system_prompt(profile)

    # The number itself should appear; the prompt tells the LLM to produce
    # exactly that many meals.
    assert "5" in prompt
    assert "meals" in prompt


def test_system_prompt_includes_flavor_profiles_when_set() -> None:
    profile = UserProfile(
        goal="maintain",
        calorie_target=2000,
        flavor_profiles=["savory", "umami"],
    )

    prompt = build_system_prompt(profile)

    assert "savory" in prompt
    assert "umami" in prompt


def test_initial_user_message_mentions_target_and_cuisines_and_meal_count() -> None:
    profile = UserProfile(
        goal="maintain",
        calorie_target=2100,
        cuisine_preferences=["Paulista", "Japanese"],
        meals_per_day=4,
    )

    message = build_initial_user_message(profile)

    assert "2100" in message
    assert "Paulista" in message
    assert "Japanese" in message
    assert "4" in message
