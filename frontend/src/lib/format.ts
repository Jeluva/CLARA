/** Formatting helpers for money, percentages and signed/colored figures. */

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const usdCompact = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

/** Currency, e.g. $12,345.67 */
export function formatCurrency(value: number, compact = false): string {
  return compact ? usdCompact.format(value) : usd.format(value);
}

/** Percentage from a fraction, e.g. 0.1234 -> "12.34%". */
export function formatPercent(fraction: number, digits = 2): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** Signed percentage, e.g. +12.34% / -5.00%. */
export function formatSignedPercent(fraction: number, digits = 2): string {
  const sign = fraction > 0 ? "+" : "";
  return `${sign}${(fraction * 100).toFixed(digits)}%`;
}

/** Signed currency, e.g. +$1,234.00 / -$56.00 */
export function formatSignedCurrency(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${usd.format(Math.abs(value))}`;
}

/** Tailwind text-color class for a financial value: green up, red down. */
export function pnlColor(value: number): string {
  if (value > 0) return "text-gain";
  if (value < 0) return "text-loss";
  return "text-secondary";
}

/** Number with thousands separators and fixed decimals. */
export function formatNumber(value: number, digits = 2): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Rough relative time in Spanish, e.g. "hace 3 h" / "hace 2 d". */
export function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "recién";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} d`;
}
