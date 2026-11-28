import { currentLanguage, STRINGS } from "./i18n";
import type { Session } from "./session";
import type { Conversation, Memory, MemoryAction, MenuEntry, Message } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export function createApi(session: Session, onUnauthorised: () => void) {
  async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
    const token = await session.token();
    let response: Response;
    try {
      response = await fetch(`/api${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          ...(body ? { "Content-Type": "application/json" } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new ApiError(STRINGS[currentLanguage()].offline, 0);
    }
    if (response.status === 401) onUnauthorised();
    if (!response.ok) {
      const detail = await response
        .json()
        .then((data) => data.detail)
        .catch(() => null);
      const lang = currentLanguage();
      // Server messages are English, so Arabic readers get a translated equivalent.
      const known = response.status === 429 ? STRINGS[lang].tooFast : STRINGS[lang].wrong;
      throw new ApiError(
        lang === "en" && typeof detail === "string" ? detail : known,
        response.status,
      );
    }
    return response.json() as Promise<T>;
  }

  return {
    chat: (message: string, conversationId: string | null) =>
      request<{ conversation_id: string; message: Message }>("/chat", "POST", {
        message,
        conversation_id: conversationId,
      }),
    conversations: () => request<Conversation[]>("/conversations"),
    messages: (id: string) => request<Message[]>(`/conversations/${id}/messages`),
    menu: () => request<MenuEntry[]>(`/menu?lang=${currentLanguage()}`),
    memory: () => request<Memory>("/memory"),
    changeMemory: (id: string, action: MemoryAction) =>
      action === "forget"
        ? request<Memory>(`/memory/${id}`, "DELETE")
        : request<Memory>(`/memory/${id}/${action}`, "POST"),
    addAllergy: (allergen: string) => request<Memory>("/memory/allergies", "POST", { allergen }),
    addFavourite: (itemId: string) =>
      request<unknown>(`/favorites/${itemId}?lang=${currentLanguage()}`, "POST"),
  };
}

export type Api = ReturnType<typeof createApi>;
