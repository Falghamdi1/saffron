import { useState } from "react";
import { ALLERGENS, label, preferenceText, when } from "../format";
import type { Memory, MemoryAction, Preference } from "../types";

interface Props {
  memory: Memory;
  onChange: (id: string, action: MemoryAction) => Promise<void>;
  onAddAllergy: (allergen: string) => Promise<void>;
}

function AddAllergy({ onAdd }: { onAdd: Props["onAddAllergy"] }) {
  const [allergen, setAllergen] = useState("");
  return (
    <form
      className="mt-3 flex gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        void onAdd(allergen).then(() => setAllergen(""));
      }}
    >
      <select
        className="field w-auto text-sm"
        name="allergen"
        aria-label="Allergen to add"
        value={allergen}
        onChange={(event) => setAllergen(event.target.value)}
      >
        <option value="">Add an allergy…</option>
        {ALLERGENS.map((value) => (
          <option key={value} value={value}>
            {label(value)}
          </option>
        ))}
      </select>
      <button className="btn btn-quiet" disabled={!allergen}>
        Add
      </button>
    </form>
  );
}

const GROUPS: { title: string; categories: string[]; empty: string }[] = [
  { title: "Allergies", categories: ["allergy"], empty: "None recorded." },
  { title: "Dietary choices", categories: ["diet"], empty: "None recorded." },
  { title: "Tastes", categories: ["like", "dislike", "cuisine", "favorite_dish"], empty: "Nothing yet." },
  { title: "Spice and budget", categories: ["spice", "budget"], empty: "Nothing yet." },
];

const EVENT_LABELS: Record<string, string> = {
  created: "Added",
  proposed: "Suggested",
  confirmed: "Confirmed",
  reinforced: "Mentioned again",
  reaffirmed: "Kept",
  superseded: "Replaced",
  retracted: "Removed",
  removal_requested: "Removal asked",
  dismissed: "Dismissed",
};

function Row({ preference, onChange }: { preference: Preference; onChange: Props["onChange"] }) {
  const waiting = preference.status === "pending" || preference.removal_requested;

  function forget() {
    const warning =
      preference.category === "allergy"
        ? `Remove “${preferenceText(preference)}”? Dishes containing it may be recommended again.`
        : `Forget “${preferenceText(preference)}”?`;
    if (window.confirm(warning)) void onChange(preference.id, "forget");
  }

  return (
    <li
      className={`flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:gap-3 ${
        waiting ? "bg-notice px-3" : ""
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{preferenceText(preference)}</p>
        <p className="text-muted text-[13px] break-words">
          {preference.certainty === "confirmed" ? "Confirmed" : "Unconfirmed guess"} ·{" "}
          {when(preference.updated_at)}
          {preference.source_text && ` · from “${preference.source_text}”`}
        </p>
        {preference.removal_requested && (
          <p className="text-ember text-[13px] font-semibold">
            You mentioned removing this. It stays in force until you confirm.
          </p>
        )}
        {preference.status === "pending" && preference.category === "allergy" && (
          <p className="text-ember text-[13px] font-semibold">
            Avoided as a precaution until you answer.
          </p>
        )}
      </div>
      {waiting ? (
        <span className="flex shrink-0 gap-2">
          <button className="btn btn-primary" onClick={() => void onChange(preference.id, "confirm")}>
            {preference.removal_requested ? "Remove it" : "Confirm"}
          </button>
          <button className="btn btn-quiet" onClick={() => void onChange(preference.id, "dismiss")}>
            {preference.removal_requested ? "Keep it" : "Not right"}
          </button>
        </span>
      ) : (
        <button className="btn-text shrink-0 self-start sm:self-auto" onClick={forget}>
          Forget<span className="sr-only">: {preferenceText(preference)}</span>
        </button>
      )}
    </li>
  );
}

export default function MemoryView({ memory, onChange, onAddAllergy }: Props) {
  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="mx-auto grid max-w-5xl gap-10 px-4 py-5 sm:px-6 lg:grid-cols-[1.4fr_1fr]">
        <section>
          <h1 className="font-display text-3xl font-semibold">What I remember about you</h1>
          <p className="text-muted mt-1 text-sm">
            Only you can see this. Correct it here, or just tell me in the chat.
          </p>
          {GROUPS.map((group) => {
            const rows = memory.preferences.filter((p) => group.categories.includes(p.category));
            return (
              <div key={group.title} className="mt-7">
                <h2 className="section-title">{group.title}</h2>
                {rows.length === 0 ? (
                  <p className="text-muted pt-2 text-sm">{group.empty}</p>
                ) : (
                  <ul className="divide-line border-line divide-y border-b">
                    {rows.map((preference) => (
                      <Row key={preference.id} preference={preference} onChange={onChange} />
                    ))}
                  </ul>
                )}
                {group.categories.includes("allergy") && <AddAllergy onAdd={onAddAllergy} />}
              </div>
            );
          })}
        </section>

        <section>
          <h2 className="section-title">How it changed</h2>
          {memory.history.length === 0 ? (
            <p className="text-muted pt-2 text-sm">Changes to your preferences will be listed here.</p>
          ) : (
            <ol className="divide-line divide-y">
              {memory.history.map((event) => (
                <li key={event.id} className="py-2.5 text-sm">
                  <p>
                    <span className="font-semibold">
                      {EVENT_LABELS[event.event_type] ?? event.event_type}:
                    </span>{" "}
                    {preferenceText(event)}
                  </p>
                  <p className="text-muted text-[13px]">
                    {event.reason} · {when(event.created_at)}
                  </p>
                  {event.source_text && (
                    <p className="text-muted text-[13px] break-words">“{event.source_text}”</p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}
