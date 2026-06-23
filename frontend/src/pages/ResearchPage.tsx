import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Heatmap } from "@/components/Heatmap";
import { TechnicalChart } from "@/components/TechnicalChart";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import {
  getCorrelation,
  getIndicators,
  compareAssets,
  type Indicators,
  type AssetComparison,
} from "@/lib/api";
import { pnlColor } from "@/lib/format";

/** Tab 3 — Research: correlation heatmap + technical indicators. */
export function ResearchPage() {
  const correlation = useApi(getCorrelation);
  const [ticker, setTicker] = useState<string | null>(null);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker && correlation.data?.tickers.length) {
      setTicker(correlation.data.tickers[0]);
    }
  }, [correlation.data, ticker]);

  useEffect(() => {
    if (!ticker) return;
    let active = true;
    setLoading(true);
    getIndicators(ticker)
      .then((d) => active && setIndicators(d))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [ticker]);

  return (
    <div>
      <PageHeader
        title="Research"
        question="¿Qué me dicen los datos técnicos y las correlaciones?"
      />

      <Card
        title="Matriz de correlación"
        subtitle="Retornos diarios — detecta falsa diversificación"
        className="mb-5"
      >
        {correlation.loading && <Spinner />}
        {correlation.error && <ErrorState message={correlation.error} />}
        {correlation.data && <Heatmap data={correlation.data} />}
      </Card>

      <Card
        title="Indicadores técnicos"
        subtitle="Precio, medias móviles (20/50), RSI(14) y MACD"
        action={
          <div className="flex flex-wrap gap-1.5">
            {correlation.data?.tickers.map((t) => (
              <button
                key={t}
                onClick={() => setTicker(t)}
                className={`rounded-control border px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
                  ticker === t
                    ? "border-accent bg-accent/10 text-primary"
                    : "border-separator text-secondary hover:bg-separator/40"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        }
      >
        {loading && <Spinner />}
        {indicators && <TechnicalChart points={indicators.points} />}
      </Card>

      <AssetComparator tickers={correlation.data?.tickers ?? []} />
    </div>
  );
}

function AssetComparator({ tickers }: { tickers: string[] }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [data, setData] = useState<AssetComparison[] | null>(null);
  const [loading, setLoading] = useState(false);

  function toggle(t: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  useEffect(() => {
    if (selected.size < 2) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    compareAssets([...selected])
      .then((d) => active && setData(d))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [selected]);

  const METRICS: { key: keyof AssetComparison; label: string; suffix: string; signed?: boolean }[] = [
    { key: "latest_price", label: "Precio", suffix: "" },
    { key: "total_return", label: "Retorno total", suffix: "%", signed: true },
    { key: "return_1m", label: "Retorno 1M", suffix: "%", signed: true },
    { key: "volatility", label: "Volatilidad", suffix: "%" },
    { key: "max_drawdown", label: "Max Drawdown", suffix: "%" },
    { key: "sharpe", label: "Sharpe", suffix: "" },
  ];

  return (
    <Card
      title="Comparador de activos"
      subtitle="Seleccioná 2 o más activos para comparar métricas"
      className="mt-5"
    >
      <div className="mb-4 flex flex-wrap gap-1.5">
        {tickers.map((t) => (
          <button
            key={t}
            onClick={() => toggle(t)}
            className={`rounded-control border px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
              selected.has(t)
                ? "border-accent bg-accent/10 text-primary"
                : "border-separator text-secondary hover:bg-separator/40"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {selected.size < 2 && (
        <p className="py-4 text-sm text-secondary">
          Seleccioná al menos 2 activos para comparar.
        </p>
      )}

      {loading && <Spinner />}

      {data && data.length >= 2 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-separator text-xs uppercase tracking-wide text-secondary">
                <th className="px-3 py-2 text-left font-medium">Métrica</th>
                {data.map((d) => (
                  <th key={d.ticker} className="px-3 py-2 text-right font-medium">
                    {d.ticker}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {METRICS.map((m) => (
                <tr key={m.key} className="border-b border-separator/50">
                  <td className="px-3 py-2.5 font-medium text-primary">{m.label}</td>
                  {data.map((d) => {
                    const val = d[m.key] as number | undefined;
                    if (val == null) return <td key={d.ticker} className="px-3 py-2.5 text-right text-secondary">—</td>;
                    const color = m.signed ? pnlColor(val) : "text-primary";
                    const sign = m.signed && val > 0 ? "+" : "";
                    return (
                      <td key={d.ticker} className={`tabnum px-3 py-2.5 text-right ${color}`}>
                        {sign}{val.toFixed(2)}{m.suffix}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
