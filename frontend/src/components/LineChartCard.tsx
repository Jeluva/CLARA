import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { colors } from "@/styles/theme";
import type { HistoryPoint } from "@/lib/api";
import { formatSignedPercent } from "@/lib/format";

/** Portfolio cumulative-return evolution vs. benchmark. */
export function LineChartCard({ data }: { data: HistoryPoint[] }) {
  // Show ~12 x-axis labels max to avoid clutter.
  const tickInterval = Math.max(1, Math.floor(data.length / 6));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={colors.separator} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: colors.secondary, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: colors.separator }}
            interval={tickInterval}
            tickFormatter={(d: string) => d.slice(5)}
          />
          <YAxis
            tick={{ fill: colors.secondary, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip
            contentStyle={{
              background: colors.surface,
              border: `1px solid ${colors.separator}`,
              borderRadius: 12,
              color: colors.primary,
              fontSize: 12,
            }}
            labelStyle={{ color: colors.secondary }}
            formatter={(value: number, name: string) => [
              formatSignedPercent(value),
              name === "portfolio" ? "Portfolio" : "Benchmark",
            ]}
          />
          <Line
            type="monotone"
            dataKey="portfolio"
            stroke={colors.accent}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="benchmark"
            stroke={colors.secondary}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
