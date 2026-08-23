import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card } from "@/components/Card";
import { Metric } from "@/components/Metric";
import { SentimentTag } from "@/components/SentimentTag";
import { TechnicalChart } from "@/components/TechnicalChart";
import { Chatbot } from "@/components/Chatbot";
import { Button } from "@/components/Field";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi, type ApiState } from "@/hooks/useApi";
import {
  ApiError,
  getAssetSummary,
  getIndicators,
  getNews,
  createAsset,
  runIngestion,
  type AssetSummary,
  type SentimentLabel,
} from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  formatSignedCurrency,
  formatSignedPercent,
  pnlColor,
} from "@/lib/format";

type Tab = "resumen" | "noticias" | "tecnico" | "chatbot";

const TABS: { id: Tab; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "noticias", label: "Noticias" },
  { id: "tecnico", label: "Análisis técnico" },
  { id: "chatbot", label: "Chatbot IA" },
];

function sentimentLabel(score: number): SentimentLabel {
  if (score >= 0.05) return "positive";
  if (score <= -0.05) return "negative";
  return "neutral";
}

/** Like useApi, but distinguishes "asset never loaded" (404) from a real
 * error, so the page can offer to add it to the watchlist instead of just
 * showing an error box — the whole point of looking up a ticker on a whim. */
function useAssetSummary(ticker: string) {
  const [state, setState] = useState<{
    data: AssetSummary | null;
    loading: boolean;
    error: string | null;
    notFound: boolean;
  }>({ data: null, loading: true, error: null, notFound: false });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: null, notFound: false });
    getAssetSummary(ticker)
      .then((data) => active && setState({ data, loading: false, error: null, notFound: false }))
      .catch((err: unknown) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setState({ data: null, loading: false, error: null, notFound: true });
        } else {
          setState({
            data: null,
            loading: false,
            error: err instanceof Error ? err.message : "Error desconocido",
            notFound: false,
          });
        }
      });
    return () => {
      active = false;
    };
  }, [ticker, version]);

  return { ...state, reload: () => setVersion((v) => v + 1) };
}

export function AssetDetailPage() {
  const { ticker = "" } = useParams();
  const [tab, setTab] = useState<Tab>("resumen");
  const summary = useAssetSummary(ticker);

  return (
    <div>
      <div className="mb-5">
        <Link to="/" className="text-sm text-accent hover:underline">
          ← Volver a Portfolio
        </Link>
        <div className="mt-2 flex items-baseline gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-primary">
            {ticker}
          </h1>
          {summary.data && (
            <span className="text-sm text-secondary">{summary.data.name}</span>
          )}
        </div>
      </div>

      {summary.notFound ? (
        <WatchlistAddCard ticker={ticker} onAdded={summary.reload} />
      ) : (
        <>
          {/* Tabs */}
          <div className="mb-5 flex gap-1 border-b border-separator">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={[
                  "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors duration-150",
                  tab === t.id
                    ? "border-accent text-primary"
                    : "border-transparent text-secondary hover:text-primary",
                ].join(" ")}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "resumen" && <ResumenTab summary={summary} />}
          {tab === "noticias" && <NoticiasTab ticker={ticker} />}
          {tab === "tecnico" && <TecnicoTab ticker={ticker} />}
          {tab === "chatbot" && (
            <Card title="Análisis fundamental con IA" subtitle={`Asistente sobre ${ticker}`}>
              <Chatbot ticker={ticker} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/** Shown when the ticker isn't loaded as an asset yet — the "solo mirar"
 * entry point: add it to the watchlist (no position required) and pull
 * price + fundamentals for it right away. */
function WatchlistAddCard({ ticker, onAdded }: { ticker: string; onAdded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add() {
    setBusy(true);
    setError(null);
    try {
      await createAsset({
        ticker,
        name: ticker,
        asset_class: "equity",
        sector: "Unknown",
        country: "Unknown",
        currency: "USD",
      });
      onAdded();
      // Best-effort: pull price + fundamentals now instead of making the
      // user find the buttons in Ingreso de datos. Ingestion covers every
      // asset and is idempotent, so this is safe to fire in the background.
      void runIngestion("prices");
      void runIngestion("fundamentals");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo agregar el activo");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={`${ticker} no está en seguimiento`}>
      <p className="mb-4 text-sm text-secondary">
        Agregalo para ver precio, técnico, noticias y fundamentals — sin
        necesidad de cargar una posición.
      </p>
      {error && <p className="mb-3 text-sm text-loss">{error}</p>}
      <Button onClick={add} disabled={busy}>
        {busy ? "Agregando…" : `Agregar ${ticker} a seguimiento`}
      </Button>
    </Card>
  );
}

function ResumenTab({ summary }: { summary: ApiState<AssetSummary> }) {
  if (summary.loading) return <Card><Spinner /></Card>;
  if (summary.error) return <Card><ErrorState message={summary.error} /></Card>;
  if (!summary.data) return null;
  const s = summary.data;

  return (
    <div className="space-y-5">
      <Card title="Datos del activo">
        <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
          <Metric label="Clase" value={<span className="text-base">{s.asset_class}</span>} />
          <Metric label="Sector" value={<span className="text-base">{s.sector}</span>} />
          <Metric label="País" value={<span className="text-base">{s.country}</span>} />
          <Metric label="Moneda" value={<span className="text-base">{s.currency}</span>} />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Mercado">
          <div className="grid grid-cols-2 gap-6">
            <Metric label="Último precio" value={s.latest_price !== null ? formatCurrency(s.latest_price) : "—"} />
            <Metric
              label="Rendimiento período"
              value={
                s.total_return !== null ? (
                  <span className={pnlColor(s.total_return)}>{formatSignedPercent(s.total_return)}</span>
                ) : "—"
              }
            />
            <Metric label="Volatilidad (anual.)" value={s.volatility !== null ? formatPercent(s.volatility) : "—"} />
            <Metric
              label="Max drawdown"
              value={s.max_drawdown !== null ? <span className="text-loss">{formatPercent(s.max_drawdown)}</span> : "—"}
            />
          </div>
        </Card>

        <Card title="Tu posición">
          {s.position ? (
            <div className="grid grid-cols-2 gap-6">
              <Metric label="Cantidad" value={s.position.quantity.toLocaleString("en-US")} />
              <Metric label="Costo prom." value={formatCurrency(s.position.avg_cost)} />
              <Metric label="Valor de mercado" value={formatCurrency(s.position.market_value)} />
              <Metric
                label="P&L"
                value={<span className={pnlColor(s.position.pnl)}>{formatSignedCurrency(s.position.pnl)}</span>}
                sub={<span className={pnlColor(s.position.pnl)}>{formatSignedPercent(s.position.pnl_pct)}</span>}
              />
            </div>
          ) : (
            <p className="py-6 text-sm text-secondary">No tenés posición abierta en este activo.</p>
          )}
        </Card>
      </div>

      <Card title="Sentimiento de noticias">
        <div className="flex items-center gap-3">
          {s.avg_sentiment !== null ? (
            <SentimentTag label={sentimentLabel(s.avg_sentiment)} score={s.avg_sentiment} />
          ) : (
            <span className="text-sm text-secondary">Sin noticias</span>
          )}
          <span className="text-sm text-secondary">{s.news_count} noticias recientes</span>
        </div>
      </Card>
    </div>
  );
}

function NoticiasTab({ ticker }: { ticker: string }) {
  const news = useApi(() => getNews(ticker));
  return (
    <Card title="Noticias" subtitle={ticker}>
      {news.loading && <Spinner />}
      {news.error && <ErrorState message={news.error} />}
      {news.data && news.data.length === 0 && (
        <p className="py-6 text-sm text-secondary">Sin noticias para este activo.</p>
      )}
      <ul className="divide-y divide-separator/60">
        {news.data?.map((n) => (
          <li key={n.id} className="py-3.5 first:pt-0">
            <div className="mb-1 flex items-center gap-2">
              <SentimentTag label={n.sentiment_label} score={n.sentiment} />
              <span className="text-xs text-secondary">{n.source} · {n.published_at}</span>
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
  );
}

function TecnicoTab({ ticker }: { ticker: string }) {
  const indicators = useApi(() => getIndicators(ticker));
  return (
    <Card title="Análisis técnico" subtitle="Medias móviles, RSI y MACD">
      {indicators.loading && <Spinner />}
      {indicators.error && <ErrorState message={indicators.error} />}
      {indicators.data && <TechnicalChart points={indicators.data.points} />}
    </Card>
  );
}
