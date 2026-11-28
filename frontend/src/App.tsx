import { useEffect, useMemo, useState } from "react";
import { createApi } from "./api";
import { ErrorBanner, Loading } from "./components/Feedback";
import SignIn from "./components/SignIn";
import Workspace from "./components/Workspace";
import { applyLanguage, initialLanguage, LanguageContext, useLanguage } from "./i18n";
import { createSession, type Session } from "./session";
import type { AppConfig } from "./types";

export default function App() {
  const [lang, setLang] = useState(initialLanguage);
  useEffect(() => applyLanguage(lang), [lang]);
  const language = useMemo(
    () => ({ lang, toggle: () => setLang(lang === "en" ? "ar" : "en") }),
    [lang],
  );
  return (
    <LanguageContext.Provider value={language}>
      <Screen />
    </LanguageContext.Provider>
  );
}

function Screen() {
  const { t } = useLanguage();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [failed, setFailed] = useState(false);

  async function start() {
    setFailed(false);
    try {
      const response = await fetch("/api/config");
      if (!response.ok) throw new Error();
      const loaded: AppConfig = await response.json();
      const created = createSession(loaded);
      setConfig(loaded);
      setSession(created);
      setSignedIn(Boolean(await created.token()));
    } catch {
      setFailed(true);
    }
  }

  useEffect(() => {
    void start();
  }, []);

  const api = useMemo(
    () => session && createApi(session, () => void session.signOut().then(() => setSignedIn(false))),
    [session],
  );

  if (failed) {
    return (
      <main className="mx-auto max-w-md p-6 pt-24">
        <ErrorBanner message={t.notResponding} onRetry={() => void start()} />
      </main>
    );
  }
  if (!config || !session || !api || signedIn === null) {
    return <div className="mx-auto max-w-md p-6"><Loading label={t.opening} /></div>;
  }
  if (!signedIn) {
    return <SignIn config={config} session={session} onSignedIn={() => setSignedIn(true)} />;
  }
  return (
    <Workspace
      api={api}
      onSignOut={() => void session.signOut().then(() => setSignedIn(false))}
    />
  );
}
