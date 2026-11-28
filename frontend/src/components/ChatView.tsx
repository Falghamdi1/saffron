import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import type { Api } from "../api";
import { preferenceText } from "../format";
import { useLanguage } from "../i18n";
import type { Conversation, Memory, MemoryAction, Message } from "../types";
import { ErrorBanner, Loading } from "./Feedback";
import Icon from "./Icons";
import MessageView from "./MessageView";
import type { DishActions } from "./Workspace";

const SUGGESTIONS = {
  en: [
    "I'm vegetarian and I love mushrooms",
    "What should I have for dinner under SAR 60?",
    "I'm allergic to nuts. Which desserts can I have?",
    "Compare Butter Chicken and Chicken Vindaloo",
  ],
  ar: [
    "أنا نباتي وأحب الفطر",
    "وش تنصحني للعشا أقل من 60 ريال؟",
    "عندي حساسية من المكسرات. أي حلى أقدر آكل؟",
    "قارن بين دجاج بالزبدة و دجاج فيندالو",
  ],
};

interface Props {
  api: Api;
  memory: Memory | null;
  dishActions: DishActions;
  onMemoryChanged: () => Promise<void>;
  onChangeMemory: (id: string, action: MemoryAction) => Promise<void>;
}

export default function ChatView(props: Props) {
  const { api, memory, dishActions, onMemoryChanged, onChangeMemory } = props;
  const { lang, t } = useLanguage();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState<"idle" | "sending" | "loading">("idle");
  const [error, setError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const question = useRef<HTMLDivElement>(null);

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

  // Long answers start at the question, so memory notes and the reply are not scrolled past.
  useEffect(() => {
    if (messages.at(-1)?.role === "assistant") {
      question.current?.scrollIntoView({ block: "start" });
    } else if (messages.length > 0) {
      bottom.current?.scrollIntoView({ block: "end" });
    }
  }, [messages, busy]);

  const lastQuestion = messages.map((m) => m.role).lastIndexOf("user");

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
    <div className="grid h-full grid-cols-1 md:grid-cols-[14rem_1fr] xl:grid-cols-[15rem_1fr_17rem]">
      <aside
        aria-label={t.past}
        className={`border-line overflow-y-auto overscroll-contain border-e p-3 ${
          historyOpen ? "block" : "hidden md:block"
        }`}
      >
        {historyOpen && (
          <button
            className="btn btn-quiet mb-2 w-full md:hidden"
            onClick={() => setHistoryOpen(false)}
          >
            {t.back}
          </button>
        )}
        <button className="btn btn-quiet w-full" onClick={() => void open(null)}>
          {t.newConversation}
        </button>
        <h2 className="mt-5 mb-1 px-2 text-sm font-semibold">{t.earlier}</h2>
        {conversations.length === 0 && (
          <p className="text-muted px-2 text-sm">{t.noChats}</p>
        )}
        <ul>
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                className={`rounded-control min-h-10 w-full truncate px-2 text-start text-sm pointer-coarse:min-h-11 ${
                  conversation.id === conversationId
                    ? "bg-line/50 font-semibold"
                    : "text-muted hover:text-ink hover:bg-line/30"
                }`}
                aria-current={conversation.id === conversationId ? "true" : undefined}
                title={conversation.title}
                dir="auto"
                onClick={() => void open(conversation.id)}
              >
                {conversation.title}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section
        className={`min-h-0 min-w-0 flex-col ${historyOpen ? "hidden md:flex" : "flex"}`}
        aria-label={t.conversation}
      >
        <div className="border-line flex gap-5 border-b px-4 md:hidden">
          <button className="btn-text" onClick={() => setHistoryOpen(true)}>
            {t.history}
          </button>
          <button className="btn-text" onClick={() => void open(null)}>
            {t.newChat}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-5" aria-live="polite">
          <div className="mx-auto flex max-w-2xl flex-col gap-5">
            {messages.length === 0 && busy === "idle" && (
              <div className="pt-2 sm:pt-8">
                <h2 className="font-display text-3xl font-semibold">{t.mood}</h2>
                <p className="text-muted mt-2 max-w-prose">{t.moodNote}</p>
                <h3 className="mt-7 text-sm font-semibold">{t.tryThese}</h3>
                <ul className="border-line divide-line mt-2 divide-y border-y">
                  {SUGGESTIONS[lang].map((suggestion) => (
                    <li key={suggestion}>
                      <button
                        className="hover:text-pine hover:bg-card flex min-h-12 w-full items-center justify-between gap-3 px-1 text-start"
                        onClick={() => void send(suggestion)}
                      >
                        {suggestion}
                        <Icon name="arrow" className="text-ember" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {messages.map((message, index) => (
              <div key={index} ref={index === lastQuestion ? question : undefined}>
                <MessageView
                  message={message}
                  memory={memory}
                  dishActions={dishActions}
                  onChangeMemory={onChangeMemory}
                />
              </div>
            ))}
            {busy !== "idle" && (
              <Loading label={busy === "sending" ? t.checking : t.openingChat} />
            )}
            {error && <ErrorBanner message={error} />}
            <div ref={bottom} />
          </div>
        </div>

        <form
          onSubmit={submit}
          className="border-line bg-paper border-t px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
        >
          <div className="mx-auto flex max-w-2xl gap-2">
            <label className="sr-only" htmlFor="message">
              {t.message}
            </label>
            <input
              id="message"
              name="message"
              className="field"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={t.placeholder}
              dir="auto"
              maxLength={1000}
              autoComplete="off"
              enterKeyHint="send"
            />
            <button className="btn btn-primary px-5" disabled={!draft.trim() || busy !== "idle"}>
              {t.send}
            </button>
          </div>
        </form>
      </section>

      <aside className="border-line hidden overflow-y-auto border-s p-4 xl:block">
        <h2 className="font-display border-ink border-b pb-1.5 text-lg font-semibold">
          {t.remember}
        </h2>
        {live.length === 0 ? (
          <p className="text-muted mt-2 text-sm">{t.rememberEmpty}</p>
        ) : (
          <ul className="divide-line divide-y">
            {live.map((preference) => (
              <li
                key={preference.id}
                className={`flex gap-2 py-2 text-sm ${
                  preference.category === "allergy" ? "text-alert font-medium" : ""
                }`}
              >
                <Icon
                  name={preference.category === "allergy" ? "warning" : "note"}
                  className="mt-0.5"
                />
                <span>
                  {preferenceText(preference, lang)}
                  {(preference.status === "pending" || preference.removal_requested) && (
                    <span className="text-ember block text-xs font-semibold">
                      {t.waiting}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
        <a className="btn-text mt-2" href="#preferences">
          {t.review}
          <Icon name="arrow" />
        </a>
      </aside>
    </div>
  );
}
