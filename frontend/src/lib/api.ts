/**
 * Thin API client. Uses same-origin `/api/...` paths; Vite proxies them to
 * FastAPI in dev. Centralises error handling so pages don't repeat fetch logic.
 */

const BASE = "/api";

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

export const getNews = (ticker?: string) =>
  apiGet<NewsItem[]>(`/news${ticker ? `?ticker=${ticker}` : ""}`);
export const getNewsSentiment = () =>
  apiGet<TickerSentiment[]>("/news/sentiment");
export const getTranscripts = () => apiGet<Transcript[]>("/transcripts");
