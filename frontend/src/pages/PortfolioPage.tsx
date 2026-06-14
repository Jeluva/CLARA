import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Placeholder } from "@/components/Placeholder";
import { Card } from "@/components/Card";
import { getHealth, type HealthResponse } from "@/lib/api";

/** Tab 1 — Portfolio (main). Phase 0: shell + live API connectivity check. */
export function PortfolioPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  return (
    <div>
      <PageHeader
        title="Portfolio"
        question="¿Cómo está parada mi cartera hoy?"
      />
      <div className="mb-5">
        <Card title="Estado del backend" subtitle="Verificación de conectividad">
          {error ? (
            <p className="text-sm text-loss">
              No se pudo contactar la API. ¿Está corriendo uvicorn?
            </p>
          ) : health ? (
            <p className="text-sm text-gain">
              Conectado · {health.app} v{health.version} ({health.environment})
            </p>
          ) : (
            <p className="text-sm text-secondary">Verificando…</p>
          )}
        </Card>
      </div>
      <Placeholder phase="la Fase 4" />
    </div>
  );
}
