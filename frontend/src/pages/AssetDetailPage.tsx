import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card } from "@/components/Card";
import { Metric } from "@/components/Metric";
import { SentimentTag } from "@/components/SentimentTag";
import { TechnicalChart } from "@/components/TechnicalChart";
import { Chatbot } from "@/components/Chatbot";
import { Button, Field, Input, Select, Textarea } from "@/components/Field";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi, type ApiState } from "@/hooks/useApi";
import {
  ApiError,
  getAssetSummary,
  getIndicators,
  getNews,
  createAsset,
  createThesis,
  deleteThesis,
  getTheses,
  runIngestion,
  simulatePurchase,
  type AssetSummary,
  type Conviction,
  type SentimentLabel,
  type Simulation,
  type Thesis,
  type ThesisStatus,
} from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  formatSignedCurrency,
  formatSignedPercent,
  pnlColor,
} from "@/lib/format";

type Tab = "resumen" | "noticias" | "tecnico" | "simular" | "tesis" | "chatbot";

const TABS: { id: Tab; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "noticias", label: "Noticias" },
  { id: "tecnico", label: "Análisis técnico" },
  { id: "simular", label: "Simular compra" },
  { id: "tesis", label: "Diario de tesis" },
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
          {tab === "simular" && <SimularTab ticker={ticker} summary={summary.data} />}
          {tab === "tesis" && <TesisTab ticker={ticker} />}
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

/** One category's exposure before vs. after the simulated purchase — only
 * rendered for the asset's own sector/country/currency, since that's what a
 * single purchase can meaningfully move. */
function ExposureShift({
  label,
  category,
  before,
  after,
}: {
  label: string;
  category: string | null;
  before: Record<string, number>;
  after: Record<string, number>;
}) {
  if (!category) return null;
  const b = before[category] ?? 0;
  const a = after[category] ?? 0;
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-secondary">
        {label} · {category}
      </p>
      <p className="tabnum text-base font-medium text-primary">
        {formatPercent(b)} → {formatPercent(a)}
      </p>
    </div>
  );
}

const STATUS_STYLES: Record<ThesisStatus, { label: string; cls: string }> = {
  en_curso: { label: "En curso", cls: "bg-secondary/15 text-secondary" },
  objetivo_alcanzado: { label: "Objetivo alcanzado", cls: "bg-gain/15 text-gain" },
  stop_tocado: { label: "Stop tocado", cls: "bg-loss/15 text-loss" },
  sin_precio: { label: "Sin precio", cls: "bg-secondary/15 text-secondary" },
};

const CONVICTIONS: Conviction[] = ["baja", "media", "alta"];

/** Diario de tesis: por qué se compró, precio objetivo, stop-loss,
 * convicción, y contraste posterior con el resultado real
 * (docs/devlog/BACKLOG.md, v2 item 6). */
function TesisTab({ ticker }: { ticker: string }) {
  const [theses, setTheses] = useState<Thesis[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [conviction, setConviction] = useState<Conviction>("media");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    setLoading(true);
    getTheses(ticker)
      .then(setTheses)
      .finally(() => setLoading(false));
  }

  useEffect(reload, [ticker]);

  async function save() {
    if (!note.trim()) {
      setError("Contá por qué comprarías (o compraste) este activo.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createThesis({
        ticker,
        note: note.trim(),
        target_price: targetPrice ? Number(targetPrice) : null,
        stop_loss: stopLoss ? Number(stopLoss) : null,
        conviction,
      });
      setNote("");
      setTargetPrice("");
      setStopLoss("");
      setConviction("media");
      reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar la tesis");
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: number) {
    await deleteThesis(id);
    reload();
  }

  return (
    <div className="space-y-5">
      <Card title="Nueva entrada" subtitle="Por qué comprarías esto, y a qué precio salís">
        <div className="space-y-3">
          <Field label="Motivo / tesis">
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder={`¿Por qué ${ticker}? Catalizador, tesis de valuación, momentum…`}
            />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="Precio objetivo (opcional)">
              <Input
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                inputMode="decimal"
                placeholder="—"
              />
            </Field>
            <Field label="Stop-loss (opcional)">
              <Input
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                inputMode="decimal"
                placeholder="—"
              />
            </Field>
            <Field label="Convicción">
              <Select value={conviction} onChange={(e) => setConviction(e.target.value as Conviction)}>
                {CONVICTIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Select>
            </Field>
          </div>
          {error && <p className="text-sm text-loss">{error}</p>}
          <Button onClick={save} disabled={saving}>
            {saving ? "Guardando…" : "Guardar tesis"}
          </Button>
        </div>
      </Card>

      <Card title="Historial" subtitle={`Tesis registradas para ${ticker}`}>
        {loading && <Spinner />}
        {theses && theses.length === 0 && (
          <p className="py-4 text-sm text-secondary">Todavía no registraste ninguna tesis.</p>
        )}
        {theses && theses.length > 0 && (
          <ul className="divide-y divide-separator/60">
            {theses.map((t) => {
              const status = STATUS_STYLES[t.status];
              return (
                <li key={t.id} className="py-3.5 first:pt-0">
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${status.cls}`}>
                        {status.label}
                      </span>
                      <span className="text-xs capitalize text-secondary">
                        Convicción {t.conviction}
                      </span>
                    </div>
                    <button
                      onClick={() => remove(t.id)}
                      className="text-xs text-secondary hover:text-loss"
                    >
                      Eliminar
                    </button>
                  </div>
                  <p className="text-sm text-primary">{t.note}</p>
                  <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-secondary">
                    <span>{new Date(t.created_at).toLocaleDateString()}</span>
                    <span>
                      Entrada: {t.price_at_entry != null ? formatCurrency(t.price_at_entry) : "—"}
                    </span>
                    <span>
                      Objetivo: {t.target_price != null ? formatCurrency(t.target_price) : "—"}
                    </span>
                    <span>
                      Stop: {t.stop_loss != null ? formatCurrency(t.stop_loss) : "—"}
                    </span>
                    <span>
                      Actual: {t.current_price != null ? formatCurrency(t.current_price) : "—"}
                      {t.return_since_entry != null && (
                        <span className={`ml-1 ${pnlColor(t.return_since_entry)}`}>
                          ({formatSignedPercent(t.return_since_entry)})
                        </span>
                      )}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}

/** "Qué pasa si compro esto": impacto de una compra hipotética en
 * concentración, exposición y correlación — sin tocar ninguna posición
 * real (docs/devlog/BACKLOG.md, v2 item 5). */
function SimularTab({ ticker, summary }: { ticker: string; summary: AssetSummary | null }) {
  const [amount, setAmount] = useState("1000");
  const [result, setResult] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    const value = Number(amount);
    if (!value || value <= 0) {
      setError("Ingresá un monto válido.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await simulatePurchase(ticker, value));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo simular la compra");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const top3Delta = result ? result.top3_after - result.top3_before : 0;
  const hhiDelta = result ? result.herfindahl_after - result.herfindahl_before : 0;

  return (
    <Card
      title="Simular compra"
      subtitle="Impacto en concentración, exposición y correlación antes de comprar de verdad"
    >
      <div className="mb-5 flex items-end gap-3">
        <div className="w-40">
          <Field label="Monto a invertir (USD)">
            <Input
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              inputMode="decimal"
            />
          </Field>
        </div>
        <Button onClick={run} disabled={loading}>
          {loading ? "Simulando…" : "Simular"}
        </Button>
      </div>

      {error && <p className="mb-4 text-sm text-loss">{error}</p>}

      {result && (
        <div className="space-y-5">
          {result.warnings.length > 0 && (
            <ul className="rounded-control border border-separator bg-separator/20 p-3 text-xs text-secondary">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            <Metric
              label="Cantidad a comprar"
              value={result.quantity_added.toLocaleString("en-US", { maximumFractionDigits: 4 })}
            />
            <Metric label="Peso resultante" value={formatPercent(result.new_weight)} />
            <Metric
              label="Concentración top-3"
              value={formatPercent(result.top3_after)}
              sub={
                <span className={pnlColor(top3Delta)}>
                  {formatSignedPercent(top3Delta)} vs. hoy
                </span>
              }
            />
            <Metric
              label="Herfindahl (HHI)"
              value={result.herfindahl_after.toFixed(3)}
              sub={
                <span className={pnlColor(hhiDelta)}>
                  {hhiDelta >= 0 ? "+" : ""}
                  {hhiDelta.toFixed(3)} vs. hoy
                </span>
              }
            />
          </div>

          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-secondary">
              Correlación con la cartera actual
            </p>
            {result.correlation_to_portfolio !== null ? (
              <p className="text-sm text-primary">
                {result.correlation_to_portfolio.toFixed(2)} —{" "}
                {Math.abs(result.correlation_to_portfolio) < 0.3
                  ? "buena diversificación"
                  : result.correlation_to_portfolio > 0.7
                    ? "se mueve muy parecido a lo que ya tenés"
                    : "correlación moderada"}
              </p>
            ) : (
              <p className="text-sm text-secondary">Sin datos suficientes todavía.</p>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <ExposureShift
              label="Sector"
              category={summary?.sector ?? null}
              before={result.exposure_before.sector}
              after={result.exposure_after.sector}
            />
            <ExposureShift
              label="País"
              category={summary?.country ?? null}
              before={result.exposure_before.country}
              after={result.exposure_after.country}
            />
            <ExposureShift
              label="Moneda"
              category={summary?.currency ?? null}
              before={result.exposure_before.currency}
              after={result.exposure_after.currency}
            />
          </div>
        </div>
      )}
    </Card>
  );
}
