import type { SentimentLabel } from "@/lib/api";

const STYLES: Record<SentimentLabel, { cls: string; text: string }> = {
  positive: { cls: "bg-gain/15 text-gain", text: "Positivo" },
  neutral: { cls: "bg-secondary/15 text-secondary", text: "Neutral" },
  negative: { cls: "bg-loss/15 text-loss", text: "Negativo" },
};

/** Colored sentiment pill with the numeric score. */
export function SentimentTag({
  label,
  score,
}: {
  label: SentimentLabel;
  score?: number;
}) {
  const s = STYLES[label];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}
    >
      {s.text}
      {score !== undefined && (
        <span className="tabnum opacity-80">
          {score > 0 ? "+" : ""}
          {score.toFixed(2)}
        </span>
      )}
    </span>
  );
}
