import { useState, useEffect } from "react";
import { PageHeader } from "@/components/PageHeader";
import { PortfolioSwitcher } from "@/components/PortfolioSwitcher";
import { ExecutiveSummary } from "@/components/ExecutiveSummary";
import { Card } from "@/components/Card";
import { Metric } from "@/components/Metric";
import { Donut } from "@/components/Donut";
import { LineChartCard } from "@/components/LineChartCard";
import { PositionsTable } from "@/components/PositionsTable";
import { RiskPanel } from "@/components/RiskPanel";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import { usePortfolios } from "@/hooks/usePortfolios";
import {
  getPortfolio,
  getMetrics,
  getExposure,
  getHistory,
  getRealizedHistory,
  type RealizedPoint,
} from "@/lib/api";
import {
  formatCurrency,
  formatSignedCurrency,
  formatSignedPercent,
  pnlColor,
} from "@/lib/format";

type ChartMode = "basket" | "realized";

/** Tab 1 — Portfolio (main). The showcase dashboard. */
export function PortfolioPage() {
  const { activeId } = usePortfolios();
  const overview = useApi(() => getPortfolio(activeId), [activeId]);
  const metrics = useApi(() => getMetrics(activeId), [activeId]);
  const exposure = useApi(() => getExposure(activeId), [activeId]);
  const history = useApi(() => getHistory(activeId), [activeId]);
  const [chartMode, setChartMode] = useState<ChartMode>("basket");
  const [realized, setRealized] = useState<RealizedPoint[] | null>(null);

  useEffect(() => {
    setRealized(null);
  }, [activeId]);

  useEffect(() => {
    if (chartMode === "realized" && !realized) {
      getRealizedHistory(activeId).then(setRealized);
    }
  }, [chartMode, realized, activeId]);

  return (
    <div>
      <PageHeader
        title="Portfolio"
        question="¿Cómo está parada mi cartera hoy?"
        adornment={<PortfolioSwitcher />}
      />

      <ExecutiveSummary />

      {/* KPI row */}
      <Card className="mb-5">
        {overview.loading && <Spinner />}
        {overview.error && <ErrorState message={overview.error} />}
        {overview.data && (
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            <Metric
              label="Valor total"
              value={formatCurrency(overview.data.total_value)}
            />
            <Metric
              label="P&L total"
              value={
                <span className={pnlColor(overview.data.total_pnl)}>
                  {formatSignedCurrency(overview.data.total_pnl)}
                </span>
              }
              sub={
                <span className={pnlColor(overview.data.total_pnl)}>
                  {formatSignedPercent(overview.data.total_pnl_pct)}
                </span>
              }
            />
            <Metric
              label="P&L diario"
              value={
                <span className={pnlColor(overview.data.daily_pnl)}>
                  {formatSignedCurrency(overview.data.daily_pnl)}
                </span>
              }
              sub={
                <span className={pnlColor(overview.data.daily_pnl)}>
                  {formatSignedPercent(overview.data.daily_pnl_pct)}
                </span>
              }
            />
            <Metric
              label="Costo invertido"
              value={formatCurrency(overview.data.total_cost)}
            />
          </div>
        )}
      </Card>

      {/* Evolution chart + risk panel */}
      <div className="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card
          title={chartMode === "basket" ? "Evolución vs. benchmark (SPY)" : "P&L realizado"}
          subtitle={chartMode === "basket" ? "Basket hipotético (tenencias actuales)" : "Respeta fecha de entrada de cada posición"}
          className="lg:col-span-2"
          action={
            <div className="flex gap-1">
              {(["basket", "realized"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setChartMode(m)}
                  className={`rounded-control border px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
                    chartMode === m
                      ? "border-accent bg-accent/10 text-primary"
                      : "border-separator text-secondary hover:bg-separator/40"
                  }`}
                >
                  {m === "basket" ? "Basket" : "Realizado"}
                </button>
              ))}
            </div>
          }
        >
          {chartMode === "basket" && (
            <>
              {history.loading && <Spinner />}
              {history.error && <ErrorState message={history.error} />}
              {history.data &&
                (history.data.length > 0 ? (
                  <LineChartCard data={history.data} />
                ) : (
                  <p className="py-10 text-sm text-secondary">Sin historial</p>
                ))}
            </>
          )}
          {chartMode === "realized" && (
            <>
              {!realized && <Spinner />}
              {realized && realized.length > 0 ? (
                <LineChartCard
                  data={realized.map((p) => ({
                    date: p.date,
                    portfolio: p.realized_pnl,
                    benchmark: null,
                  }))}
                />
              ) : realized ? (
                <p className="py-10 text-sm text-secondary">Sin datos de P&L realizado</p>
              ) : null}
            </>
          )}
        </Card>

        <Card title="Riesgo" subtitle="Métricas de la cartera">
          {metrics.loading && <Spinner />}
          {metrics.error && <ErrorState message={metrics.error} />}
          {metrics.data && <RiskPanel metrics={metrics.data} />}
        </Card>
      </div>

      {/* Exposure donuts */}
      <Card title="Exposición" subtitle="Distribución del valor de mercado" className="mb-5">
        {exposure.loading && <Spinner />}
        {exposure.error && <ErrorState message={exposure.error} />}
        {exposure.data && (
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
            <Donut title="Por sector" data={exposure.data.sector} />
            <Donut title="Por país" data={exposure.data.country} />
            <Donut title="Por moneda" data={exposure.data.currency} />
          </div>
        )}
      </Card>

      {/* Positions table */}
      <Card title="Posiciones" subtitle="Tenencias abiertas">
        {overview.loading && <Spinner />}
        {overview.error && <ErrorState message={overview.error} />}
        {overview.data && <PositionsTable positions={overview.data.positions} />}
      </Card>
    </div>
  );
}
