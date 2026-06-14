import type { Position } from "@/lib/api";
import {
  formatCurrency,
  formatNumber,
  formatSignedCurrency,
  formatSignedPercent,
  formatPercent,
  pnlColor,
} from "@/lib/format";

/** Dense, right-aligned-numbers position table sorted by market value. */
export function PositionsTable({ positions }: { positions: Position[] }) {
  const rows = [...positions].sort((a, b) => b.market_value - a.market_value);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-separator text-xs uppercase tracking-wide text-secondary">
            <th className="px-2 py-2 text-left font-medium">Activo</th>
            <th className="px-2 py-2 text-right font-medium">Cant.</th>
            <th className="px-2 py-2 text-right font-medium">Costo prom.</th>
            <th className="px-2 py-2 text-right font-medium">Precio</th>
            <th className="px-2 py-2 text-right font-medium">Valor</th>
            <th className="px-2 py-2 text-right font-medium">P&L</th>
            <th className="px-2 py-2 text-right font-medium">P&L %</th>
            <th className="px-2 py-2 text-right font-medium">Peso</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr
              key={p.ticker}
              className="border-b border-separator/50 transition-colors hover:bg-separator/30"
            >
              <td className="px-2 py-2.5">
                <div className="font-medium text-primary">{p.ticker}</div>
                <div className="text-xs text-secondary">{p.sector}</div>
              </td>
              <td className="tabnum px-2 py-2.5 text-right text-secondary">
                {formatNumber(p.quantity, 0)}
              </td>
              <td className="tabnum px-2 py-2.5 text-right text-secondary">
                {formatCurrency(p.avg_cost)}
              </td>
              <td className="tabnum px-2 py-2.5 text-right text-primary">
                {formatCurrency(p.latest_price)}
              </td>
              <td className="tabnum px-2 py-2.5 text-right text-primary">
                {formatCurrency(p.market_value)}
              </td>
              <td className={`tabnum px-2 py-2.5 text-right ${pnlColor(p.pnl)}`}>
                {formatSignedCurrency(p.pnl)}
              </td>
              <td className={`tabnum px-2 py-2.5 text-right ${pnlColor(p.pnl)}`}>
                {formatSignedPercent(p.pnl_pct)}
              </td>
              <td className="tabnum px-2 py-2.5 text-right text-secondary">
                {formatPercent(p.weight, 1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
