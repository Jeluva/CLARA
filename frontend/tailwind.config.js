/** @type {import('tailwindcss').Config} */
// Theme tokens — single source of truth for CLARA's dark/iOS visual language.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces
        bg: "#0D0D0F", // app background (near black)
        surface: "#1C1C1E", // cards / panels
        separator: "#2C2C2E", // borders / dividers
        elevated: "#2C2C2E",
        // Text
        primary: "#FFFFFF",
        secondary: "#8E8E93",
        // Accent + financial semantics
        accent: "#0A84FF", // iOS blue: selection, links, CTAs
        gain: "#30D158", // green: profit / positive sentiment
        loss: "#FF453A", // red: loss / negative sentiment
        warn: "#FF9F0A", // orange: alert / neutral-with-risk
      },
      fontFamily: {
        sans: [
          "Inter",
          "SF Pro Text",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "sans-serif",
        ],
      },
      borderRadius: {
        card: "16px",
        control: "12px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.30), 0 8px 24px rgba(0,0,0,0.25)",
      },
      transitionDuration: {
        DEFAULT: "180ms",
      },
    },
  },
  plugins: [],
};
