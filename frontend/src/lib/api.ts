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
