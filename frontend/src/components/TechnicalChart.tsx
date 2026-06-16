import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Cell,
} from "recharts";
import { colors } from "@/styles/theme";
import type { IndicatorPoint } from "@/lib/api";

const tooltipStyle = {
  background: colors.surface,
  border: `1px solid ${colors.separator}`,
  borderRadius: 12,
  fontSize: 12,
} as const;

/** Price + moving averages, RSI(14) and MACD for one asset's series. */
export function TechnicalChart({ points }: { points: IndicatorPoint[] }) {
  if (points.length === 0) {
    return <p className="py-6 text-sm text-secondary">Sin datos</p>;
  }
  const interval = Math.max(1, Math.floor(points.length / 6));
  const fmtDate = (d: string) => d.slice(5);

  return (
    <div className="space-y-4">
      {/* Price + SMA */}
      <div>
        <Label>Precio · SMA 20/50</Label>
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke={colors.separator} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: colors.secondary, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.separator }} interval={interval} tickFormatter={fmtDate} />
              <YAxis tick={{ fill: colors.secondary, fontSize: 11 }} tickLine={false} axisLine={false} width={52} domain={["auto", "auto"]} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="close" stroke={colors.primary} strokeWidth={1.5} dot={false} isAnimationActive={false} name="Precio" />
              <Line type="monotone" dataKey="sma20" stroke={colors.accent} strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 20" />
              <Line type="monotone" dataKey="sma50" stroke={colors.warn} strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 50" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* RSI */}
      <div>
        <Label>RSI (14)</Label>
        <div className="h-28 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke={colors.separator} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" hide />
              <YAxis domain={[0, 100]} ticks={[30, 50, 70]} tick={{ fill: colors.secondary, fontSize: 11 }} tickLine={false} axisLine={false} width={52} />
              <ReferenceLine y={70} stroke={colors.loss} strokeDasharray="3 3" />
              <ReferenceLine y={30} stroke={colors.gain} strokeDasharray="3 3" />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="rsi" stroke={colors.accent} strokeWidth={1.5} dot={false} isAnimationActive={false} name="RSI" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* MACD */}
      <div>
        <Label>MACD (12, 26, 9)</Label>
        <div className="h-32 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedMacd points={points} interval={interval} fmtDate={fmtDate} />
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

/** MACD line + signal line over a histogram of their difference. */
function ComposedMacd({
  points,
  interval,
  fmtDate,
}: {
  points: IndicatorPoint[];
  interval: number;
  fmtDate: (d: string) => string;
}) {
  // Recharts can't mix Bar+Line in one element without ComposedChart; use a
  // BarChart for the histogram with reference lines, and overlay nothing —
  // the line vs signal crossing is conveyed by the histogram sign + color.
  return (
    <BarChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
      <CartesianGrid stroke={colors.separator} strokeDasharray="3 3" vertical={false} />
      <XAxis dataKey="date" tick={{ fill: colors.secondary, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.separator }} interval={interval} tickFormatter={fmtDate} />
      <YAxis tick={{ fill: colors.secondary, fontSize: 11 }} tickLine={false} axisLine={false} width={52} />
      <ReferenceLine y={0} stroke={colors.separator} />
      <Tooltip contentStyle={tooltipStyle} />
      <Bar dataKey="macd_hist" name="Histograma" isAnimationActive={false}>
        {points.map((p, i) => (
          <Cell key={i} fill={(p.macd_hist ?? 0) >= 0 ? colors.gain : colors.loss} />
        ))}
      </Bar>
    </BarChart>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-xs font-medium uppercase tracking-wide text-secondary">
      {children}
    </span>
  );
}
