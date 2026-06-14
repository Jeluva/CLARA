/**
 * Theme tokens mirrored in TS for use in JS contexts (Recharts props, inline
 * styles) where Tailwind classes don't reach. Keep in sync with
 * tailwind.config.js — this is the canvas/chart-facing copy of the palette.
 */
export const colors = {
  bg: "#0D0D0F",
  surface: "#1C1C1E",
  separator: "#2C2C2E",
  primary: "#FFFFFF",
  secondary: "#8E8E93",
  accent: "#0A84FF",
  gain: "#30D158",
  loss: "#FF453A",
  warn: "#FF9F0A",
} as const;

/** Palette for categorical series (sectors, currencies) in charts. */
export const chartPalette = [
  "#0A84FF",
  "#30D158",
  "#FF9F0A",
  "#FF453A",
  "#BF5AF2",
  "#64D2FF",
  "#FFD60A",
  "#5E5CE6",
] as const;
