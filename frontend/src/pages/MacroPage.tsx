import { PageHeader } from "@/components/PageHeader";
import { Placeholder } from "@/components/Placeholder";

/** Tab 4 — Macro. */
export function MacroPage() {
  return (
    <div>
      <PageHeader
        title="Macro"
        question="¿Cómo está el contexto macro (índices, tasas, dólar)?"
      />
      <Placeholder phase="la Fase 7" />
    </div>
  );
}
