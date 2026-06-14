import { PageHeader } from "@/components/PageHeader";
import { Placeholder } from "@/components/Placeholder";

/** Tab 2 — Noticias & Sentimiento. */
export function NewsPage() {
  return (
    <div>
      <PageHeader
        title="Noticias & Sentimiento"
        question="¿Qué pasa con mis activos y cómo afecta mi tesis?"
      />
      <Placeholder phase="la Fase 6" />
    </div>
  );
}
