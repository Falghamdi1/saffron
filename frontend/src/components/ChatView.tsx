import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import type { Api } from "../api";
import { preferenceText } from "../format";
import type { Conversation, Memory, MemoryAction, Message } from "../types";
import { ErrorBanner, Loading } from "./Feedback";
import MessageView from "./MessageView";
import type { DishActions } from "./Workspace";

const SUGGESTIONS = [
  "I'm vegetarian and I love mushrooms",
  "What should I have for dinner under SAR 60?",
  "I'm allergic to nuts. Which desserts can I have?",
  "Compare Butter Chicken and Chicken Vindaloo",
];

interface Props {
  api: Api;
  memory: Memory | null;
  dishActions: DishActions;
  onMemoryChanged: () => Promise<void>;
  onChangeMemory: (id: string, action: MemoryAction) => Promise<void>;
  onShowMemory: () => void;
}

export default function ChatView(props: Props) {
  const { api, memory, dishActions, onMemoryChanged, onChangeMemory, onShowMemory } = props;
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState<"idle" | "sending" | "loading">("idle");
  const [error, setError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.conversations());
    } catch (caught) {
      setError((caught as Error).message);
    }
  }, [api]);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages, busy]);

  async function open(id: string | null) {
    setHistoryOpen(false);
    setConversationId(id);
    setMessages([]);
    setError("");
    if (!id) return;
    setBusy("loading");
    try {
      setMessages(await api.messages(id));
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy("idle");
    }
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy !== "idle") return;
    setDraft("");
    setError("");
    setBusy("sending");
    setMessages((current) => [...current, { role: "user", content: message, payload: {} }]);
    try {
      const response = await api.chat(message, conversationId);
      setConversationId(response.conversation_id);
      setMessages((current) => [...current, response.message]);
      await Promise.all([onMemoryChanged(), refreshConversations()]);
    } catch (caught) {
      // Nothing was saved, so return the text to the box for another try.
      setMessages((current) => current.slice(0, -1));
      setDraft(message);
      setError((caught as Error).message);
    } finally {
      setBusy("idle");
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  const live = memory?.preferences ?? [];

  return (
    <div className="grid h-full grid-cols-1 md:grid-cols-[15rem_1fr] xl:grid-cols-[15rem_1fr_18rem]">
      <aside
        className={`border-line overflow-y-auto border-r p-3 ${
          historyOpen ? "block" : "hidden md:block"
        }`}
      >
        {historyOpen && (
          <button className="btn btn-quiet mb-2 w-full md:hidden" onClick={() => setHistoryOpen(false)}>
            Back to chat
          </button>
        )}
        <button className="btn btn-primary w-full" onClick={() => void open(null)}>
          New conversation
        </button>
        <p className="eyebrow mt-4 mb-1 px-2">Previous</p>
        {conversations.length === 0 && (
          <p className="text-muted px-2 text-sm">Your past chats will appear here.</p>
        )}
        <ul>
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                className={`w-full truncate rounded-lg px-2 py-2 text-left text-sm ${
                  conversation.id === conversationId ? "bg-card font-semibold" : "hover:bg-card"
                }`}
                onClick={() => void open(conversation.id)}
              >
                {conversation.title}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section
        className={`min-h-0 flex-col ${historyOpen ? "hidden md:flex" : "flex"}`}
        aria-label="Conversation"
      >
        <div className="border-line flex gap-2 border-b p-2 md:hidden">
          <button className="btn btn-quiet" onClick={() => setHistoryOpen(true)}>
            History
          </button>
          <button className="btn btn-quiet" onClick={() => void open(null)}>
            New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-5" aria-live="polite">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.length === 0 && busy === "idle" && (
              <div className="pt-8 text-center">
                <h2 className="font-display text-3xl">What are you in the mood for?</h2>
                <p className="text-muted mt-2">
                  Mention allergies, tastes or a budget as they come to you. I'll remember them for
                  next time.
                </p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      className="btn btn-quiet font-normal"
                      onClick={() => void send(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message, index) => (
              <MessageView
                key={index}
                message={message}
                memory={memory}
                dishActions={dishActions}
                onChangeMemory={onChangeMemory}
              />
            ))}
            {busy !== "idle" && (
              <Loading label={busy === "sending" ? "Checking the menu" : "Opening conversation"} />
            )}
            {error && <ErrorBanner message={error} />}
            <div ref={bottom} />
          </div>
        </div>

        <form onSubmit={submit} className="border-line bg-paper border-t p-3">
          <div className="mx-auto flex max-w-3xl gap-2">
            <label className="sr-only" htmlFor="message">
              Message
            </label>
            <input
              id="message"
              className="field rounded-full px-5"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="e.g. something light, no dairy"
              maxLength={1000}
              autoComplete="off"
            />
            <button className="btn btn-primary px-5" disabled={!draft.trim() || busy !== "idle"}>
              Send
            </button>
          </div>
        </form>
      </section>

      <aside className="border-line hidden overflow-y-auto border-l p-4 xl:block">
        <h2 className="font-display text-lg">What I remember</h2>
        {live.length === 0 ? (
          <p className="text-muted mt-2 text-sm">
            Nothing yet. Preferences you mention will show up here straight away.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {live.map((preference) => (
              <li
                key={preference.id}
                className={`rounded-xl border px-3 py-2 text-sm ${
                  preference.category === "allergy"
                    ? "border-alert/30 bg-alert-soft"
                    : "border-line bg-card"
                }`}
              >
                {preferenceText(preference)}
                {(preference.status === "pending" || preference.removal_requested) && (
                  <span className="text-ember block text-xs font-semibold">
                    Waiting for your confirmation
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
        <button className="text-ember mt-3 text-sm font-semibold" onClick={onShowMemory}>
          Review and edit →
        </button>
      </aside>
    </div>
  );
}
