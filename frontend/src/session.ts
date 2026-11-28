import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { currentLanguage, STRINGS } from "./i18n";
import type { AppConfig } from "./types";

// Per-tab storage in local mode, so two tabs can demonstrate two separate diners.
const LOCAL_KEY = "saffron.local-token";

export interface Session {
  token(): Promise<string | null>;
  signIn(identifier: string, password: string): Promise<void>;
  signUp(identifier: string, password: string): Promise<string | null>;
  signOut(): Promise<void>;
}

function localSession(): Session {
  return {
    async token() {
      return sessionStorage.getItem(LOCAL_KEY);
    },
    async signIn(name) {
      const response = await fetch("/api/local-auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) throw new Error(STRINGS[currentLanguage()].nameRule);
      sessionStorage.setItem(LOCAL_KEY, (await response.json()).access_token);
    },
    async signUp(name) {
      await this.signIn(name, "");
      return null;
    },
    async signOut() {
      sessionStorage.removeItem(LOCAL_KEY);
    },
  };
}

function supabaseSession(client: SupabaseClient): Session {
  return {
    async token() {
      const { data } = await client.auth.getSession();
      return data.session?.access_token ?? null;
    },
    async signIn(email, password) {
      const { error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw new Error(STRINGS[currentLanguage()].signInFailed || error.message);
    },
    async signUp(email, password) {
      const { data, error } = await client.auth.signUp({ email, password });
      const strings = STRINGS[currentLanguage()];
      if (error) throw new Error(strings.signInFailed || error.message);
      return data.session ? null : strings.confirmEmail;
    },
    async signOut() {
      await client.auth.signOut();
    },
  };
}

export function createSession(config: AppConfig): Session {
  return config.auth_mode === "local"
    ? localSession()
    : supabaseSession(createClient(config.supabase_url, config.supabase_anon_key));
}
