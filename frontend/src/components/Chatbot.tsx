import { useState, useRef, useEffect, type FormEvent } from "react";
import { Button, Input } from "@/components/Field";
import { postChat, type ChatTurn } from "@/lib/api";

const SUGGESTIONS = [
  "¿Qué tipo de activo es y qué impulsa su valor?",
  "¿Qué dicen las noticias recientes sobre mi tesis?",
  "¿Cuáles son los principales riesgos y catalizadores?",
];

/** Fundamental-analysis chatbot scoped to one asset. */
export function Chatbot({ ticker }: { ticker: string }) {
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
      const resp = await postChat(ticker, next);
      setMessages([...next, { role: "assistant", content: resp.reply }]);
      setNotice(resp.configured ? null : "Modo demo — configurá ANTHROPIC_API_KEY para respuestas reales.");
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
            <p className="text-sm text-secondary">
              Preguntale al analista de CLARA sobre los fundamentals de{" "}
              <span className="font-medium text-primary">{ticker}</span>.
            </p>
            <div className="mt-3 flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
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
          placeholder={`Preguntá sobre ${ticker}…`}
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
