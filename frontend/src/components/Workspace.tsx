import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api";
import { dishText } from "../format";
import { useLanguage } from "../i18n";
import type { Memory, MemoryAction, MenuItem } from "../types";
import ChatView from "./ChatView";
import CompareDialog from "./CompareDialog";
import { ErrorBanner, Loading } from "./Feedback";
import MemoryView from "./MemoryView";
import MenuView from "./MenuView";

// Each section has its own address, so the back button and bookmarks work.
const SECTIONS = [
  { hash: "#order", label: "order" },
  { hash: "#menu", label: "menu" },
  { hash: "#preferences", label: "preferences" },
] as const;
type Section = (typeof SECTIONS)[number]["hash"];
const MAX_COMPARE = 3;

function currentSection(): Section {
  return SECTIONS.find((s) => s.hash === window.location.hash)?.hash ?? "#order";
}

export interface DishActions {
  compared: MenuItem[];
  favourites: Set<string>;
  toggleCompare: (item: MenuItem) => void;
  addFavourite: (item: MenuItem) => void;
}

export default function Workspace({ api, onSignOut }: { api: Api; onSignOut: () => void }) {
  const { lang, t, toggle } = useLanguage();
  const [section, setSection] = useState<Section>(currentSection);
  const [memory, setMemory] = useState<Memory | null>(null);
  const [error, setError] = useState("");
  const [compared, setCompared] = useState<MenuItem[]>([]);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    const follow = () => setSection(currentSection());
    window.addEventListener("hashchange", follow);
    return () => window.removeEventListener("hashchange", follow);
  }, []);

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
      <a
        href="#content"
        className="bg-card rounded-control sr-only z-10 font-semibold focus:not-sr-only focus:absolute focus:start-2 focus:top-2 focus:px-4 focus:py-2.5"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("content")?.focus();
        }}
      >
        {t.skip}
      </a>
      <header className="on-pine bg-pine text-paper flex flex-wrap items-center justify-between gap-x-6 px-4 sm:px-6">
        <p className="font-display text-saffron py-2 text-2xl font-semibold" translate="no">
          Saffron
        </p>
        <nav
          className="order-last flex w-full gap-6 sm:order-none sm:me-auto sm:w-auto"
          aria-label={t.sections}
        >
          {SECTIONS.map((entry) => (
            <a
              key={entry.hash}
              href={entry.hash}
              aria-current={section === entry.hash ? "page" : undefined}
              className={`flex min-h-11 items-center border-b-[3px] pt-[3px] text-sm font-semibold whitespace-nowrap ${
                section === entry.hash
                  ? "border-saffron text-paper"
                  : "text-paper/75 hover:text-paper border-transparent"
              }`}
            >
              {t[entry.label]}
            </a>
          ))}
        </nav>
        <button
          className="text-paper/75 hover:text-paper min-h-11 text-sm whitespace-nowrap"
          lang={lang === "ar" ? "en" : "ar"}
          onClick={toggle}
        >
          {t.switchTo}
        </button>
        <button
          className="text-paper/75 hover:text-paper min-h-11 text-sm whitespace-nowrap"
          onClick={() => {
            window.history.replaceState(null, "", window.location.pathname);
            onSignOut();
          }}
        >
          {t.signOut}
        </button>
      </header>

      {error && (
        <div className="px-4 pt-3">
          <ErrorBanner message={error} onRetry={() => void refreshMemory()} />
        </div>
      )}

      <main id="content" tabIndex={-1} className="min-h-0 flex-1">
        {section === "#order" && <h1 className="sr-only">{t.orderTitle}</h1>}
        {/* The chat stays mounted so switching sections does not lose the conversation. */}
        <div className={section === "#order" ? "h-full" : "hidden"}>
          <ChatView
            api={api}
            memory={memory}
            dishActions={dishActions}
            onMemoryChanged={refreshMemory}
            onChangeMemory={changeMemory}
          />
        </div>
        {section === "#menu" && <MenuView api={api} dishActions={dishActions} memory={memory} />}
        {section === "#preferences" &&
          (memory ? (
            <MemoryView
              memory={memory}
              onChange={changeMemory}
              onAddAllergy={(allergen) => run(() => api.addAllergy(allergen))}
            />
          ) : (
            !error && <Loading label={t.reading} />
          ))}
      </main>

      {compared.length > 0 && (
        <div className="border-ink bg-card flex items-center justify-between gap-3 border-t px-4 py-2 text-sm">
          <p className="min-w-0 truncate" aria-live="polite">
            <span className="font-semibold">
              {compared.length} {t.toCompare}
            </span>{" "}
            {compared.map((c) => dishText(c, lang).name).join(lang === "ar" ? "، " : ", ")}
          </p>
          <span className="flex shrink-0 gap-2">
            <button className="btn btn-quiet" onClick={() => setCompared([])}>
              {t.clear}
            </button>
            <button
              className="btn btn-primary"
              disabled={compared.length < 2}
              onClick={() => setComparing(true)}
            >
              {t.compare}
            </button>
          </span>
        </div>
      )}
      {comparing && (
        <CompareDialog api={api} items={compared} onClose={() => setComparing(false)} />
      )}
    </div>
  );
}
