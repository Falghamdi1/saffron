import type { MemoryAction, MemoryNote, Memory, Message } from "../types";
import CompareTable from "./CompareTable";
import DishCard from "./DishCard";
import type { DishActions } from "./Workspace";

interface Props {
  message: Message;
  memory: Memory | null;
  dishActions: DishActions;
  onChangeMemory: (id: string, action: MemoryAction) => Promise<void>;
}

const NOTE_STYLES: Record<MemoryNote["kind"], string> = {
  saved: "bg-herb-soft text-herb",
  updated: "bg-herb-soft text-herb",
  removed: "bg-card text-muted",
  temporary: "bg-card text-muted",
  needs_confirmation: "bg-amber-100 text-amber-950",
  conflict: "bg-alert-soft text-alert",
};

export default function MessageView({ message, memory, dishActions, onChangeMemory }: Props) {
  if (message.role === "user") {
    return (
      <p className="bg-pine text-paper ml-auto max-w-[85%] rounded-2xl rounded-br-md px-4 py-2.5">
        {message.content}
      </p>
    );
  }
  const { recommendations = [], comparison = [], memory_notes = [], notice, engine } =
    message.payload;
  // Memory notes are shown as their own list, so remove them from the opening text.
  const text = memory_notes
    .reduce((remaining, note) => remaining.replace(note.message, ""), message.content)
    .trim();

  // A button is offered only while that preference is still awaiting an answer.
  const awaiting = (id: string | null) =>
    memory?.preferences.find((p) => p.id === id && (p.status === "pending" || p.removal_requested));

  return (
    <div className="flex flex-col gap-3">
      {memory_notes.length > 0 && (
        <ul className="space-y-1.5" aria-label="Memory updates">
          {memory_notes.map((note) => {
            const preference = awaiting(note.preference_id);
            return (
              <li key={note.message} className={`rounded-xl px-3 py-2 text-sm ${NOTE_STYLES[note.kind]}`}>
                {note.message}
                {preference && (
                  <span className="mt-1.5 flex gap-2">
                    <button
                      className="btn btn-primary px-3 py-1 text-xs"
                      onClick={() => void onChangeMemory(preference.id, "confirm")}
                    >
                      {preference.removal_requested ? "Yes, remove it" : "Yes, remember"}
                    </button>
                    <button
                      className="btn btn-quiet px-3 py-1 text-xs"
                      onClick={() => void onChangeMemory(preference.id, "dismiss")}
                    >
                      {preference.removal_requested ? "Keep it" : "No"}
                    </button>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {text && <p>{text}</p>}

      {recommendations.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          {recommendations.map((recommendation) => (
            <DishCard
              key={recommendation.item.id}
              item={recommendation.item}
              reasons={recommendation.reasons}
              cautions={recommendation.cautions}
              actions={dishActions}
            />
          ))}
        </div>
      )}

      {comparison.length === 1 && (
        <div className="max-w-sm">
          <DishCard
            item={comparison[0].item}
            violations={comparison[0].violations}
            actions={dishActions}
          />
        </div>
      )}
      {comparison.length > 1 && (
        <CompareTable
          items={comparison.map((entry) => entry.item)}
          violations={comparison.map((entry) => entry.violations)}
        />
      )}

      {notice && (
        <p className="border-alert/40 text-alert border-l-2 pl-3 text-xs leading-relaxed">{notice}</p>
      )}
      {(engine === "fallback" || engine === "rules") && (
        <p className="text-muted text-xs">
          I read this message with basic phrase matching and may have missed something. Please check
          “My preferences”, especially for allergies.
        </p>
      )}
    </div>
  );
}
