import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

// The Portfolio page calls the API on mount; stub fetch so the shell renders
// deterministically in jsdom.
beforeEach(() => {
  // Array-shaped endpoints (portfolios, history, alerts, theses, freshness)
  // must return an array — response_model=list[...] on the backend
  // guarantees that in production, and components like ExecutiveSummary
  // rely on it without their own defensive check. Everything else
  // (health, portfolio overview, metrics, exposure) gets the superset
  // object shape below.
  const LIST_ENDPOINTS = [
    "/portfolios",
    "/history",
    "/alerts",
    "/theses",
    "/ingestion/freshness",
  ];
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (LIST_ENDPOINTS.some((p) => url.includes(p))) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "ok",
            app: "CLARA",
            version: "0.1.0",
            environment: "test",
            total_value: 0,
            total_cost: 0,
            total_pnl: 0,
            total_pnl_pct: 0,
            daily_pnl: 0,
            daily_pnl_pct: 0,
            positions: [],
            sector: {},
            country: {},
            currency: {},
          }),
      });
    }),
  );
});

describe("app shell", () => {
  it("renders the sidebar with all six tabs", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    for (const label of [
      "Portfolio",
      "Noticias",
      "Research",
      "Macro",
      "Screener",
      "Ingreso de datos",
    ]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("renders the default Portfolio route heading", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Portfolio", level: 1 }),
    ).toBeInTheDocument();
  });
});
