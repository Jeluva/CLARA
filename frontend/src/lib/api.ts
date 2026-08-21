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

export const getPortfolio = () => apiGet<PortfolioOverview>("/portfolio");
export const getMetrics = () => apiGet<RiskMetrics>("/portfolio/metrics");
export const getExposure = () => apiGet<Exposure>("/portfolio/exposure");
export const getHistory = () => apiGet<HistoryPoint[]>("/portfolio/history");

export interface RealizedPoint {
  date: string;
  realized_pnl: number;
}

export const getRealizedHistory = () =>
  apiGet<RealizedPoint[]>("/portfolio/realized-history");
export const getCorrelation = () =>
  apiGet<Correlation>("/research/correlation");

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

export const getPositions = () => apiGet<PositionFull[]>("/positions");
export const createPosition = (body: {
  ticker: string;
  quantity: number;
  avg_cost: number;
}) => apiPost<PositionFull>("/positions", body);
export const deletePosition = (id: number) => apiDelete(`/positions/${id}`);

export const runIngestion = (source: string) =>
  apiPost<IngestionResult>(`/ingestion/run?source=${source}`, {});

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
}

export const compareAssets = (tickers: string[]) =>
  apiGet<AssetComparison[]>(`/research/compare?tickers=${tickers.join(",")}`);
export const getMacro = () => apiGet<MacroCard[]>("/macro");

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

export const getAssetSummary = (ticker: string) =>
  apiGet<AssetSummary>(`/assets/${ticker}/summary`);

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
