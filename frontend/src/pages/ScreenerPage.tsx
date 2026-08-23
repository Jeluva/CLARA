import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Field, Input, Select, Button } from "@/components/Field";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import {
  getScreener,
  seedScreenerUniverse,
  runIngestion,
  ApiError,
  type ScreenerRow,
} from "@/lib/api";
import { pnlColor } from "@/lib/format";

type SortKey = keyof Pick<
  ScreenerRow,
  | "ticker"
  | "latest_price"
  | "return_1m"
  | "rsi14"
  | "pe_ratio"
  | "dividend_yield"
  | "revenue_growth"
  | "roe"
>;

const COLUMNS: { key: SortKey; label: string; suffix?: string }[] = [
  { key: "ticker", label: "Ticker" },
  { key: "latest_price", label: "Precio" },
  { key: "return_1m", label: "Retorno 1M", suffix: "%" },
  { key: "rsi14", label: "RSI(14)" },
  { key: "pe_ratio", label: "P/E" },
  { key: "dividend_yield", label: "Div. yield", suffix: "%" },
  { key: "revenue_growth", label: "Crec. ingresos", suffix: "%pt" },
  { key: "roe", label: "ROE", suffix: "%pt" },
];

/** Tab — Screener: filter every tracked asset by fundamentals + technicals
 * to generate candidate ideas, instead of only analyzing what's already
 * loaded (see docs/devlog/BACKLOG.md, v2 item 3). */
export function ScreenerPage() {
  const screener = useApi(getScreener);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState("Todos");
  const [assetClass, setAssetClass] = useState("Todos");
  const [momentumOnly, setMomentumOnly] = useState(false);
  const [peMax, setPeMax] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [sortDir, setSortDir] = useState<1 | -1>(1);

  const rows = screener.data ?? [];
  const sectors = useMemo(
    () => ["Todos", ...new Set(rows.map((r) => r.sector))].sort(),
    [rows],
  );
  const classes = useMemo(
    () => ["Todos", ...new Set(rows.map((r) => r.asset_class))].sort(),
    [rows],
  );

  const filtered = rows
    .filter((r) => sector === "Todos" || r.sector === sector)
    .filter((r) => assetClass === "Todos" || r.asset_class === assetClass)
    .filter((r) => !momentumOnly || (r.return_1m ?? -Infinity) > 0)
    .filter((r) => {
      const max = Number(peMax);
      return !peMax || r.pe_ratio == null || r.pe_ratio <= max;
    })
    .filter((r) => {
      const q = search.trim().toUpperCase();
      return !q || r.ticker.includes(q) || r.name.toUpperCase().includes(q);
    })
    .sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "string" || typeof bv === "string") {
        return sortDir * String(av).localeCompare(String(bv));
      }
      return sortDir * ((av as number) - (bv as number));
    });

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(1);
    }
  }

  return (
    <div>
      <PageHeader
        title="Screener"
        question="¿Qué candidatos hay más allá de lo que ya tengo cargado?"
      />

      <SeedUniverseCard onSeeded={screener.reload} />

      <Card className="mb-5 mt-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Field label="Buscar">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Ticker o nombre"
            />
          </Field>
          <Field label="Sector">
            <Select value={sector} onChange={(e) => setSector(e.target.value)}>
              {sectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </Select>
          </Field>
          <Field label="Clase">
            <Select value={assetClass} onChange={(e) => setAssetClass(e.target.value)}>
              {classes.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </Select>
          </Field>
          <Field label="P/E máximo">
            <Input
              type="number"
              step="any"
              min="0"
              value={peMax}
              onChange={(e) => setPeMax(e.target.value)}
              placeholder="Sin límite"
            />
          </Field>
          <label className="flex items-end gap-2 pb-2 text-sm text-secondary">
            <input
              type="checkbox"
              checked={momentumOnly}
              onChange={(e) => setMomentumOnly(e.target.checked)}
            />
            Solo momentum positivo
          </label>
        </div>
      </Card>

      <Card
        title="Universo"
        subtitle={`${filtered.length} de ${rows.length} activos — clic en una columna para ordenar`}
      >
        {screener.loading && <Spinner />}
        {screener.error && <ErrorState message={screener.error} />}
        {!screener.loading && !screener.error && rows.length === 0 && (
          <p className="py-6 text-sm text-secondary">
            Sin activos todavía. Cargá el universo ampliado arriba o agregá
            tickers desde Ingreso de datos.
          </p>
        )}
        {filtered.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-separator text-xs uppercase tracking-wide text-secondary">
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="px-2 py-2 text-left font-medium">
                      <button
                        onClick={() => toggleSort(c.key)}
                        className="flex items-center gap-1 hover:text-primary"
                      >
                        {c.label}
                        {sortKey === c.key && (sortDir === 1 ? "↑" : "↓")}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.ticker} className="border-b border-separator/50">
                    <td className="px-2 py-2.5 font-medium text-primary">
                      <Link to={`/activo/${r.ticker}`} className="hover:underline">
                        {r.ticker}
                      </Link>
                    </td>
                    <td className="tabnum px-2 py-2.5 text-secondary">
                      {r.latest_price != null ? r.latest_price.toFixed(2) : "—"}
                    </td>
                    <td className={`tabnum px-2 py-2.5 ${r.return_1m != null ? pnlColor(r.return_1m) : "text-secondary"}`}>
                      {r.return_1m != null ? `${r.return_1m > 0 ? "+" : ""}${r.return_1m.toFixed(2)}%` : "—"}
                    </td>
                    <td className="tabnum px-2 py-2.5 text-secondary">
                      {r.rsi14 != null ? r.rsi14.toFixed(1) : "—"}
                    </td>
                    <td className="tabnum px-2 py-2.5 text-secondary">
                      {r.pe_ratio != null ? `${r.pe_ratio.toFixed(1)}x` : "—"}
                    </td>
                    <td className="tabnum px-2 py-2.5 text-secondary">
                      {r.dividend_yield != null ? `${r.dividend_yield.toFixed(2)}%` : "—"}
                    </td>
                    <td className="tabnum px-2 py-2.5 text-secondary">
                      {r.revenue_growth != null ? `${(r.revenue_growth * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="tabnum px-2 py-2.5 text-secondary">
                      {r.roe != null ? `${(r.roe * 100).toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function SeedUniverseCard({ onSeeded }: { onSeeded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setMessage(null);
    try {
      const seed = await seedScreenerUniverse();
      await runIngestion("prices");
      await runIngestion("fundamentals");
      setMessage(seed.message);
      onSeeded();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "No se pudo cargar el universo");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="Universo ampliado"
      subtitle="~30 tickers líderes (CEDEARs de EE. UU., Merval, soberanos AR) para generar ideas más allá de lo que ya cargaste"
    >
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={load} disabled={busy}>
          {busy ? "Cargando universo…" : "Cargar universo ampliado"}
        </Button>
        {message && <span className="text-sm text-secondary">{message}</span>}
      </div>
    </Card>
  );
}
