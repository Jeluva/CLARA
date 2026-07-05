import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { SentimentTag } from "@/components/SentimentTag";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import {
  getNews,
  getNewsSentiment,
  getSentimentSeries,
  getTranscripts,
  type NewsItem,
  type SentimentPoint,
} from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { colors } from "@/styles/theme";

/** Tab 2 — Noticias & Sentimiento. */
export function NewsPage() {
  const sentiment = useApi(getNewsSentiment);
  const transcripts = useApi(getTranscripts);

  const [ticker, setTicker] = useState<string | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [newsError, setNewsError] = useState<string | null>(null);
  const [series, setSeries] = useState<SentimentPoint[]>([]);

  useEffect(() => {
    let active = true;
    setNewsLoading(true);
    Promise.all([
      getNews(ticker ?? undefined),
      getSentimentSeries(ticker ?? undefined),
    ])
      .then(([n, s]) => {
        if (!active) return;
        setNews(n);
        setSeries(s);
        setNewsError(null);
      })
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

      {series.length > 1 && (
        <Card
          title="Tendencia de sentimiento"
          subtitle={ticker ? `Filtrado: ${ticker}` : "Todos los activos"}
          className="mb-5"
        >
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid stroke={colors.separator} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: colors.secondary, fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: colors.separator }}
                  tickFormatter={(d: string) => d.slice(5)}
                />
                <YAxis
                  domain={[-1, 1]}
                  tick={{ fill: colors.secondary, fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                />
                <ReferenceLine y={0} stroke={colors.separator} />
                <Tooltip
                  contentStyle={{
                    background: colors.surface,
                    border: `1px solid ${colors.separator}`,
                    borderRadius: 12,
                    color: colors.primary,
                    fontSize: 12,
                  }}
                  formatter={(value: number) => [value.toFixed(3), "Sentimiento"]}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke={colors.accent}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

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
                  <a
                    href={n.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    {n.title}
                  </a>
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
