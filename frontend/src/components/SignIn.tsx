import { useState, type FormEvent } from "react";
import { useLanguage } from "../i18n";
import type { Session } from "../session";
import type { AppConfig } from "../types";
import { ErrorBanner } from "./Feedback";

interface Props {
  config: AppConfig;
  session: Session;
  onSignedIn: () => void;
}

export default function SignIn({ config, session, onSignedIn }: Props) {
  const { t, toggle } = useLanguage();
  const local = config.auth_mode === "local";
  const [creating, setCreating] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (creating) {
        const message = await session.signUp(identifier.trim(), password);
        if (message) {
          setInfo(message);
          setCreating(false);
          return;
        }
      } else {
        await session.signIn(identifier.trim(), password);
      }
      onSignedIn();
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const action = creating ? t.create : local ? t.start : t.signIn;

  return (
    <main className="grid min-h-dvh content-start lg:grid-cols-[1.1fr_1fr] lg:content-stretch">
      <section className="bg-pine text-paper flex flex-col justify-between gap-6 px-6 py-8 lg:p-14">
        <div className="on-pine flex items-center justify-between gap-4">
          <p className="font-display text-saffron text-2xl font-semibold" translate="no">
            Saffron
          </p>
          <button type="button" className="min-h-11 text-sm underline-offset-4 hover:underline" onClick={toggle}>
            {t.switchTo}
          </button>
        </div>
        <div className="max-w-md">
          <h1 className="font-display text-3xl leading-tight font-semibold lg:text-5xl">
            {t.tagline}
          </h1>
          <p className="text-paper/85 mt-4">{t.intro}</p>
        </div>
        <p className="text-paper/75 hidden text-sm lg:block">{t.kitchen}</p>
      </section>

      <section className="flex items-center justify-center px-6 py-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <h2 className="font-display text-2xl font-semibold">
            {local ? t.who : creating ? t.createTitle : t.welcomeBack}
          </h2>
          {local && (
            <p className="text-muted text-sm">{t.localNote}</p>
          )}
          <label className="block text-sm font-semibold">
            {local ? t.yourName : t.email}
            <input
              className="field mt-1 font-normal"
              name={local ? "name" : "email"}
              type={local ? "text" : "email"}
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete={local ? "off" : "email"}
              spellCheck={false}
              dir={local ? "auto" : "ltr"}
              maxLength={local ? 40 : 254}
              required
            />
          </label>
          {!local && (
            <label className="block text-sm font-semibold">
              {t.password}
              <input
                className="field mt-1 font-normal"
                name="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={creating ? "new-password" : "current-password"}
                minLength={8}
                aria-describedby={creating ? "password-hint" : undefined}
                required
              />
              {creating && (
                <span id="password-hint" className="text-muted mt-1 block font-normal">
                  {t.passwordHint}
                </span>
              )}
            </label>
          )}
          {error && <ErrorBanner message={error} />}
          {info && (
            <p role="status" className="bg-notice rounded-control px-4 py-3 text-sm">
              {info}
            </p>
          )}
          <button className="btn btn-primary w-full" disabled={busy}>
            {busy ? t.busy : action}
          </button>
          {!local && (
            <button
              type="button"
              className="btn-text w-full justify-center"
              onClick={() => {
                setCreating(!creating);
                setError("");
              }}
            >
              {creating ? t.haveAccount : t.newHere}
            </button>
          )}
        </form>
      </section>
    </main>
  );
}
