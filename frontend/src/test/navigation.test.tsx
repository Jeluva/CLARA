import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/assets") || url.includes("/research/screener")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "ok",
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
            tickers: [],
            matrix: [],
          }),
      });
    }),
  );
});

describe("routing", () => {
  it("renders News page at /noticias", () => {
    render(
      <MemoryRouter initialEntries={["/noticias"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Noticias & Sentimiento", level: 1 }),
    ).toBeInTheDocument();
  });

  it("renders Research page at /research", () => {
    render(
      <MemoryRouter initialEntries={["/research"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Research", level: 1 }),
    ).toBeInTheDocument();
  });

  it("renders Macro page at /macro", () => {
    render(
      <MemoryRouter initialEntries={["/macro"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Macro", level: 1 }),
    ).toBeInTheDocument();
  });

  it("renders Screener page at /screener", () => {
    render(
      <MemoryRouter initialEntries={["/screener"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Screener", level: 1 }),
    ).toBeInTheDocument();
  });

  it("renders Data Entry page at /datos", () => {
    render(
      <MemoryRouter initialEntries={["/datos"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Ingreso de datos", level: 1 }),
    ).toBeInTheDocument();
  });
});
