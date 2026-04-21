// TypeScript mirrors of the Pydantic classes in agent/schemas.py.
//
// Keep these in sync by hand. If Python adds a field, add it here too —
// the compiler will loudly point out every place in the frontend that
// needs updating.

export type Goal = "lose_weight" | "maintain" | "gain_muscle";

export type FlavorProfile =
  | "savory"
  | "sweet"
  | "spicy"
  | "umami"
  | "sour"
  | "bitter";

export interface UserProfile {
  goal: Goal;
  allergies: string[];
  disliked_ingredients: string[];
  calorie_target: number;
  protein_g_target?: number | null;
  carbs_g_target?: number | null;
  fat_g_target?: number | null;
  cuisine_preferences: string[];
  flavor_profiles: FlavorProfile[];
  meals_per_day: number;
}

export interface Food {
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface Meal {
  name: string;
  description: string;
  ingredients: Food[];
  // Pydantic sends these as `computed_field`s in the JSON, so they're
  // present on the wire — we just have to tell TypeScript they exist.
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealPlan {
  meals: Meal[];
  notes: string;
  total_calories: number;
}

// Shapes of the HTTP responses, mirrored from src/app/routes/*.py.
export interface PlanResponse {
  session_id: string;
  plan: MealPlan;
}

export interface ChatResponse {
  plan: MealPlan;
}
