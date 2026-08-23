import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

const METRICS_SHAPE = {
  volatility: 0,
  sharpe: 0,
  max_drawdown: 0,
  beta: 0,
  cumulative_return: 0,
  top3_concentration: 0,
  herfindahl: 0,
};

function mockFetch({
  alerts = [],
  theses = [],
  freshness = [],
}: {
  alerts?: unknown[];
  theses?: unknown[];
  freshness?: unknown[];
} = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.includes("/alerts")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(alerts) });
      }
      if (url.includes("/theses")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(theses) });
      }
      if (url.includes("/ingestion/freshness")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(freshness) });
      }
      if (url.includes("/portfolio/metrics")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(METRICS_SHAPE) });
      }
      if (url.includes("/portfolio/exposure")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sector: {}, country: {}, currency: {} }),
        });
      }
      if (url.includes("/portfolios") || url.includes("/portfolio/history")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      }
      if (url.includes("/portfolio")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              total_value: 0,
              total_cost: 0,
              total_pnl: 0,
              total_pnl_pct: 0,
              daily_pnl: 0,
              daily_pnl_pct: 0,
              positions: [],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({ status: "ok", app: "CLARA", version: "0.1.0", environment: "test" }),
      });
    }),
  );
}

describe("ExecutiveSummary", () => {
  it("shows triggered alerts and theses that need review, hides the rest", async () => {
    mockFetch({
      alerts: [
        { id: 1, ticker: "AAPL", metric: "price", condition: "above", threshold: 1 },
      ],
      theses: [
        {
          id: 1,
          ticker: "AAPL",
          note: "stop",
          price_at_entry: 100,
          target_price: null,
          stop_loss: 400,
          conviction: "media",
          created_at: "2026-01-01",
          current_price: 100,
          return_since_entry: 0,
          status: "stop_tocado",
        },
        {
          id: 2,
          ticker: "MSFT",
          note: "en curso",
          price_at_entry: 100,
          target_price: 500,
          stop_loss: 50,
          conviction: "alta",
          created_at: "2026-01-01",
          current_price: 200,
          return_since_entry: 100,
          status: "en_curso",
        },
      ],
      freshness: [
        {
          source: "fundamentals",
          label: "Fundamentals",
          last_success_at: null,
          last_attempt_at: null,
        },
        {
          source: "prices",
          label: "Precios",
          last_success_at: "2026-08-23T00:00:00",
          last_attempt_at: "2026-08-23T00:00:00",
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Resumen ejecutivo")).toBeInTheDocument();
    expect(await screen.findByText(/price ≥ 1/)).toBeInTheDocument();
    expect(screen.getByText("Stop tocado")).toBeInTheDocument();
    expect(screen.getByText("Fundamentals")).toBeInTheDocument();

    // en_curso thesis and the fresh "prices" source don't need attention.
    expect(screen.queryByText("MSFT")).not.toBeInTheDocument();
    expect(screen.queryByText("Precios")).not.toBeInTheDocument();
  });

  it("shows an all-clear message when nothing needs attention", async () => {
    mockFetch();

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/Todo en orden/),
    ).toBeInTheDocument();
  });
});
