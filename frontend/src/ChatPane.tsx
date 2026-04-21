import { useEffect, useRef, useState } from "react";

import { sendChat } from "./api";
import type { MealPlan } from "./types";

// Conversation turn shown in the chat log. Kept small on purpose: the
// backend is the source of truth for the plan; here we only remember what
// the user typed and a short acknowledgement from the agent.
interface Turn {
  role: "user" | "nutri";
  text: string;
}

interface ChatPaneProps {
  sessionId: string;
  // Called whenever /chat succeeds — <App /> uses this to update the plan
  // pane on the right.
  onPlanUpdate: (plan: MealPlan) => void;
  // Flipped by <App /> to true while /chat is in flight, so the plan pane
  // can render an "updating…" hint.
  onPendingChange: (pending: boolean) => void;
}

export function ChatPane({
  sessionId,
  onPlanUpdate,
  onPendingChange,
}: ChatPaneProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // `useRef` gets you a direct handle on a DOM node. We use it to scroll
  // the chat log to the bottom whenever a new turn is appended.
  const logRef = useRef<HTMLDivElement>(null);

  // `useEffect` runs *after* React commits a render. Here we use it to
  // scroll to the bottom any time `turns` changes.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;

    setError(null);
    setDraft("");
    setTurns((current) => [...current, { role: "user", text: message }]);
    setSending(true);
    onPendingChange(true);

    try {
      const response = await sendChat(sessionId, message);
      onPlanUpdate(response.plan);
      setTurns((current) => [
        ...current,
        {
          role: "nutri",
          text: response.plan.notes || "(updated the plan — see the card on the right)",
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSending(false);
      onPendingChange(false);
    }
  }

  return (
    <section className="pane" aria-label="Chat">
      <h2>Refine it</h2>

      <div className="chat-log" ref={logRef}>
        {turns.length === 0 ? (
          <p className="chat-empty">
            Ask for tweaks like <em>"make lunch lighter"</em> or <em>"more Bahian food at dinner"</em>.
          </p>
        ) : (
          turns.map((turn, idx) => (
            <div className={`turn ${turn.role}`} key={idx}>
              <div className="role">{turn.role === "user" ? "you" : "nutri"}</div>
              <div>{turn.text}</div>
            </div>
          ))
        )}
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Type a refinement…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={sending}
        />
        <button type="submit" disabled={sending || !draft.trim()}>
          {sending ? "…" : "Send"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
