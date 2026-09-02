import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Chatbot } from "@/components/Chatbot";
import { usePortfolios } from "@/hooks/usePortfolios";
import { postPortfolioChat } from "@/lib/api";

const SUGGESTIONS = [
  "¿Cómo está parada mi cartera hoy?",
  "¿Qué activos concentran más riesgo?",
  "¿Qué noticias o transcripciones son relevantes para mis posiciones?",
];

/** Tab — chatbot con contexto de toda la cartera (posiciones, riesgo,
 * exposición, noticias/transcripciones y macro), a diferencia del chat de
 * la ficha de cada activo. El contexto que arma el backend está acotado
 * (ver chat_service._build_portfolio_context): siempre manda un resumen
 * compacto de la cartera + macro, y agrega detalle en profundidad solo del
 * activo puntual que la pregunta menciona (o, si la pregunta es general,
 * las noticias/transcripciones de mayor impacto en la cartera). */
export function ChatPage() {
  const { activeId } = usePortfolios();

  return (
    <div>
      <PageHeader
        title="Chat"
        question="¿Qué me dicen mi cartera, las noticias y el contexto macro en conjunto?"
      />
      <Card title="Asistente de cartera" subtitle="Análisis con IA sobre toda tu cartera">
        <Chatbot
          send={(messages) => postPortfolioChat(activeId, messages)}
          placeholder="Preguntá sobre tu cartera…"
          suggestions={SUGGESTIONS}
          intro="Preguntale al analista de CLARA sobre tu cartera: composición, riesgo, exposición, noticias y contexto macro."
        />
      </Card>
    </div>
  );
}
