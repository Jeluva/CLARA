/**
 * Thin API client. Centralises error handling so pages don't repeat fetch
 * logic. Talks to same-origin `/api/...` by default (Vite proxies it to
 * FastAPI in dev); set VITE_API_URL to point at a backend on another origin
 * (e.g. when the frontend and backend are deployed separately).
 */

const BASE = `${import.meta.env.VITE_API_URL ?? ""}/api`;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(`No se pudo contactar el servidor (${path})`, 0);
  }
  if (!resp.ok) {
    // Surface FastAPI's {detail: "..."} message when present.
    let detail = `La petición a ${path} falló (${resp.status})`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new ApiError(detail, resp.status);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function apiDelete(path: string): Promise<void> {
  return request<void>(path, { method: "DELETE" });
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export const getHealth = () => apiGet<HealthResponse>("/health");

// --- Portfolio ---------------------------------------------------------------

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  latest_price: number;
  market_value: number;
  cost_basis: number;
  pnl: number;
  pnl_pct: number;
  weight: number;
  sector: string;
  country: string;
  currency: string;
}

export interface PortfolioOverview {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  positions: Position[];
}

export interface RiskMetrics {
  volatility: number;
  sharpe: number;
  max_drawdown: number;
  beta: number;
  cumulative_return: number;
  top3_concentration: number;
  herfindahl: number;
}

export interface Exposure {
  sector: Record<string, number>;
  country: Record<string, number>;
  currency: Record<string, number>;
}

export interface HistoryPoint {
  date: string;
  portfolio: number;
  benchmark: number | null;
}

export interface Correlation {
  tickers: string[];
  matrix: number[][];
}

/** Query-string suffix for the active portfolio; omitted -> backend merges
 * every portfolio ("Todos"). See docs/devlog/BACKLOG.md v3 item 1. */
function portfolioQS(portfolioId: number | null) {
  return portfolioId !== null ? `?portfolio_id=${portfolioId}` : "";
}

export const getPortfolio = (portfolioId: number | null = null) =>
  apiGet<PortfolioOverview>(`/portfolio${portfolioQS(portfolioId)}`);
export const getMetrics = (portfolioId: number | null = null) =>
  apiGet<RiskMetrics>(`/portfolio/metrics${portfolioQS(portfolioId)}`);
export const getExposure = (portfolioId: number | null = null) =>
  apiGet<Exposure>(`/portfolio/exposure${portfolioQS(portfolioId)}`);
export const getHistory = (portfolioId: number | null = null) =>
  apiGet<HistoryPoint[]>(`/portfolio/history${portfolioQS(portfolioId)}`);

export interface RealizedPoint {
  date: string;
  realized_pnl: number;
}

export const getRealizedHistory = (portfolioId: number | null = null) =>
  apiGet<RealizedPoint[]>(`/portfolio/realized-history${portfolioQS(portfolioId)}`);
export const getCorrelation = () =>
  apiGet<Correlation>("/research/correlation");

export interface Simulation {
  ticker: string;
  amount: number;
  quantity_added: number;
  already_held: boolean;
  new_weight: number;
  total_value_before: number;
  total_value_after: number;
  top3_before: number;
  top3_after: number;
  herfindahl_before: number;
  herfindahl_after: number;
  correlation_to_portfolio: number | null;
  exposure_before: Record<string, Record<string, number>>;
  exposure_after: Record<string, Record<string, number>>;
  warnings: string[];
}

export const simulatePurchase = (
  ticker: string,
  amount: number,
  portfolioId: number | null = null,
) =>
  apiPost<Simulation>("/portfolio/simulate", {
    ticker,
    amount,
    portfolio_id: portfolioId,
  });

export interface PositionSizeGuide {
  ticker: string;
  current_price: number;
  volatility: number;
  risk_budget_pct: number;
  risk_budget_amount: number;
  portfolio_total_value: number;
  target_amount: number;
  target_weight_pct: number;
  current_amount: number;
  current_weight_pct: number;
  delta_amount: number;
  delta_quantity: number;
  capped: boolean;
  max_weight_cap: number;
  warnings: string[];
}

export const getPositionSizeGuide = (
  ticker: string,
  riskBudgetPct: number,
  portfolioId: number | null = null,
) =>
  apiGet<PositionSizeGuide>(
    `/portfolio/position-size/${ticker}?risk_budget_pct=${riskBudgetPct}` +
      (portfolioId !== null ? `&portfolio_id=${portfolioId}` : ""),
  );

// --- Portfolios (multi-portfolio switcher) ------------------------------------

export interface Portfolio {
  id: number;
  name: string;
  created_at: string;
}

export const getPortfolios = () => apiGet<Portfolio[]>("/portfolios");
export const createPortfolio = (name: string) =>
  apiPost<Portfolio>("/portfolios", { name });
export const renamePortfolio = (id: number, name: string) =>
  apiPatch<Portfolio>(`/portfolios/${id}`, { name });

// --- Data entry --------------------------------------------------------------

export interface Asset {
  id: number;
  ticker: string;
  name: string;
  asset_class: string;
  sector: string;
  country: string;
  currency: string;
}

export interface AssetCreate {
  ticker: string;
  name: string;
  asset_class: string;
  sector: string;
  country: string;
  currency: string;
}

export interface PositionFull {
  id: number;
  ticker: string;
  portfolio_id: number;
  quantity: number;
  avg_cost: number;
  opened_at: string;
  status: string;
}

export interface IngestionResult {
  source: string;
  promoted: number;
  quarantined: number;
  message: string;
}

export const getAssets = () => apiGet<Asset[]>("/assets");
export const createAsset = (body: AssetCreate) =>
  apiPost<Asset>("/assets", body);
export const deleteAsset = (id: number) => apiDelete(`/assets/${id}`);

export const getPositions = (portfolioId?: number | null) =>
  apiGet<PositionFull[]>(
    `/positions${portfolioId != null ? `?portfolio_id=${portfolioId}` : ""}`,
  );
export const createPosition = (body: {
  ticker: string;
  portfolio_id: number;
  quantity: number;
  avg_cost: number;
}) => apiPost<PositionFull>("/positions", body);
export const deletePosition = (id: number) => apiDelete(`/positions/${id}`);

export const runIngestion = (source: string) =>
  apiPost<IngestionResult>(`/ingestion/run?source=${source}`, {});

export interface Freshness {
  source: string;
  label: string;
  last_success_at: string | null;
  last_attempt_at: string | null;
}

export const getFreshness = () => apiGet<Freshness[]>("/ingestion/freshness");

export interface YoutubeChannel {
  id: number;
  channel_id: string;
  handle: string;
  display_name: string;
  active: boolean;
  added_at: string;
}

export const getChannels = () => apiGet<YoutubeChannel[]>("/youtube/channels");
export const createChannel = (url_or_handle: string) =>
  apiPost<YoutubeChannel>("/youtube/channels", { url_or_handle });
export const deleteChannel = (id: number) => apiDelete(`/youtube/channels/${id}`);

export interface TransactionCreate {
  ticker: string;
  type: "buy" | "sell";
  quantity: number;
  price: number;
  fee: number;
}

export const createTransaction = (body: TransactionCreate) =>
  apiPost<{ id: number; status: string }>("/transactions", body);

// --- News & sentiment --------------------------------------------------------

export type SentimentLabel = "positive" | "neutral" | "negative";

export interface NewsItem {
  id: number;
  ticker: string | null;
  title: string;
  summary: string;
  url: string;
  source: string;
  sentiment: number;
  sentiment_label: SentimentLabel;
  published_at: string;
}

export interface TickerSentiment {
  ticker: string;
  score: number;
  label: SentimentLabel;
  count: number;
}

export interface Transcript {
  id: number;
  source_channel: string;
  title: string;
  url: string;
  summary: string;
  sentiment: number;
  sentiment_label: SentimentLabel;
  published_at: string;
}

export interface SentimentPoint {
  date: string;
  score: number;
  count: number;
}

export const getNews = (ticker?: string) =>
  apiGet<NewsItem[]>(`/news${ticker ? `?ticker=${ticker}` : ""}`);
export const getNewsSentiment = () =>
  apiGet<TickerSentiment[]>("/news/sentiment");
export const getSentimentSeries = (ticker?: string) =>
  apiGet<SentimentPoint[]>(`/news/sentiment/series${ticker ? `?ticker=${ticker}` : ""}`);
export const getTranscripts = () => apiGet<Transcript[]>("/transcripts");

// --- Research & Macro --------------------------------------------------------

export interface IndicatorPoint {
  date: string;
  close: number;
  sma20: number | null;
  sma50: number | null;
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
}

export interface Indicators {
  ticker: string;
  points: IndicatorPoint[];
}

export interface MacroCard {
  key: string;
  label: string;
  value: number;
  unit: string;
  change_pct: number;
  group: string;
}

export const getIndicators = (ticker: string) =>
  apiGet<Indicators>(`/research/indicators?ticker=${ticker}`);

export interface AssetComparison {
  ticker: string;
  data_points: number;
  latest_price?: number;
  total_return?: number;
  return_1m?: number;
  volatility?: number;
  max_drawdown?: number;
  sharpe?: number;
  pe_ratio: number | null;
  forward_pe: number | null;
  pb_ratio: number | null;
  ev_to_ebitda: number | null;
  dividend_yield: number | null;
  roe: number | null;
}

export const compareAssets = (tickers: string[]) =>
  apiGet<AssetComparison[]>(`/research/compare?tickers=${tickers.join(",")}`);
export const getMacro = () => apiGet<MacroCard[]>("/macro");

export interface ScreenerRow {
  ticker: string;
  name: string;
  asset_class: string;
  sector: string;
  country: string;
  currency: string;
  latest_price: number | null;
  return_1m: number | null;
  rsi14: number | null;
  trend: "alcista" | "bajista" | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  pb_ratio: number | null;
  dividend_yield: number | null;
  revenue_growth: number | null;
  roe: number | null;
}

export const getScreener = () => apiGet<ScreenerRow[]>("/research/screener");

export interface SeedResult {
  created: number;
  already_tracked: number;
  message: string;
}

export const seedScreenerUniverse = () =>
  apiPost<SeedResult>("/screener/seed", {});

export interface Fundamentals {
  ticker: string;
  source: string;
  updated_at: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  pb_ratio: number | null;
  ev_to_ebitda: number | null;
  peg_ratio: number | null;
  dividend_yield: number | null;
  payout_ratio: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  profit_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  analyst_target_mean: number | null;
  analyst_recommendation: string | null;
  next_earnings_date: string | null;
}

export const getFundamentals = (ticker: string) =>
  apiGet<Fundamentals>(`/research/fundamentals/${ticker}`);

// --- Asset detail + chatbot --------------------------------------------------

export interface AssetPosition {
  quantity: number;
  avg_cost: number;
  market_value: number;
  pnl: number;
  pnl_pct: number;
}

export interface AssetSummary {
  ticker: string;
  name: string;
  asset_class: string;
  sector: string;
  country: string;
  currency: string;
  latest_price: number | null;
  total_return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  position: AssetPosition | null;
  news_count: number;
  avg_sentiment: number | null;
}

export const getAssetSummary = (
  ticker: string,
  portfolioId: number | null = null,
) =>
  apiGet<AssetSummary>(
    `/assets/${ticker}/summary${portfolioId !== null ? `?portfolio_id=${portfolioId}` : ""}`,
  );

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  configured: boolean;
  error: boolean;
}

export const postChat = (ticker: string, messages: ChatTurn[]) =>
  apiPost<ChatResponse>("/chat/fundamental", { ticker, messages });

// --- Thesis journal ------------------------------------------------------------

export type Conviction = "baja" | "media" | "alta";
export type ThesisStatus = "en_curso" | "objetivo_alcanzado" | "stop_tocado" | "sin_precio";

export interface Thesis {
  id: number;
  ticker: string;
  note: string;
  price_at_entry: number | null;
  target_price: number | null;
  stop_loss: number | null;
  conviction: Conviction;
  created_at: string;
  current_price: number | null;
  return_since_entry: number | null;
  status: ThesisStatus;
}

export interface ThesisCreate {
  ticker: string;
  note: string;
  target_price?: number | null;
  stop_loss?: number | null;
  conviction?: Conviction;
}

export const getTheses = (ticker?: string) =>
  apiGet<Thesis[]>(`/theses${ticker ? `?ticker=${ticker}` : ""}`);
export const createThesis = (body: ThesisCreate) =>
  apiPost<Thesis>("/theses", body);
export const deleteThesis = (id: number) => apiDelete(`/theses/${id}`);

// --- Alerts --------------------------------------------------------------------

export type AlertMetric = "price" | "sentiment" | "pe_ratio";
export type AlertCondition = "above" | "below";
export type AlertStatus = "disparada" | "en_seguimiento" | "sin_dato" | "inactiva";

export interface Alert {
  id: number;
  ticker: string;
  metric: AlertMetric;
  condition: AlertCondition;
  threshold: number;
  active: boolean;
  created_at: string;
  current_value: number | null;
  triggered: boolean;
  status: AlertStatus;
}

export interface AlertCreate {
  ticker: string;
  metric: AlertMetric;
  condition: AlertCondition;
  threshold: number;
}

export const getAlerts = (params?: { ticker?: string; onlyTriggered?: boolean }) => {
  const qs = new URLSearchParams();
  if (params?.ticker) qs.set("ticker", params.ticker);
  if (params?.onlyTriggered) qs.set("only_triggered", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet<Alert[]>(`/alerts${suffix}`);
};
export const createAlert = (body: AlertCreate) => apiPost<Alert>("/alerts", body);
export const deleteAlert = (id: number) => apiDelete(`/alerts/${id}`);
