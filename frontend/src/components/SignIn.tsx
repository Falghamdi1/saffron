import { useState, type FormEvent } from "react";
import type { Session } from "../session";
import type { AppConfig } from "../types";
import { ErrorBanner } from "./Feedback";

interface Props {
  config: AppConfig;
  session: Session;
  onSignedIn: () => void;
}

export default function SignIn({ config, session, onSignedIn }: Props) {
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

  const action = creating ? "Create account" : local ? "Start ordering" : "Sign in";

  return (
    <main className="grid min-h-dvh content-start lg:grid-cols-[1.1fr_1fr] lg:content-stretch">
      <section className="bg-pine text-paper flex flex-col justify-between gap-6 px-6 py-8 lg:p-14">
        <p className="font-display text-saffron text-2xl font-semibold" translate="no">
          Saffron
        </p>
        <div className="max-w-md">
          <h1 className="font-display text-3xl leading-tight font-semibold lg:text-5xl">
            A table that remembers how you eat.
          </h1>
          <p className="text-paper/85 mt-4">
            Tell us once about your allergies, tastes and budget. Next time the suggestions already
            fit, and you can see and correct everything we remember.
          </p>
        </div>
        <p className="text-paper/75 hidden text-sm lg:block">
          Levantine, Gulf, Indian and Mediterranean kitchen
        </p>
      </section>

      <section className="flex items-center justify-center px-6 py-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <h2 className="font-display text-2xl font-semibold">
            {local ? "Who is ordering?" : creating ? "Create your account" : "Welcome back"}
          </h2>
          {local && (
            <p className="text-muted text-sm">
              Local demo mode: a name identifies a diner and there is no password.
            </p>
          )}
          <label className="block text-sm font-semibold">
            {local ? "Your name" : "Email"}
            <input
              className="field mt-1 font-normal"
              name={local ? "name" : "email"}
              type={local ? "text" : "email"}
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete={local ? "off" : "email"}
              spellCheck={false}
              maxLength={local ? 40 : 254}
              required
            />
          </label>
          {!local && (
            <label className="block text-sm font-semibold">
              Password
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
                  At least 8 characters.
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
            {busy ? "One moment…" : action}
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
              {creating ? "I already have an account" : "New here? Create an account"}
            </button>
          )}
        </form>
      </section>
    </main>
  );
}
