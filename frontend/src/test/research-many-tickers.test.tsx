import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

// Regression guard: with a large universe (screener seeds ~28 assets), the
// ticker pickers must not degrade into an unbounded row of chips — the
// indicators picker becomes a <select>, and the comparator gets a filter
// box instead of listing every ticker as a chip.
const MANY_TICKERS = Array.from({ length: 28 }, (_, i) => `TICK${i}`);

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/assets")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve(
              MANY_TICKERS.map((t, i) => ({
                id: i,
                ticker: t,
                name: t,
                asset_class: "equity",
                sector: "Technology",
                country: "USA",
                currency: "USD",
              })),
            ),
        });
      }
      if (url.includes("/research/correlation")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ tickers: [], matrix: [] }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }),
  );
});

describe("Research page — large ticker universe", () => {
  it("uses a dropdown for the indicators picker, not one chip per ticker", async () => {
    render(
      <MemoryRouter initialEntries={["/research"]}>
        <App />
      </MemoryRouter>,
    );

    const select = await screen.findByRole("combobox");
    expect(select.querySelectorAll("option")).toHaveLength(28);
    // The comparator below still renders one chip per ticker (scrollable +
    // filterable), but the indicators picker itself must not — so each
    // ticker should appear as a chip button at most once on the page.
    expect(await screen.findAllByRole("button", { name: "TICK0" })).toHaveLength(1);
  });

  it("shows a filter box for the comparator instead of 28 unfiltered chips", async () => {
    render(
      <MemoryRouter initialEntries={["/research"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByPlaceholderText("Filtrar ticker…")).toBeInTheDocument();
  });
});
