import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  createPortfolio as apiCreatePortfolio,
  getPortfolios,
  renamePortfolio as apiRenamePortfolio,
  type Portfolio,
} from "@/lib/api";

const STORAGE_KEY = "clara.activePortfolioId";

interface PortfolioContextValue {
  portfolios: Portfolio[];
  loading: boolean;
  /** null = "Todos" -- every portfolio merged (see BACKLOG.md v3 item 1). */
  activeId: number | null;
  activePortfolio: Portfolio | null;
  setActiveId: (id: number | null) => void;
  createPortfolio: (name: string) => Promise<void>;
  renamePortfolio: (id: number, name: string) => Promise<void>;
}

const PortfolioContext = createContext<PortfolioContextValue | null>(null);

function readStoredId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw || raw === "all") return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

/** Global active-portfolio selection, persisted per-browser in localStorage
 * (not a server preference -- each device can look at a different one). */
export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveIdState] = useState<number | null>(readStoredId);

  useEffect(() => {
    getPortfolios()
      .then((response) => {
        const list = Array.isArray(response) ? response : [];
        setPortfolios(list);
        // A stored id from a portfolio that no longer exists (e.g. a reset
        // dev DB) silently falls back to "Todos" instead of an empty page.
        setActiveIdState((current) =>
          current !== null && !list.some((p) => p.id === current)
            ? null
            : current,
        );
      })
      .catch(() => setPortfolios([]))
      .finally(() => setLoading(false));
  }, []);

  function setActiveId(id: number | null) {
    setActiveIdState(id);
    try {
      localStorage.setItem(STORAGE_KEY, id === null ? "all" : String(id));
    } catch {
      /* private browsing / storage disabled -- selection just won't persist */
    }
  }

  async function createPortfolio(name: string) {
    const created = await apiCreatePortfolio(name);
    setPortfolios((prev) => [...prev, created]);
    setActiveId(created.id);
  }

  async function renamePortfolio(id: number, name: string) {
    const updated = await apiRenamePortfolio(id, name);
    setPortfolios((prev) => prev.map((p) => (p.id === id ? updated : p)));
  }

  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null;

  return (
    <PortfolioContext.Provider
      value={{
        portfolios,
        loading,
        activeId,
        activePortfolio,
        setActiveId,
        createPortfolio,
        renamePortfolio,
      }}
    >
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolios(): PortfolioContextValue {
  const ctx = useContext(PortfolioContext);
  if (!ctx) {
    throw new Error("usePortfolios must be used within a PortfolioProvider");
  }
  return ctx;
}
