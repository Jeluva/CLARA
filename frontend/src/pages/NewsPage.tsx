import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { SentimentTag } from "@/components/SentimentTag";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import {
  getNews,
  getNewsSentiment,
  getTranscripts,
  type NewsItem,
} from "@/lib/api";

/** Tab 2 — Noticias & Sentimiento. */
export function NewsPage() {
  const sentiment = useApi(getNewsSentiment);
  const transcripts = useApi(getTranscripts);

  const [ticker, setTicker] = useState<string | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [newsError, setNewsError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setNewsLoading(true);
    getNews(ticker ?? undefined)
      .then((d) => active && (setNews(d), setNewsError(null)))
      .catch((e) => active && setNewsError(e?.message ?? "Error"))
      .finally(() => active && setNewsLoading(false));
    return () => {
      active = false;
    };
  }, [ticker]);

  return (
    <div>
      <PageHeader
        title="Noticias & Sentimiento"
        question="¿Qué pasa con mis activos y cómo afecta mi tesis?"
      />

      {/* Aggregate sentiment by ticker */}
      <Card
        title="Sentimiento por activo"
        subtitle="Promedio sobre las noticias de cada ticker"
        className="mb-5"
      >
        {sentiment.loading && <Spinner />}
        {sentiment.error && <ErrorState message={sentiment.error} />}
        {sentiment.data && (
          <div className="flex flex-wrap gap-2">
            <FilterChip
              active={ticker === null}
              onClick={() => setTicker(null)}
              label="Todos"
            />
            {sentiment.data.map((t) => (
              <button
                key={t.ticker}
                onClick={() =>
                  setTicker(ticker === t.ticker ? null : t.ticker)
                }
                className={`flex items-center gap-2 rounded-control border px-3 py-1.5 text-sm transition-colors duration-150 ${
                  ticker === t.ticker
                    ? "border-accent bg-accent/10"
                    : "border-separator hover:bg-separator/40"
                }`}
              >
                <span className="font-medium text-primary">{t.ticker}</span>
                <SentimentTag label={t.label} score={t.score} />
              </button>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* News feed */}
        <div className="lg:col-span-2">
          <Card
            title="Noticias"
            subtitle={ticker ? `Filtrado: ${ticker}` : "Todas las fuentes"}
          >
            {newsLoading && <Spinner />}
            {newsError && <ErrorState message={newsError} />}
            {!newsLoading && !newsError && news.length === 0 && (
              <p className="py-6 text-sm text-secondary">Sin noticias</p>
            )}
            <ul className="divide-y divide-separator/60">
              {news.map((n) => (
                <li key={n.id} className="py-3.5 first:pt-0">
                  <div className="mb-1 flex items-center gap-2">
                    {n.ticker && (
                      <span className="rounded bg-separator/60 px-1.5 py-0.5 text-xs font-medium text-primary">
                        {n.ticker}
                      </span>
                    )}
                    <SentimentTag label={n.sentiment_label} score={n.sentiment} />
                    <span className="text-xs text-secondary">
                      {n.source} · {n.published_at}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-primary">{n.title}</p>
                  <p className="mt-0.5 text-sm text-secondary">{n.summary}</p>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        {/* Transcripts */}
        <Card title="Transcripciones" subtitle="YouTube · resumidas">
          {transcripts.loading && <Spinner />}
          {transcripts.error && <ErrorState message={transcripts.error} />}
          <ul className="space-y-4">
            {transcripts.data?.map((t) => (
              <li key={t.id}>
                <div className="mb-1 flex items-center gap-2">
                  <SentimentTag label={t.sentiment_label} score={t.sentiment} />
                  <span className="text-xs text-secondary">
                    {t.source_channel}
                  </span>
                </div>
                <p className="text-sm font-medium text-primary">{t.title}</p>
                <p className="mt-0.5 text-xs text-secondary">{t.summary}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-control border px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
        active
          ? "border-accent bg-accent/10 text-primary"
          : "border-separator text-secondary hover:bg-separator/40"
      }`}
    >
      {label}
    </button>
  );
}
