import type { Correlation } from "@/lib/api";

/** Color a correlation value: blue for +, red for -, faded near 0. */
function cellColor(v: number): string {
  const a = Math.min(1, Math.abs(v));
  if (v >= 0) return `rgba(10, 132, 255, ${0.15 + a * 0.7})`; // accent blue
  return `rgba(255, 69, 58, ${0.15 + a * 0.7})`; // loss red
}

/** Correlation matrix as a colored grid. */
export function Heatmap({ data }: { data: Correlation }) {
  const { tickers, matrix } = data;
  if (tickers.length === 0) {
    return <p className="py-6 text-sm text-secondary">Sin datos</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="border-separate" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="px-2 py-1" />
            {tickers.map((t) => (
              <th
                key={t}
                className="px-2 py-1 text-xs font-medium text-secondary"
              >
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={tickers[i]}>
              <td className="px-2 py-1 text-right text-xs font-medium text-secondary">
                {tickers[i]}
              </td>
              {row.map((v, j) => (
                <td
                  key={j}
                  title={`${tickers[i]} / ${tickers[j]}: ${v.toFixed(2)}`}
                  className="tabnum h-9 w-12 rounded text-center text-xs text-primary"
                  style={{ background: cellColor(v) }}
                >
                  {v.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
