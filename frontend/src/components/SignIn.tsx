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

  return (
    <main className="grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      <section className="bg-pine text-paper flex flex-col justify-between gap-10 p-8 lg:p-14">
        <p className="font-display text-saffron text-2xl">Saffron</p>
        <div className="max-w-md">
          <h1 className="font-display text-4xl leading-tight lg:text-5xl">
            A table that remembers how you eat.
          </h1>
          <p className="text-paper/80 mt-4">
            Tell us once about your allergies, tastes and budget. Next time, the suggestions are
            already yours, and you can see and correct everything we remember.
          </p>
        </div>
        <p className="text-paper/60 text-sm">Levantine, Gulf, Indian and Mediterranean kitchen</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <h2 className="font-display text-2xl">
            {local ? "Who is ordering?" : creating ? "Create your account" : "Welcome back"}
          </h2>
          {local && (
            <p className="text-muted text-sm">
              Local demo mode: a name identifies a diner and there is no password.
            </p>
          )}
          <label className="block text-sm font-medium">
            {local ? "Your name" : "Email"}
            <input
              className="field mt-1"
              type={local ? "text" : "email"}
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete={local ? "off" : "email"}
              maxLength={local ? 40 : 254}
              required
            />
          </label>
          {!local && (
            <label className="block text-sm font-medium">
              Password
              <input
                className="field mt-1"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={creating ? "new-password" : "current-password"}
                minLength={8}
                required
              />
            </label>
          )}
          {error && <ErrorBanner message={error} />}
          {info && <p className="bg-herb-soft text-herb rounded-xl px-4 py-3 text-sm">{info}</p>}
          <button className="btn btn-primary w-full py-3" disabled={busy || !identifier.trim()}>
            {busy ? "One moment…" : creating ? "Create account" : "Continue"}
          </button>
          {!local && (
            <button
              type="button"
              className="text-ember w-full text-sm font-semibold"
              onClick={() => setCreating(!creating)}
            >
              {creating ? "I already have an account" : "New here? Create an account"}
            </button>
          )}
        </form>
      </section>
    </main>
  );
}
