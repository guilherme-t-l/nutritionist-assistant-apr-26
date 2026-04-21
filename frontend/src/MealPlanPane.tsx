import type { MealPlan } from "./types";

interface MealPlanPaneProps {
  plan: MealPlan;
  updating: boolean;
}

// Sum macros across every meal in the plan. We do this on the client
// because the backend only sends `total_calories`; computing P/C/F here
// is cheaper than adding more @computed_fields in agent/schemas.py.
// `reduce` walks the array once, carrying an accumulator object.
function dayTotals(plan: MealPlan) {
  return plan.meals.reduce(
    (acc, m) => ({
      calories: acc.calories + m.calories,
      protein_g: acc.protein_g + m.protein_g,
      carbs_g: acc.carbs_g + m.carbs_g,
      fat_g: acc.fat_g + m.fat_g,
    }),
    { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
  );
}

// Round to 1 decimal so we don't render "23.4000001g" artifacts that
// come from adding floats.
const r = (n: number) => Math.round(n * 10) / 10;

// Pure render: no useState, no effects, no fetch. Ideal component shape.
export function MealPlanPane({ plan, updating }: MealPlanPaneProps) {
  const totals = dayTotals(plan);

  return (
    <section className="pane" aria-label="Meal plan">
      <div className="plan-header">
        <h2>Your meal plan {updating && <span className="muted small">· updating…</span>}</h2>
        <span className="plan-total">{r(totals.calories)} kcal</span>
      </div>

      <div className="day-totals" aria-label="Daily macro totals">
        <span>P {r(totals.protein_g)}g</span>
        <span>C {r(totals.carbs_g)}g</span>
        <span>F {r(totals.fat_g)}g</span>
      </div>

      {plan.meals.map((meal, idx) => (
        // React needs a stable `key` prop when rendering lists so it can
        // efficiently diff between renders. Using the index is OK here
        // because meals don't get reordered — if they did, we'd want a
        // real unique ID.
        <div className="meal" key={idx}>
          <div className="meal-head">
            <h3>{meal.name}</h3>
            <span className="macros">
              {r(meal.calories)} kcal · P {r(meal.protein_g)}g · C {r(meal.carbs_g)}g · F {r(meal.fat_g)}g
            </span>
          </div>

          {meal.description && (
            <p className="meal-desc muted small">{meal.description}</p>
          )}

          <ul className="food-list">
            {meal.ingredients.map((food, fIdx) => (
              <li className="food-row" key={fIdx}>
                <span className="food-name">{food.name}</span>
                <span className="food-macros">
                  {r(food.calories)} kcal · P {r(food.protein_g)}g · C {r(food.carbs_g)}g · F {r(food.fat_g)}g
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {plan.notes && <div className="plan-notes">{plan.notes}</div>}
    </section>
  );
}
