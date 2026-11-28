import { useState } from "react";
import { ALLERGENS, label, preferenceText, when } from "../format";
import { useLanguage, type Strings } from "../i18n";
import type { Memory, MemoryAction, Preference } from "../types";

interface Props {
  memory: Memory;
  onChange: (id: string, action: MemoryAction) => Promise<void>;
  onAddAllergy: (allergen: string) => Promise<void>;
}

function AddAllergy({ onAdd }: { onAdd: Props["onAddAllergy"] }) {
  const { lang, t } = useLanguage();
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
        aria-label={t.allergenToAdd}
        value={allergen}
        onChange={(event) => setAllergen(event.target.value)}
      >
        <option value="">{t.addAllergy}</option>
        {ALLERGENS.map((value) => (
          <option key={value} value={value}>
            {label(value, lang)}
          </option>
        ))}
      </select>
      <button className="btn btn-quiet" disabled={!allergen}>
        {t.add}
      </button>
    </form>
  );
}

const GROUPS: { title: keyof Strings; categories: string[]; empty: keyof Strings }[] = [
  { title: "allergiesGroup", categories: ["allergy"], empty: "noneYet" },
  { title: "dietGroup", categories: ["diet"], empty: "noneYet" },
  { title: "tastesGroup", categories: ["like", "dislike", "cuisine", "favorite_dish"], empty: "nothingYet" },
  { title: "spiceGroup", categories: ["spice", "budget"], empty: "nothingYet" },
];

const EVENT_LABELS: Record<string, { en: string; ar: string }> = {
  created: { en: "Added", ar: "أضيف" },
  proposed: { en: "Suggested", ar: "اقتراح" },
  confirmed: { en: "Confirmed", ar: "تأكد" },
  reinforced: { en: "Mentioned again", ar: "ذُكر مجدداً" },
  reaffirmed: { en: "Kept", ar: "أُبقي" },
  superseded: { en: "Replaced", ar: "استُبدل" },
  retracted: { en: "Removed", ar: "حُذف" },
  removal_requested: { en: "Removal asked", ar: "طُلب حذفه" },
  dismissed: { en: "Dismissed", ar: "رُفض" },
};

function Row({ preference, onChange }: { preference: Preference; onChange: Props["onChange"] }) {
  const { lang, t } = useLanguage();
  const waiting = preference.status === "pending" || preference.removal_requested;

  function forget() {
    const template = preference.category === "allergy" ? t.forgetAllergy : t.forgetOther;
    const warning = template.replace("{what}", preferenceText(preference, lang));
    if (window.confirm(warning)) void onChange(preference.id, "forget");
  }

  return (
    <li
      className={`flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:gap-3 ${
        waiting ? "bg-notice px-3" : ""
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{preferenceText(preference, lang)}</p>
        <p className="text-muted text-[13px] break-words">
          {preference.certainty === "confirmed" ? t.confirmed : t.guess} ·{" "}
          {when(preference.updated_at, lang)}
          {preference.source_text && (
            <>
              {" "}
              · {t.from} <bdi>“{preference.source_text}”</bdi>
            </>
          )}
        </p>
        {preference.removal_requested && (
          <p className="text-ember text-[13px] font-semibold">
            {t.removalNote}
          </p>
        )}
        {preference.status === "pending" && preference.category === "allergy" && (
          <p className="text-ember text-[13px] font-semibold">
            {t.precaution}
          </p>
        )}
      </div>
      {waiting ? (
        <span className="flex shrink-0 gap-2">
          <button className="btn btn-primary" onClick={() => void onChange(preference.id, "confirm")}>
            {preference.removal_requested ? t.removeIt : t.confirm}
          </button>
          <button className="btn btn-quiet" onClick={() => void onChange(preference.id, "dismiss")}>
            {preference.removal_requested ? t.keep : t.notRight}
          </button>
        </span>
      ) : (
        <button className="btn-text shrink-0 self-start sm:self-auto" onClick={forget}>
          {t.forget}
          <span className="sr-only">: {preferenceText(preference, lang)}</span>
        </button>
      )}
    </li>
  );
}

export default function MemoryView({ memory, onChange, onAddAllergy }: Props) {
  const { lang, t } = useLanguage();
  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="mx-auto grid max-w-5xl gap-10 px-4 py-5 sm:px-6 lg:grid-cols-[1.4fr_1fr]">
        <section>
          <h1 className="font-display text-3xl font-semibold">{t.aboutYou}</h1>
          <p className="text-muted mt-1 text-sm">{t.private}</p>
          {GROUPS.map((group) => {
            const rows = memory.preferences.filter((p) => group.categories.includes(p.category));
            return (
              <div key={group.title} className="mt-7">
                <h2 className="section-title">{t[group.title]}</h2>
                {rows.length === 0 ? (
                  <p className="text-muted pt-2 text-sm">{t[group.empty]}</p>
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
          <h2 className="section-title">{t.changed}</h2>
          {memory.history.length === 0 ? (
            <p className="text-muted pt-2 text-sm">{t.noChanges}</p>
          ) : (
            <ol className="divide-line divide-y">
              {memory.history.map((event) => (
                <li key={event.id} className="py-2.5 text-sm">
                  <p>
                    <span className="font-semibold">
                      {EVENT_LABELS[event.event_type]?.[lang] ?? event.event_type}:
                    </span>{" "}
                    {preferenceText(event, lang)}
                  </p>
                  <p className="text-muted text-[13px]">
                    {/* Reasons are recorded in English; the event label covers Arabic. */}
                    {lang === "en" && `${event.reason} · `}
                    {when(event.created_at, lang)}
                  </p>
                  {event.source_text && (
                    <p dir="auto" className="text-muted text-[13px] break-words">
                      “{event.source_text}”
                    </p>
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
