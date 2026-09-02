import { useState, useRef, useEffect, type FormEvent, type ReactNode } from "react";
import { Button, Input } from "@/components/Field";
import { type ChatResponse, type ChatTurn } from "@/lib/api";

interface ChatbotProps {
  /** Sends the full conversation so far and resolves with the reply. */
  send: (messages: ChatTurn[]) => Promise<ChatResponse>;
  intro: ReactNode;
  suggestions: string[];
  placeholder: string;
}

/** Chat UI shared by the per-asset and portfolio-wide assistants — only the
 * backend call, intro copy and suggestions differ between them. */
export function Chatbot({ send: sendMessage, intro, suggestions, placeholder }: ChatbotProps) {
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    const next: ChatTurn[] = [...messages, { role: "user", content: question }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const resp = await sendMessage(next);
      setMessages([...next, { role: "assistant", content: resp.reply }]);
      setNotice(resp.configured ? null : "Modo estático — configurá GROQ_API_KEY en .env para respuestas conversacionales.");
    } catch (e) {
      setMessages([
        ...next,
        {
          role: "assistant",
          content:
            e instanceof Error ? `Error: ${e.message}` : "Ocurrió un error.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[28rem] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 && (
          <div className="py-4">
            <p className="text-sm text-secondary">{intro}</p>
            <div className="mt-3 flex flex-col gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-control border border-separator px-3 py-2 text-left text-sm text-secondary transition-colors duration-150 hover:bg-separator/40 hover:text-primary"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            <div
              className={[
                "max-w-[85%] whitespace-pre-wrap rounded-card px-3 py-2 text-sm",
                m.role === "user"
                  ? "bg-accent/15 text-primary"
                  : "border border-separator bg-surface text-primary",
              ].join(" ")}
            >
              {m.content}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex justify-start">
            <div className="rounded-card border border-separator bg-surface px-3 py-2 text-sm text-secondary">
              <span className="inline-flex gap-1">
                <Dot /> <Dot /> <Dot />
              </span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {notice && <p className="pt-2 text-xs text-warn">{notice}</p>}

      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          void send(input);
        }}
        className="mt-3 flex gap-2"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={busy}
        />
        <Button type="submit" disabled={busy || !input.trim()}>
          Enviar
        </Button>
      </form>
    </div>
  );
}

function Dot() {
  return <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-secondary" />;
}
