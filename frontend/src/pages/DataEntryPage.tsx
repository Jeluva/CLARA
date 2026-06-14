import { PageHeader } from "@/components/PageHeader";
import { Placeholder } from "@/components/Placeholder";

/** Tab 5 — Ingreso de datos. */
export function DataEntryPage() {
  return (
    <div>
      <PageHeader
        title="Ingreso de datos"
        question="¿Cómo cargo y edito posiciones, transacciones y fuentes?"
      />
      <Placeholder phase="la Fase 5" />
    </div>
  );
}
