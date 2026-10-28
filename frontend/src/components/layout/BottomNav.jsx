import { NavLink } from "react-router-dom";
import { LayoutDashboard, QrCode, Bell, MessageSquare, FileText, Settings, Wallet, Megaphone } from "lucide-react";
import { useApp } from "../../context/AppContext";

const TABS = {
  influencer: [
    { to: "/influencer", icon: LayoutDashboard, label: "Painel", end: true },
    { to: "/influencer#campanhas", icon: Megaphone, label: "Cupões" },
    { to: "/influencer/extrato", icon: FileText, label: "Extrato" },
    { to: "/mensagens", icon: MessageSquare, label: "Chat", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Alertas", badge: "notifications" },
  ],
  partner: [
    { to: "/parceiro", icon: LayoutDashboard, label: "Painel", end: true },
    { to: "/parceiro#validar", icon: QrCode, label: "Ler QR", primary: true },
    { to: "/mensagens", icon: MessageSquare, label: "Chat", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Alertas", badge: "notifications" },
  ],
  admin: [
    { to: "/admin", icon: LayoutDashboard, label: "Visão", end: true },
    { to: "/admin/gestao", icon: Settings, label: "Gestão" },
    { to: "/admin/pagamentos", icon: Wallet, label: "Finanças" },
    { to: "/mensagens", icon: MessageSquare, label: "Chat", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Alertas", badge: "notifications" },
  ],
};

export const BottomNav = () => {
  const { user, unread } = useApp();
  const tabs = TABS[user?.role] || [];
  if (!tabs.length) return null;
  return (
    <nav data-testid="bottom-nav" aria-label="Navegação principal" className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-[#070B1F]/95 backdrop-blur-md border-t border-white/10 pb-[env(safe-area-inset-bottom)]">
      <ul className="flex items-stretch justify-around h-16">
        {tabs.map((t) => {
          const count = t.badge ? unread?.[t.badge] || 0 : 0;
          return (
            <li key={t.to} className="flex-1">
              <NavLink to={t.to} end={t.end} data-testid={`bottom-nav-${t.label.toLowerCase().replace(/\s/g, "-")}`}
                className={({ isActive }) => `relative h-full flex flex-col items-center justify-center gap-1 text-[10px] font-semibold transition-colors ${isActive ? "text-violet-300" : "text-white/60 hover:text-white"}`}>
                <span className={`relative flex items-center justify-center rounded-2xl transition-transform ${t.primary ? "w-12 h-12 -mt-6 bg-violet-600 text-white shadow-lg shadow-violet-900/50" : "w-9 h-7"}`}>
                  <t.icon className={t.primary ? "w-6 h-6" : "w-5 h-5"} />
                  {count > 0 && <span data-testid={`bottom-nav-badge-${t.badge}`} className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-amber-500 text-[9px] text-white flex items-center justify-center">{count > 99 ? "99+" : count}</span>}
                </span>
                {t.label}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};
