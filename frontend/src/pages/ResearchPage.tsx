import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Heatmap } from "@/components/Heatmap";
import { TechnicalChart } from "@/components/TechnicalChart";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import { getCorrelation, getIndicators, type Indicators } from "@/lib/api";

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
    </div>
  );
}
