import { Routes, Route } from "react-router-dom";
import { TopNav } from "@/components/TopNav";
import { PortfolioPage } from "@/pages/PortfolioPage";
import { NewsPage } from "@/pages/NewsPage";
import { ResearchPage } from "@/pages/ResearchPage";
import { MacroPage } from "@/pages/MacroPage";
import { DataEntryPage } from "@/pages/DataEntryPage";
import { AssetDetailPage } from "@/pages/AssetDetailPage";

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-primary">
      <TopNav />
      <main>
        <div className="mx-auto max-w-6xl px-8 py-7">
          <Routes>
            <Route path="/" element={<PortfolioPage />} />
            <Route path="/noticias" element={<NewsPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/macro" element={<MacroPage />} />
            <Route path="/datos" element={<DataEntryPage />} />
            <Route path="/activo/:ticker" element={<AssetDetailPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
