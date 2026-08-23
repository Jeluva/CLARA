import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

const ROWS = [
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    asset_class: "cedear",
    sector: "Technology",
    country: "USA",
    currency: "USD",
    latest_price: 190.5,
    return_1m: 5.2,
    rsi14: 55.1,
    trend: "alcista",
    pe_ratio: 28.4,
    forward_pe: 25.1,
    pb_ratio: 12.3,
    dividend_yield: 0.5,
    revenue_growth: 0.08,
    roe: 0.45,
  },
  {
    ticker: "GGAL",
    name: "Grupo Financiero Galicia",
    asset_class: "equity",
    sector: "Financials",
    country: "Argentina",
    currency: "ARS",
    latest_price: 3200,
    return_1m: -2.1,
    rsi14: 40.2,
    trend: "bajista",
    pe_ratio: null,
    forward_pe: null,
    pb_ratio: null,
    dividend_yield: null,
    revenue_growth: null,
    roe: null,
  },
];

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/research/screener")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(ROWS) });
      }
      if (url.includes("/screener/seed") && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              created: 26,
              already_tracked: 2,
              message: "26 activos nuevos agregados al universo del screener.",
            }),
        });
      }
      if (url.includes("/ingestion/run")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ source: "prices", promoted: 0, quarantined: 0, message: "ok" }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
    }),
  );
}

describe("Screener page", () => {
  it("lists every tracked asset and filters by search", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/screener"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("GGAL")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Ticker o nombre"), {
      target: { value: "AAPL" },
    });

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.queryByText("GGAL")).not.toBeInTheDocument();
  });

  it("seeds the curated universe and shows the result message", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/screener"]}>
        <App />
      </MemoryRouter>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Cargar universo ampliado/ }),
    );

    expect(
      await screen.findByText(/26 activos nuevos agregados/),
    ).toBeInTheDocument();
  });
});
