import type { RiskMetrics } from "@/lib/api";
import { formatNumber, formatPercent, pnlColor } from "@/lib/format";

interface RiskRow {
  label: string;
  value: string;
  hint: string;
  className?: string;
}

/** Grid of risk metrics with a one-line plain-language hint each. */
export function RiskPanel({ metrics }: { metrics: RiskMetrics }) {
  const rows: RiskRow[] = [
    {
      label: "Volatilidad (anual.)",
      value: formatPercent(metrics.volatility),
      hint: "Desvío anualizado de los retornos diarios",
    },
    {
      label: "Max drawdown",
      value: formatPercent(metrics.max_drawdown),
      hint: "Mayor caída pico-a-valle",
      className: "text-loss",
    },
    {
      label: "Sharpe",
      value: formatNumber(metrics.sharpe),
      hint: "Retorno ajustado por riesgo (rf=0)",
      className: pnlColor(metrics.sharpe),
    },
    {
      label: "Beta vs. SPY",
      value: formatNumber(metrics.beta),
      hint: "Sensibilidad al benchmark",
    },
    {
      label: "Concentración top-3",
      value: formatPercent(metrics.top3_concentration),
      hint: "Peso de las 3 mayores posiciones",
    },
    {
      label: "Herfindahl",
      value: formatNumber(metrics.herfindahl, 3),
      hint: "Índice de concentración (1 = todo en uno)",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-5">
      {rows.map((r) => (
        <div key={r.label} className="flex flex-col gap-0.5">
          <span className="text-xs font-medium uppercase tracking-wide text-secondary">
            {r.label}
          </span>
          <span
            className={`tabnum text-xl font-semibold ${r.className ?? "text-primary"}`}
          >
            {r.value}
          </span>
          <span className="text-xs text-secondary">{r.hint}</span>
        </div>
      ))}
    </div>
  );
}
