import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Spinner, ErrorState } from "@/components/Spinner";
import { useApi } from "@/hooks/useApi";
import { getMacro, type MacroCard } from "@/lib/api";
import { formatNumber, formatSignedPercent, pnlColor } from "@/lib/format";

/** Tab 4 — Macro: reference indices, FX and rates (mock). */
export function MacroPage() {
  const macro = useApi(getMacro);

  const groups = (macro.data ?? []).reduce<Record<string, MacroCard[]>>(
    (acc, card) => {
      (acc[card.group] ??= []).push(card);
      return acc;
    },
    {},
  );

  return (
    <div>
      <PageHeader
        title="Macro"
        question="¿Cómo está el contexto macro (índices, tasas, dólar)?"
      />

      {macro.loading && (
        <Card>
          <Spinner />
        </Card>
      )}
      {macro.error && (
        <Card>
          <ErrorState message={macro.error} />
        </Card>
      )}

      <div className="space-y-5">
        {Object.entries(groups).map(([group, cards]) => (
          <Card key={group} title={group}>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {cards.map((c) => (
                <div
                  key={c.key}
                  className="rounded-control border border-separator bg-bg/40 p-4"
                >
                  <div className="text-xs font-medium uppercase tracking-wide text-secondary">
                    {c.label}
                  </div>
                  <div className="tabnum mt-1 text-xl font-semibold text-primary">
                    {formatNumber(c.value, c.value >= 1000 ? 0 : 2)}
                    <span className="ml-1 text-xs font-normal text-secondary">
                      {c.unit}
                    </span>
                  </div>
                  <div className={`tabnum mt-0.5 text-sm ${pnlColor(c.change_pct)}`}>
                    {formatSignedPercent(c.change_pct / 100)}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      <p className="mt-4 text-xs text-secondary">
        Fuentes: yfinance (índices, US 10Y), dolarapi.com (dólar MEP/CCL/Blue).
        Riesgo país y BADLAR usan valores de referencia estáticos.
      </p>
    </div>
  );
}
