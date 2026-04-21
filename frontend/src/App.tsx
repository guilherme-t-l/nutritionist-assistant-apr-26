import { useState } from "react";

import { ChatPane } from "./ChatPane";
import { MealPlanPane } from "./MealPlanPane";
import { OnboardingForm } from "./OnboardingForm";
import type { MealPlan } from "./types";

// `App` owns the state shared between panes: the session ID (required by
// /chat) and the current plan (rendered by MealPlanPane). Child components
// update it via callbacks — standard "lift state up" React pattern.
export function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [chatPending, setChatPending] = useState(false);

  if (!sessionId || !plan) {
    return (
      <OnboardingForm
        onPlanReady={(response) => {
          setSessionId(response.session_id);
          setPlan(response.plan);
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      <ChatPane
        sessionId={sessionId}
        onPlanUpdate={setPlan}
        onPendingChange={setChatPending}
      />
      <MealPlanPane plan={plan} updating={chatPending} />
    </div>
  );
}
