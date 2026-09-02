/** Navigation model: the five tabs, each answering one investor question. */
export interface NavTab {
  path: string;
  label: string;
  icon: string; // inline SVG path data (24x24 viewBox, stroke-based)
  question: string;
}

export const NAV_TABS: NavTab[] = [
  {
    path: "/",
    label: "Portfolio",
    question: "¿Cómo está parada mi cartera hoy?",
    icon: "M3 13h4v8H3v-8zm7-8h4v16h-4V5zm7 5h4v11h-4V10z",
  },
  {
    path: "/noticias",
    label: "Noticias",
    question: "¿Qué pasa con mis activos y cómo afecta mi tesis?",
    icon: "M4 5h16v14H4V5zm3 4h10M7 12h10M7 15h6",
  },
  {
    path: "/research",
    label: "Research",
    question: "¿Qué me dicen los datos técnicos y las correlaciones?",
    icon: "M4 19V5m0 14h16M8 15l3-4 3 2 4-6",
  },
  {
    path: "/macro",
    label: "Macro",
    question: "¿Cómo está el contexto macro (índices, tasas, dólar)?",
    icon: "M12 3a9 9 0 100 18 9 9 0 000-18zm0 0v18m-9-9h18",
  },
  {
    path: "/screener",
    label: "Screener",
    question: "¿Qué candidatos hay más allá de lo que ya tengo cargado?",
    icon: "M10 4a6 6 0 100 12 6 6 0 000-12zm8 16l-4.35-4.35",
  },
  {
    path: "/datos",
    label: "Ingreso de datos",
    question: "¿Cómo cargo y edito posiciones, transacciones y fuentes?",
    icon: "M12 5v14m-7-7h14",
  },
  {
    path: "/chat",
    label: "Chat",
    question: "¿Qué me dicen mi cartera, las noticias y el contexto macro en conjunto?",
    icon: "M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z",
  },
];
