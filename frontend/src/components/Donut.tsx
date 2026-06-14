import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { chartPalette } from "@/styles/theme";
import { formatPercent } from "@/lib/format";

interface DonutProps {
  title: string;
  data: Record<string, number>; // category -> weight (fraction)
}

/** Exposure donut: weights by category, legend with percentages. */
export function Donut({ title, data }: DonutProps) {
  const entries = Object.entries(data)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  if (entries.length === 0) {
    return (
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-secondary">
          {title}
        </h3>
        <p className="text-sm text-secondary">Sin datos</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-secondary">
        {title}
      </h3>
      <div className="flex items-center gap-4">
        <div className="h-28 w-28 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={entries}
                dataKey="value"
                nameKey="name"
                innerRadius={34}
                outerRadius={54}
                paddingAngle={2}
                stroke="none"
              >
                {entries.map((_, i) => (
                  <Cell
                    key={i}
                    fill={chartPalette[i % chartPalette.length]}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="flex-1 space-y-1.5">
          {entries.map((e, i) => (
            <li
              key={e.name}
              className="flex items-center justify-between gap-2 text-sm"
            >
              <span className="flex items-center gap-2 text-secondary">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: chartPalette[i % chartPalette.length] }}
                />
                {e.name}
              </span>
              <span className="tabnum text-primary">
                {formatPercent(e.value, 1)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
