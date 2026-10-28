import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, ScanLine, Bell, MessageSquare, FileText, Settings, Wallet, Megaphone, Share2, Users } from "lucide-react";
import { useApp } from "../../context/AppContext";

const TABS = {
  influencer: [
    { to: "/influencer", icon: LayoutDashboard, label: "Painel" },
    { to: "/influencer#campanhas", icon: Megaphone, label: "Cupões" },
    { to: "/influencer#partilhar", icon: Share2, label: "Partilhar", primary: true },
    { to: "/influencer/extrato", icon: FileText, label: "Extrato" },
    { to: "/notificacoes", icon: Bell, label: "Alertas", badge: "notifications" },
  ],
  partner: [
    { to: "/parceiro", icon: LayoutDashboard, label: "Painel" },
    { to: "/parceiro#historico", icon: FileText, label: "Vendas" },
    { to: "/parceiro#validar", icon: ScanLine, label: "Ler QR", primary: true },
    { to: "/mensagens", icon: MessageSquare, label: "Chat", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Alertas", badge: "notifications" },
  ],
  admin: [
    { to: "/admin", icon: LayoutDashboard, label: "Visão" },
    { to: "/admin/gestao", icon: Users, label: "Gestão" },
    { to: "/admin/pagamentos", icon: Wallet, label: "Finanças", primary: true },
    { to: "/admin/definicoes", icon: Settings, label: "Config" },
    { to: "/notificacoes", icon: Bell, label: "Alertas", badge: "notifications" },
  ],
};

const scrollToHash = (to) => {
  const id = to.split("#")[1];
  const el = id ? document.getElementById(id) : null;
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  else if (!id) window.scrollTo({ top: 0, behavior: "smooth" });
};

export const BottomNav = () => {
  const { user, unread } = useApp();
  const { pathname, hash } = useLocation();
  const tabs = TABS[user?.role] || [];
  if (!tabs.length) return null;
  const current = pathname + hash;
  useEffect(() => {
    if (!hash) return;
    const id = decodeURIComponent(hash.slice(1));
    const frame = window.requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }));
    return () => window.cancelAnimationFrame(frame);
  }, [pathname, hash]);
  return (
    <nav data-testid="bottom-nav" aria-label="Navegação principal" className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur-xl border-t border-slate-100 shadow-[0_-8px_25px_rgba(7,11,31,0.08)] pb-[env(safe-area-inset-bottom)]">
      <ul className="flex items-end justify-around px-2 pt-2 pb-2">
        {tabs.map((t) => {
          const count = t.badge ? unread?.[t.badge] || 0 : 0;
          const active = current === t.to || (!t.to.includes("#") && !hash && pathname === t.to);
          return (
            <li key={t.to} className="flex-1">
              <Link to={t.to} aria-current={active ? "page" : undefined} onClick={() => scrollToHash(t.to)}
                data-testid={`bottom-nav-${t.label.toLowerCase().replace(/\s/g, "-")}`}
                className={`relative flex flex-col items-center justify-end gap-1 text-[12px] min-h-[52px] transition-colors duration-200 ${active ? "text-[#7C3AED] font-semibold" : "text-slate-400 font-medium hover:text-slate-600"}`}>
                <span className={`relative flex items-center justify-center transition-transform active:scale-90 ${t.primary ? "w-16 h-16 -mt-8 rounded-full bg-gradient-to-tr from-[#7C3AED] to-[#A78BFA] text-white border-4 border-white shadow-[0_8px_24px_rgba(124,58,237,0.4)]" : "w-10 h-7"}`}>
                  <t.icon className={t.primary ? "w-7 h-7" : "w-[22px] h-[22px]"} />
                  {count > 0 && <span data-testid={`bottom-nav-badge-${t.badge}`} className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-amber-500 text-[10px] font-bold text-white flex items-center justify-center">{count > 99 ? "99+" : count}</span>}
                </span>
                {t.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};
