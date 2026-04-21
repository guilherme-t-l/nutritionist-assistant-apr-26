import { useState } from "react";

import { createPlan } from "./api";
import type {
  FlavorProfile,
  Goal,
  PlanResponse,
  UserProfile,
} from "./types";

// Props this component accepts. `onPlanReady` is how we bubble the result
// back up to <App />. React components don't return data — they shout it
// upward through callbacks the parent provided.
interface OnboardingFormProps {
  onPlanReady: (response: PlanResponse, profile: UserProfile) => void;
}

const FLAVOR_OPTIONS: FlavorProfile[] = [
  "savory",
  "sweet",
  "spicy",
  "umami",
  "sour",
  "bitter",
];

export function OnboardingForm({ onPlanReady }: OnboardingFormProps) {
  // Each piece of form state is a separate useState. Could also be one big
  // object; kept flat here because it reads more like a form.
  const [goal, setGoal] = useState<Goal>("maintain");
  const [calorieTarget, setCalorieTarget] = useState(2000);
  const [proteinTarget, setProteinTarget] = useState<string>("");
  const [carbsTarget, setCarbsTarget] = useState<string>("");
  const [fatTarget, setFatTarget] = useState<string>("");
  const [cuisines, setCuisines] = useState("Brazilian");
  const [flavors, setFlavors] = useState<FlavorProfile[]>(["savory"]);
  const [allergies, setAllergies] = useState("");
  const [dislikes, setDislikes] = useState("");
  const [mealsPerDay, setMealsPerDay] = useState(3);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // `FormEvent` is the TypeScript type for form-submit events. Calling
  // `e.preventDefault()` stops the browser's default behaviour (a full
  // page reload) — we want a fetch and an in-place update instead.
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    // Split free-text comma lists into arrays. `filter(Boolean)` drops
    // empty strings ("a,,b" → ["a","b"]).
    const toList = (s: string) =>
      s.split(",").map((x) => x.trim()).filter(Boolean);

    // `parseOptionalInt("")` → null, `parseOptionalInt("180")` → 180.
    // Sent as null for the optional macro targets when the user leaves
    // them blank, matching Pydantic's `int | None` default.
    const parseOptionalInt = (s: string): number | null => {
      if (!s.trim()) return null;
      const n = Number(s);
      return Number.isFinite(n) ? Math.round(n) : null;
    };

    const profile: UserProfile = {
      goal,
      calorie_target: calorieTarget,
      protein_g_target: parseOptionalInt(proteinTarget),
      carbs_g_target: parseOptionalInt(carbsTarget),
      fat_g_target: parseOptionalInt(fatTarget),
      cuisine_preferences: toList(cuisines),
      flavor_profiles: flavors,
      allergies: toList(allergies),
      disliked_ingredients: toList(dislikes),
      meals_per_day: mealsPerDay,
    };

    try {
      const response = await createPlan(profile);
      onPlanReady(response, profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function toggleFlavor(flavor: FlavorProfile) {
    setFlavors((current) =>
      current.includes(flavor)
        ? current.filter((f) => f !== flavor)
        : [...current, flavor],
    );
  }

  return (
    <div className="onboarding-wrap">
      <div className="onboarding-card">
        <h1>Nutri Assistant</h1>
        <p className="lead">
          A Brazilian AI nutritionist. Tell it about you; it builds a day of meals.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="goal">Goal</label>
          <select
            id="goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value as Goal)}
          >
            <option value="lose_weight">Lose weight</option>
            <option value="maintain">Maintain</option>
            <option value="gain_muscle">Gain muscle</option>
          </select>

          <div className="row-2">
            <div>
              <label htmlFor="calorie_target">Daily calories (kcal)</label>
              <input
                id="calorie_target"
                type="number"
                min={800}
                max={5000}
                value={calorieTarget}
                onChange={(e) => setCalorieTarget(Number(e.target.value))}
                required
              />
            </div>
            <div>
              <label htmlFor="meals_per_day">Meals per day</label>
              <input
                id="meals_per_day"
                type="number"
                min={1}
                max={8}
                value={mealsPerDay}
                onChange={(e) => setMealsPerDay(Number(e.target.value))}
                required
              />
            </div>
          </div>

          <div className="row-3">
            <div>
              <label htmlFor="protein_g">Protein g <span className="muted small">(optional)</span></label>
              <input
                id="protein_g"
                type="number"
                min={0}
                value={proteinTarget}
                onChange={(e) => setProteinTarget(e.target.value)}
                placeholder="e.g. 180"
              />
            </div>
            <div>
              <label htmlFor="carbs_g">Carbs g <span className="muted small">(optional)</span></label>
              <input
                id="carbs_g"
                type="number"
                min={0}
                value={carbsTarget}
                onChange={(e) => setCarbsTarget(e.target.value)}
                placeholder="e.g. 220"
              />
            </div>
            <div>
              <label htmlFor="fat_g">Fat g <span className="muted small">(optional)</span></label>
              <input
                id="fat_g"
                type="number"
                min={0}
                value={fatTarget}
                onChange={(e) => setFatTarget(e.target.value)}
                placeholder="e.g. 70"
              />
            </div>
          </div>

          <label htmlFor="cuisines">Cuisines (comma-separated)</label>
          <input
            id="cuisines"
            type="text"
            value={cuisines}
            onChange={(e) => setCuisines(e.target.value)}
            placeholder="Bahian, Japanese"
            required
          />

          <label>Flavor profiles</label>
          <div className="checkbox-group">
            {FLAVOR_OPTIONS.map((flavor) => (
              <label key={flavor}>
                <input
                  type="checkbox"
                  checked={flavors.includes(flavor)}
                  onChange={() => toggleFlavor(flavor)}
                />
                {flavor}
              </label>
            ))}
          </div>

          <label htmlFor="allergies">
            Allergies <span className="muted small">(never include — medical)</span>
          </label>
          <input
            id="allergies"
            type="text"
            value={allergies}
            onChange={(e) => setAllergies(e.target.value)}
            placeholder="peanuts, shellfish"
          />

          <label htmlFor="dislikes">
            Dislikes <span className="muted small">(avoid — not medical)</span>
          </label>
          <input
            id="dislikes"
            type="text"
            value={dislikes}
            onChange={(e) => setDislikes(e.target.value)}
            placeholder="cilantro, olives"
          />

          <div style={{ marginTop: "1.25rem" }}>
            <button type="submit" disabled={submitting}>
              {submitting ? "Thinking..." : "Build my meal plan"}
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </div>
    </div>
  );
}
