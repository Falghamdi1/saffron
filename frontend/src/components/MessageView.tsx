import { useLanguage } from "../i18n";
import type { MemoryAction, MemoryNote, Memory, Message } from "../types";
import CompareTable from "./CompareTable";
import DishEntry from "./DishEntry";
import Icon from "./Icons";
import type { DishActions } from "./Workspace";

interface Props {
  message: Message;
  memory: Memory | null;
  dishActions: DishActions;
  onChangeMemory: (id: string, action: MemoryAction) => Promise<void>;
}

const NOTE_ICONS: Record<MemoryNote["kind"], "note" | "info" | "warning"> = {
  saved: "note",
  updated: "note",
  removed: "note",
  temporary: "info",
  needs_confirmation: "info",
  conflict: "warning",
};

export default function MessageView({ message, memory, dishActions, onChangeMemory }: Props) {
  const { t } = useLanguage();
  if (message.role === "user") {
    return (
      <p className="bg-pine text-paper rounded-panel ms-auto w-fit max-w-[85%] px-4 py-2.5 break-words">
        <span className="sr-only">{t.youSaid}</span>
        <bdi>{message.content}</bdi>
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

  const dishes = recommendations.length
    ? recommendations
    : comparison.length === 1
      ? comparison
      : [];

  return (
    <div className="flex flex-col gap-3">
      {memory_notes.length > 0 && (
        <ul className="border-line divide-line divide-y border-y text-sm" aria-label={t.memoryUpdates}>
          {memory_notes.map((note) => {
            const preference = awaiting(note.preference_id);
            return (
              <li
                key={note.message}
                className={`flex gap-2 py-2 ${preference ? "bg-notice px-3" : ""} ${
                  note.kind === "conflict" ? "text-alert" : ""
                }`}
              >
                <Icon name={NOTE_ICONS[note.kind]} className="text-herb mt-0.5" />
                <div className="min-w-0 flex-1">
                  <p dir="auto">{note.message}</p>
                  {preference && (
                    <span className="mt-2 flex flex-wrap gap-2">
                      <button
                        className="btn btn-primary"
                        onClick={() => void onChangeMemory(preference.id, "confirm")}
                      >
                        {preference.removal_requested ? t.yesRemove : t.yesRemember}
                      </button>
                      <button
                        className="btn btn-quiet"
                        onClick={() => void onChangeMemory(preference.id, "dismiss")}
                      >
                        {preference.removal_requested ? t.keep : t.no}
                      </button>
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {text && (
        <p dir="auto" className="leading-relaxed">
          {text}
        </p>
      )}

      {/* One sheet holding the dishes, not a card for each. */}
      {dishes.length > 0 && (
        <ul className="bg-card border-line divide-line rounded-panel divide-y border px-4">
          {dishes.map((dish) => (
            <li key={dish.item.id} className="py-4">
              <DishEntry
                item={dish.item}
                reasons={"reasons" in dish ? dish.reasons : undefined}
                cautions={"cautions" in dish ? dish.cautions : undefined}
                violations={"violations" in dish ? dish.violations : undefined}
                actions={dishActions}
              />
            </li>
          ))}
        </ul>
      )}

      {comparison.length > 1 && (
        <CompareTable
          items={comparison.map((entry) => entry.item)}
          violations={comparison.map((entry) => entry.violations)}
        />
      )}

      {notice && (
        <p dir="auto" className="text-alert flex gap-2 text-[13px] leading-relaxed">
          <Icon name="warning" className="mt-0.5" />
          {notice}
        </p>
      )}
      {(engine === "fallback" || engine === "rules") && (
        <p className="text-muted flex gap-2 text-[13px]">
          <Icon name="info" className="mt-0.5" />
          {t.basic}
        </p>
      )}
    </div>
  );
}
