import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api";
import { useLanguage } from "../i18n";
import type { Memory, MenuEntry } from "../types";
import DishEntry from "./DishEntry";
import { ErrorBanner, Loading } from "./Feedback";
import type { DishActions } from "./Workspace";

const SECTIONS = [
  ["starter", { en: "Starters", ar: "المقبلات" }],
  ["main", { en: "Mains", ar: "الأطباق الرئيسية" }],
  ["dessert", { en: "Desserts", ar: "الحلويات" }],
  ["drink", { en: "Drinks", ar: "المشروبات" }],
] as const;

interface Props {
  api: Api;
  memory: Memory | null;
  dishActions: DishActions;
}

export default function MenuView({ api, memory, dishActions }: Props) {
  const { lang, t } = useLanguage();
  const [items, setItems] = useState<MenuEntry[] | null>(null);
  const [error, setError] = useState("");
  const [suitableOnly, setSuitableOnly] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      setItems(await api.menu());
    } catch (caught) {
      setError((caught as Error).message);
    }
  }, [api]);

  // Reload when memory or language changes: the suitability notes depend on both.
  useEffect(() => {
    void load();
  }, [load, memory, lang]);

  const visible = items?.filter((item) => !suitableOnly || item.violations.length === 0) ?? [];
  const sections = SECTIONS.map(([category, title]) => ({
    category,
    title: title[lang],
    dishes: visible.filter((item) => item.category === category),
  })).filter((section) => section.dishes.length > 0);

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="mx-auto max-w-4xl px-4 py-5 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
          <h1 className="font-display text-3xl font-semibold">{t.theMenu}</h1>
          <label className="btn-text cursor-pointer">
            <input
              type="checkbox"
              className="size-4"
              checked={suitableOnly}
              onChange={(event) => setSuitableOnly(event.target.checked)}
            />
            {t.onlySuitable}
          </label>
        </div>
        {sections.length > 1 && (
          <nav aria-label={t.courses} className="mt-1 flex flex-wrap gap-x-5">
            {sections.map((section) => (
              <button
                key={section.category}
                className="btn-text"
                onClick={() =>
                  document.getElementById(`course-${section.category}`)?.scrollIntoView()
                }
              >
                {section.title}
              </button>
            ))}
          </nav>
        )}
        {error && <ErrorBanner message={error} onRetry={() => void load()} />}
        {!items && !error && <Loading label={t.fetching} />}
        {items && visible.length === 0 && (
          <p className="text-muted mt-6">{t.nothingSuits}</p>
        )}
        {sections.map((section) => (
          <section key={section.category} id={`course-${section.category}`} className="pt-7">
            <h2 className="section-title">{section.title}</h2>
            <ul className="grid gap-x-12 md:grid-cols-2">
              {section.dishes.map((item) => (
                <li key={item.id} className="border-line flex border-b py-4">
                  <div className="flex w-full flex-col">
                    <DishEntry item={item} violations={item.violations} actions={dishActions} />
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
