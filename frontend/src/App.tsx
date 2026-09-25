import { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { SupplierPricingModule } from './pages/SupplierPricingModule';
import { SupplierPricingHistoryPage } from './pages/SupplierPricingHistoryPage';
import { Header } from './components/Header';

export function App() {
  const [activeModule, setActiveModule] = useState<'quotation' | 'supplier_pricing' | 'history'>('quotation');

  if (activeModule === 'supplier_pricing') {
    return (
      <div className="min-h-screen bg-[#F5F1E8] text-[#26231F] flex flex-col font-sans selection:bg-[#C98B4A]/20 selection:text-[#26231F]">
        <Header
          onReset={() => {}}
          isBusy={false}
          activeModule="supplier_pricing"
          onSelectModule={setActiveModule}
        />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
          <SupplierPricingModule />
        </main>
        <footer className="border-t border-[#786446]/10 bg-white/40 backdrop-blur-md py-5 text-center text-xs text-[#716B61]">
          QuotexAI Enterprise • Supplier Pricing & Zoho Books Module
        </footer>
      </div>
    );
  }

  if (activeModule === 'history') {
    return (
      <div className="min-h-screen bg-[#F5F1E8] text-[#26231F] flex flex-col font-sans selection:bg-[#C98B4A]/20 selection:text-[#26231F]">
        <Header
          onReset={() => {}}
          isBusy={false}
          activeModule="history"
          onSelectModule={setActiveModule}
        />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
          <SupplierPricingHistoryPage />
        </main>
        <footer className="border-t border-[#786446]/10 bg-white/40 backdrop-blur-md py-5 text-center text-xs text-[#716B61]">
          QuotexAI Enterprise • Audit History & Compliance Trail
        </footer>
      </div>
    );
  }

  return <Dashboard activeModule={activeModule} onSelectModule={setActiveModule} />;
}

export default App;
