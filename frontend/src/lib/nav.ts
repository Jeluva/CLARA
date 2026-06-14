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
    path: "/datos",
    label: "Ingreso de datos",
    question: "¿Cómo cargo y edito posiciones, transacciones y fuentes?",
    icon: "M12 5v14m-7-7h14",
  },
];
