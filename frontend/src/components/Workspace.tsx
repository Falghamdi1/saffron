import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api";
import type { Memory, MemoryAction, MenuItem } from "../types";
import ChatView from "./ChatView";
import CompareDialog from "./CompareDialog";
import { ErrorBanner, Loading } from "./Feedback";
import MemoryView from "./MemoryView";
import MenuView from "./MenuView";

type Tab = "order" | "menu" | "memory";
const TABS: { id: Tab; label: string }[] = [
  { id: "order", label: "Order" },
  { id: "menu", label: "Menu" },
  { id: "memory", label: "My preferences" },
];
const MAX_COMPARE = 3;

export interface DishActions {
  compared: MenuItem[];
  favourites: Set<string>;
  toggleCompare: (item: MenuItem) => void;
  addFavourite: (item: MenuItem) => void;
}

export default function Workspace({ api, onSignOut }: { api: Api; onSignOut: () => void }) {
  const [tab, setTab] = useState<Tab>("order");
  const [memory, setMemory] = useState<Memory | null>(null);
  const [error, setError] = useState("");
  const [compared, setCompared] = useState<MenuItem[]>([]);
  const [comparing, setComparing] = useState(false);

  const run = useCallback(async (action: () => Promise<Memory>) => {
    setError("");
    try {
      setMemory(await action());
    } catch (caught) {
      setError((caught as Error).message);
    }
  }, []);

  const refreshMemory = useCallback(() => run(() => api.memory()), [api, run]);

  useEffect(() => {
    void refreshMemory();
  }, [refreshMemory]);

  const changeMemory = (id: string, action: MemoryAction) => run(() => api.changeMemory(id, action));

  const dishActions: DishActions = {
    compared,
    favourites: new Set(
      memory?.preferences.filter((p) => p.category === "favorite_dish").map((p) => p.value),
    ),
    toggleCompare: (item) =>
      setCompared((current) =>
        current.some((c) => c.id === item.id)
          ? current.filter((c) => c.id !== item.id)
          : [...current, item].slice(-MAX_COMPARE),
      ),
    addFavourite: (item) =>
      void run(async () => {
        await api.addFavourite(item.id);
        return api.memory();
      }),
  };

  return (
    <div className="flex h-dvh flex-col">
      <header className="bg-pine text-paper flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-2.5 sm:px-6">
        <p className="font-display text-saffron text-xl">Saffron</p>
        <nav
          className="order-last flex w-full justify-center gap-1 sm:order-none sm:w-auto"
          aria-label="Sections">
          {TABS.map((entry) => (
            <button
              key={entry.id}
              onClick={() => setTab(entry.id)}
              aria-current={tab === entry.id ? "page" : undefined}
              className={`rounded-full px-3 py-1.5 text-sm font-medium whitespace-nowrap ${
                tab === entry.id ? "bg-paper text-pine" : "text-paper/80 hover:text-paper"
              }`}
            >
              {entry.label}
            </button>
          ))}
        </nav>
        <button className="text-paper/80 text-sm whitespace-nowrap" onClick={onSignOut}>
          Sign out
        </button>
      </header>

      {error && (
        <div className="px-4 pt-3">
          <ErrorBanner message={error} onRetry={() => void refreshMemory()} />
        </div>
      )}

      <div className="min-h-0 flex-1">
        {/* The chat stays mounted so switching tabs does not lose the conversation. */}
        <div className={tab === "order" ? "h-full" : "hidden"}>
          <ChatView
            api={api}
            memory={memory}
            dishActions={dishActions}
            onMemoryChanged={refreshMemory}
            onChangeMemory={changeMemory}
            onShowMemory={() => setTab("memory")}
          />
        </div>
        {tab === "menu" && <MenuView api={api} dishActions={dishActions} memory={memory} />}
        {tab === "memory" &&
          (memory ? (
            <MemoryView
              memory={memory}
              onChange={changeMemory}
              onAddAllergy={(allergen) => run(() => api.addAllergy(allergen))}
            />
          ) : (
            !error && <Loading label="Reading your preferences" />
          ))}
      </div>

      {compared.length > 0 && (
        <div className="border-line bg-card flex items-center justify-between gap-3 border-t px-4 py-2 text-sm">
          <span className="truncate">Comparing: {compared.map((c) => c.name).join(", ")}</span>
          <span className="flex shrink-0 gap-2">
            <button className="btn btn-quiet" onClick={() => setCompared([])}>
              Clear
            </button>
            <button
              className="btn btn-primary"
              disabled={compared.length < 2}
              onClick={() => setComparing(true)}
            >
              Compare
            </button>
          </span>
        </div>
      )}
      {comparing && <CompareDialog items={compared} onClose={() => setComparing(false)} />}
    </div>
  );
}
