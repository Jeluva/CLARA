import { Routes, Route } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";
import { PortfolioPage } from "@/pages/PortfolioPage";
import { NewsPage } from "@/pages/NewsPage";
import { ResearchPage } from "@/pages/ResearchPage";
import { MacroPage } from "@/pages/MacroPage";
import { DataEntryPage } from "@/pages/DataEntryPage";

export default function App() {
  return (
    <div className="flex min-h-screen bg-bg text-primary">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-7">
          <Routes>
            <Route path="/" element={<PortfolioPage />} />
            <Route path="/noticias" element={<NewsPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/macro" element={<MacroPage />} />
            <Route path="/datos" element={<DataEntryPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
