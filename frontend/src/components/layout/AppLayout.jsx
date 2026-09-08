import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu, X, Crown } from "lucide-react";
import { SidebarContent } from "./Sidebar";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const handleRoleNavigate = () => setMobileOpen(false);

  return (
    <div className="min-h-screen bg-[#F8F9FC]">
      <aside className="hidden lg:block fixed inset-y-0 left-0 w-[268px] z-40">
        <SidebarContent onNavigate={handleRoleNavigate} />
      </aside>

      <header className="lg:hidden sticky top-0 z-50 bg-[#0C0A14] text-white flex items-center justify-between px-4 h-14">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center">
            <Crown className="w-4 h-4" />
          </div>
          <span className="font-display font-bold">Robson Club</span>
        </div>
        <button data-testid="mobile-menu-toggle" onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-lg hover:bg-white/10 btn-press">
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

      <main className="lg:pl-[268px]">
        <div className="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
