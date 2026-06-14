import type { ReactNode } from "react";

interface MetricProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  valueClass?: string;
}

/** A single KPI: small label, large tabular value, optional sub-line. */
export function Metric({ label, value, sub, valueClass }: MetricProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-secondary">
        {label}
      </span>
      <span
        className={[
          "tabnum text-2xl font-semibold leading-none text-primary",
          valueClass ?? "",
        ].join(" ")}
      >
        {value}
      </span>
      {sub && <span className="tabnum text-sm">{sub}</span>}
    </div>
  );
}
