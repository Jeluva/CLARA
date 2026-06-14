import { describe, it, expect } from "vitest";
import {
  formatCurrency,
  formatPercent,
  formatSignedPercent,
  formatSignedCurrency,
  pnlColor,
} from "@/lib/format";

describe("format helpers", () => {
  it("formats currency", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });

  it("formats percent from a fraction", () => {
    expect(formatPercent(0.1234)).toBe("12.34%");
  });

  it("formats signed percent with explicit + for gains", () => {
    expect(formatSignedPercent(0.05)).toBe("+5.00%");
    expect(formatSignedPercent(-0.05)).toBe("-5.00%");
  });

  it("formats signed currency", () => {
    expect(formatSignedCurrency(1234)).toBe("+$1,234.00");
    expect(formatSignedCurrency(-50)).toBe("-$50.00");
  });

  it("maps sign to semantic color classes", () => {
    expect(pnlColor(10)).toBe("text-gain");
    expect(pnlColor(-10)).toBe("text-loss");
    expect(pnlColor(0)).toBe("text-secondary");
  });
});
