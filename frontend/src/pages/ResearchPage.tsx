import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Heatmap } from "@/components/Heatmap";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import { colors } from "@/styles/theme";
import { getCorrelation, getIndicators, type Indicators } from "@/lib/api";

/** Tab 3 — Research: correlation heatmap + technical indicators. */
export function ResearchPage() {
  const correlation = useApi(getCorrelation);
  const [ticker, setTicker] = useState<string | null>(null);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [loading, setLoading] = useState(false);

  // Default the indicator chart to the first ticker once correlation loads.
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
        subtitle="Precio, medias móviles (20/50) y RSI(14)"
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
        {indicators && indicators.points.length > 0 && (
          <>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={indicators.points}
                  margin={{ top: 8, right: 8, bottom: 0, left: 8 }}
                >
                  <CartesianGrid
                    stroke={colors.separator}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: colors.secondary, fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: colors.separator }}
                    interval={Math.floor(indicators.points.length / 6)}
                    tickFormatter={(d: string) => d.slice(5)}
                  />
                  <YAxis
                    tick={{ fill: colors.secondary, fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={52}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      background: colors.surface,
                      border: `1px solid ${colors.separator}`,
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Line type="monotone" dataKey="close" stroke={colors.primary} strokeWidth={1.5} dot={false} isAnimationActive={false} name="Precio" />
                  <Line type="monotone" dataKey="sma20" stroke={colors.accent} strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 20" />
                  <Line type="monotone" dataKey="sma50" stroke={colors.warn} strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 50" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 h-32 w-full">
              <span className="text-xs font-medium uppercase tracking-wide text-secondary">
                RSI (14)
              </span>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={indicators.points}
                  margin={{ top: 8, right: 8, bottom: 0, left: 8 }}
                >
                  <CartesianGrid stroke={colors.separator} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" hide />
                  <YAxis
                    domain={[0, 100]}
                    ticks={[30, 50, 70]}
                    tick={{ fill: colors.secondary, fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={52}
                  />
                  <ReferenceLine y={70} stroke={colors.loss} strokeDasharray="3 3" />
                  <ReferenceLine y={30} stroke={colors.gain} strokeDasharray="3 3" />
                  <Tooltip
                    contentStyle={{
                      background: colors.surface,
                      border: `1px solid ${colors.separator}`,
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Line type="monotone" dataKey="rsi" stroke={colors.accent} strokeWidth={1.5} dot={false} isAnimationActive={false} name="RSI" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
