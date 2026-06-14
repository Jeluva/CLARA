import { PageHeader } from "@/components/PageHeader";
import { Placeholder } from "@/components/Placeholder";

/** Tab 3 — Research / Análisis. */
export function ResearchPage() {
  return (
    <div>
      <PageHeader
        title="Research"
        question="¿Qué me dicen los datos técnicos y las correlaciones?"
      />
      <Placeholder phase="la Fase 7" />
    </div>
  );
}
