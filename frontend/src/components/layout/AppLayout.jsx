import { reportCurrency } from "../../lib/api";
import "../../dashboard.css";
import { useApp } from "../../context/AppContext";
import MobileNavigation from "./MobileNavigation";
import GoogleSignIn from "../GoogleSignIn";
import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { BrandLogo } from "../BrandLogo";
import { SidebarContent } from "./Sidebar";

export default function AppLayout() {
  const { role } = useApp();
  const { pathname, hash } = useLocation();
  useEffect(() => {
    setMobileOpen(false);
    if (!hash) return;
    const scroll = () => {
      const target = document.getElementById(decodeURIComponent(hash.slice(1)));
      if (target) { target.scrollIntoView({ behavior: "auto", block: "start" }); return true; }
      return false;
    };
    if (scroll()) return;
    const observer = new MutationObserver(() => { if (scroll()) observer.disconnect(); });
    observer.observe(document.body, { childList: true, subtree: true });
    const timeout = setTimeout(() => observer.disconnect(), 5000);
    return () => { observer.disconnect(); clearTimeout(timeout); };
  }, [pathname, hash]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const handleRoleNavigate = () => setMobileOpen(false);

  return (
    <div className={`min-h-screen bg-[#F3F5FB] ck-app ${role === "admin" ? "rr-shell" : ""}`}>
      <aside className="hidden lg:block fixed inset-y-0 left-0 w-[268px] z-40">
        <SidebarContent onNavigate={handleRoleNavigate} />
      </aside>

      <header className="lg:hidden sticky top-0 z-50 bg-[#070B1F] text-white flex items-center justify-between px-4 h-14">
        <BrandLogo size="sm" />
        <button aria-label={mobileOpen ? "Fechar menu" : "Abrir menu"} aria-expanded={mobileOpen} data-testid="mobile-menu-toggle" onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-lg hover:bg-white/10 btn-press">
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 top-14 z-40">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-[280px]" data-testid="mobile-sidebar">
            <SidebarContent onNavigate={handleRoleNavigate} />
          </div>
        </div>
      )}

      <main className={`lg:pl-[268px] ${role !== "admin" ? "ck-with-mobile-nav" : ""}`}>
        <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
          <div className="flex justify-end mb-4">
            <label className="text-xs text-slate-600">Moeda dos relatórios
              <select aria-label="Moeda dos relatórios" className="ml-2 rounded-lg border p-2 bg-white" value={reportCurrency()} onChange={(e) => { localStorage.setItem("rrclub_currency", e.target.value); window.location.reload(); }}>
                <option value="eur">EUR · Portugal</option><option value="brl">BRL · Brasil</option>
              </select>
            </label>
          </div>
          <Outlet />
          <details className="mt-8 rounded-xl border bg-white p-4 text-sm text-slate-600"><summary className="cursor-pointer">Segurança da conta · Associar Google</summary><p className="mt-3 text-xs">Associe uma conta Google com o mesmo email para a usar nos próximos acessos.</p><GoogleSignIn linkAccount /></details>
        </div>
      </main>
      <MobileNavigation />
    </div>
  );
}
