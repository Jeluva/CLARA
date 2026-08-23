import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/Card";
import {
  getAlerts,
  getTheses,
  getFreshness,
  type Alert,
  type Thesis,
  type Freshness,
} from "@/lib/api";
import { formatRelativeTime, formatSignedPercent } from "@/lib/format";

const THESIS_LABEL: Record<string, string> = {
  objetivo_alcanzado: "Objetivo alcanzado",
  stop_tocado: "Stop tocado",
};

/** "¿Qué necesita mi atención hoy?" — junta alertas disparadas, tesis que
 * llegaron a su objetivo/stop y fuentes desactualizadas en un solo lugar,
 * en vez de obligar a entrar a Alertas/Diario de tesis/Ingreso de datos
 * para enterarse (docs/devlog/BACKLOG.md, v4 ítem 3). Composición sobre
 * datos que los servicios ya calculan — sin cómputo nuevo. */
export function ExecutiveSummary() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [freshness, setFreshness] = useState<Freshness[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getAlerts({ onlyTriggered: true }).catch(() => []),
      getTheses().catch(() => []),
      getFreshness().catch(() => []),
    ]).then(([a, t, f]) => {
      setAlerts(a);
      setTheses(t.filter((x) => x.status === "objetivo_alcanzado" || x.status === "stop_tocado"));
      setFreshness(
        f.filter((x) => x.last_success_at === null || x.last_attempt_at !== x.last_success_at),
      );
      setLoading(false);
    });
  }, []);

  if (loading) return null;

  const nothingToShow = alerts.length === 0 && theses.length === 0 && freshness.length === 0;

  return (
    <Card title="Resumen ejecutivo" subtitle="¿Qué necesita atención hoy?" className="mb-5">
      {nothingToShow ? (
        <p className="text-sm text-secondary">
          Todo en orden: sin alertas disparadas, tesis en curso y datos frescos.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <SummarySection title={`Alertas disparadas (${alerts.length})`} empty="Sin alertas">
            {alerts.map((a) => (
              <button
                key={a.id}
                onClick={() => navigate(`/activo/${a.ticker}`)}
                className="block w-full rounded-control px-2 py-1.5 text-left text-xs transition-colors duration-150 hover:bg-separator/40"
              >
                <span className="font-medium text-primary">{a.ticker}</span>{" "}
                <span className="text-secondary">
                  {a.metric} {a.condition === "above" ? "≥" : "≤"} {a.threshold}
                </span>
              </button>
            ))}
          </SummarySection>

          <SummarySection title={`Tesis a revisar (${theses.length})`} empty="Sin novedades">
            {theses.map((t) => (
              <button
                key={t.id}
                onClick={() => navigate(`/activo/${t.ticker}`)}
                className="block w-full rounded-control px-2 py-1.5 text-left text-xs transition-colors duration-150 hover:bg-separator/40"
              >
                <span className="font-medium text-primary">{t.ticker}</span>{" "}
                <span
                  className={
                    t.status === "objetivo_alcanzado" ? "text-gain" : "text-loss"
                  }
                >
                  {THESIS_LABEL[t.status]}
                </span>
                {t.return_since_entry !== null && (
                  <span className="text-secondary">
                    {" "}
                    ({formatSignedPercent(t.return_since_entry)})
                  </span>
                )}
              </button>
            ))}
          </SummarySection>

          <SummarySection
            title={`Fuentes desactualizadas (${freshness.length})`}
            empty="Todo fresco"
          >
            {freshness.map((f) => (
              <button
                key={f.source}
                onClick={() => navigate("/datos")}
                className="block w-full rounded-control px-2 py-1.5 text-left text-xs transition-colors duration-150 hover:bg-separator/40"
              >
                <span className="font-medium text-primary">{f.label}</span>{" "}
                <span className="text-secondary">
                  {f.last_success_at ? formatRelativeTime(f.last_success_at) : "nunca"}
                </span>
              </button>
            ))}
          </SummarySection>
        </div>
      )}
    </Card>
  );
}

function SummarySection({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: ReactNode;
}) {
  const hasItems = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <div>
      <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-secondary">
        {title}
      </h3>
      {hasItems ? (
        <div className="divide-y divide-separator/60">{children}</div>
      ) : (
        <p className="text-xs text-secondary">{empty}</p>
      )}
    </div>
  );
}
