import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

// Fundamentals is 404 until the user runs ingestion — that's what every
// user sees on first load, so it's the branch worth covering here.
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.includes("/research/correlation")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ tickers: ["AAPL"], matrix: [[1]] }),
        });
      }
      if (url.endsWith("/assets")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve([
              { id: 1, ticker: "AAPL", name: "Apple", asset_class: "equity", sector: "Tech", country: "USA", currency: "USD" },
            ]),
        });
      }
      if (url.includes("/research/indicators")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ticker: "AAPL", points: [] }),
        });
      }
      if (url.includes("/research/fundamentals/")) {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () =>
            Promise.resolve({ detail: "Sin fundamentals para AAPL." }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }),
  );
});

describe("Research page — fundamentals panel", () => {
  it("prompts to run ingestion when no fundamentals were ingested yet", async () => {
    render(
      <MemoryRouter initialEntries={["/research"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText(/Sin datos de fundamentals para AAPL/),
    ).toBeInTheDocument();
  });
});
