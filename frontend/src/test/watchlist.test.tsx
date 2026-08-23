import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

// A ticker with no Asset row yet: the detail page's summary endpoint 404s
// until the user opts in, at which point it should offer to add it to the
// watchlist (no position required) and, once added, show the normal tabs.
describe("Asset detail — watchlist quick-add", () => {
  it("offers to add an unknown ticker, then loads it after adding", async () => {
    let summaryCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/assets/ZZZZ/summary")) {
          summaryCalls += 1;
          if (summaryCalls === 1) {
            return Promise.resolve({
              ok: false,
              status: 404,
              json: () =>
                Promise.resolve({ detail: "No existe el activo ZZZZ" }),
            });
          }
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ticker: "ZZZZ",
                name: "ZZZZ",
                asset_class: "equity",
                sector: "Unknown",
                country: "Unknown",
                currency: "USD",
                latest_price: null,
                total_return: null,
                volatility: null,
                max_drawdown: null,
                position: null,
                news_count: 0,
                avg_sentiment: null,
              }),
          });
        }
        if (url.includes("/assets") && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                id: 1,
                ticker: "ZZZZ",
                name: "ZZZZ",
                asset_class: "equity",
                sector: "Unknown",
                country: "Unknown",
                currency: "USD",
              }),
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }),
    );

    render(
      <MemoryRouter initialEntries={["/activo/ZZZZ"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/ZZZZ no está en seguimiento/),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Agregar ZZZZ a seguimiento/ }),
    );

    expect(await screen.findByText("Datos del activo")).toBeInTheDocument();
    expect(
      screen.queryByText(/ZZZZ no está en seguimiento/),
    ).not.toBeInTheDocument();
  });
});
