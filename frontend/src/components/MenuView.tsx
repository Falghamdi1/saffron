import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api";
import type { Memory, MenuEntry } from "../types";
import DishCard from "./DishCard";
import { ErrorBanner, Loading } from "./Feedback";
import type { DishActions } from "./Workspace";

const SECTIONS = [
  ["starter", "Starters"],
  ["main", "Mains"],
  ["dessert", "Desserts"],
  ["drink", "Drinks"],
] as const;

interface Props {
  api: Api;
  memory: Memory | null;
  dishActions: DishActions;
}

export default function MenuView({ api, memory, dishActions }: Props) {
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

  // Reload when memory changes, because the suitability flags depend on it.
  useEffect(() => {
    void load();
  }, [load, memory]);

  const visible = items?.filter((item) => !suitableOnly || item.violations.length === 0) ?? [];

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-2xl">The menu</h1>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="accent-pine size-4"
              checked={suitableOnly}
              onChange={(event) => setSuitableOnly(event.target.checked)}
            />
            Only dishes that suit me
          </label>
        </div>
        {error && <ErrorBanner message={error} onRetry={() => void load()} />}
        {!items && !error && <Loading label="Fetching the menu" />}
        {items && visible.length === 0 && (
          <p className="text-muted mt-6">No dishes match all of your requirements today.</p>
        )}
        {SECTIONS.map(([category, title]) => {
          const section = visible.filter((item) => item.category === category);
          if (section.length === 0) return null;
          return (
            <section key={category} className="mt-6">
              <h2 className="eyebrow mb-2">{title}</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {section.map((item) => (
                  <DishCard
                    key={item.id}
                    item={item}
                    violations={item.violations}
                    actions={dishActions}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
