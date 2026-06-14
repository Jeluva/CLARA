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

export async function apiGet<T>(path: string): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`);
  } catch (cause) {
    throw new ApiError(`Network error reaching ${path}`, 0);
  }
  if (!resp.ok) {
    throw new ApiError(`Request to ${path} failed`, resp.status);
  }
  return (await resp.json()) as T;
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
