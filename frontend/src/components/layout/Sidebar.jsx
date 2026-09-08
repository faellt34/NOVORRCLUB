import { useState } from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Megaphone, MessageSquare, BookOpen, Users, QrCode, Gift, ChevronsUpDown, Crown, ShieldCheck, FileText, Settings } from "lucide-react";
import { useApp } from "../../context/AppContext";
import { USERS } from "../../lib/mockData";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { ReferralDialog } from "../ReferralDialog";

const MENUS = {
  influencer: [
    { to: "/influencer", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/influencer#campanhas", icon: Megaphone, label: "Campanhas" },
    { to: "/influencer/extrato", icon: FileText, label: "Extrato Mensal" },
    { to: "/mensagens", icon: MessageSquare, label: "Mensagens", badge: 3 },
    { to: "/ebooks", icon: BookOpen, label: "E-books & Guias" },
  ],
  partner: [
    { to: "/parceiro", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/parceiro#validar", icon: QrCode, label: "Validar Cupom" },
    { to: "/mensagens", icon: MessageSquare, label: "Mensagens", badge: 1 },
  ],
  admin: [
    { to: "/admin", icon: LayoutDashboard, label: "Visão Geral" },
    { to: "/admin/gestao", icon: Settings, label: "Gestão" },
    { to: "/mensagens", icon: MessageSquare, label: "Mensagens", badge: 5 },
    { to: "/ebooks", icon: BookOpen, label: "E-books & Guias" },
  ],
};

const ROLE_ICONS = { influencer: Crown, partner: QrCode, admin: ShieldCheck };

export const SidebarContent = ({ onNavigate }) => {
  const { role, setRole, user } = useApp();
  const [referralOpen, setReferralOpen] = useState(false);
  const items = MENUS[role];

  return (
    <div className="flex flex-col h-full bg-[#0C0A14] text-slate-300">
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2.5" data-testid="sidebar-logo">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center">
            <Crown className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-display font-bold text-white leading-tight">Robson Club</p>
            <p className="text-[10px] uppercase tracking-widest text-purple-400/80">Luxury Experiences</p>
          </div>
        </div>
      </div>

      <div className="px-4 pb-4">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button data-testid="role-switcher-trigger" className="w-full p-3 rounded-xl bg-white/5 border border-white/10 flex items-center gap-3 hover:bg-white/10 transition-colors btn-press text-left">
              <img src={user.avatar} alt={user.name} className="w-9 h-9 rounded-full object-cover" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{user.name}</p>
                <p className="text-xs text-purple-300/80 truncate">{user.label} · {user.handle}</p>
              </div>
              <ChevronsUpDown className="w-4 h-4 text-slate-500 shrink-0" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-64" data-testid="role-switcher-dropdown">
            {Object.values(USERS).map((u) => {
              const Icon = ROLE_ICONS[u.role];
              return (
                <DropdownMenuItem
                  key={u.role}
                  data-testid={`role-option-${u.role}`}
                  onClick={() => { setRole(u.role); onNavigate?.(u.role); }}
                  className="gap-3 py-2.5 cursor-pointer"
                >
                  <span className="w-8 h-8 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center"><Icon className="w-4 h-4" /></span>
                  <span>
                    <span className="block text-sm font-medium">{u.name}</span>
                    <span className="block text-xs text-slate-500">{u.label}</span>
                  </span>
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto" data-testid="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.to + item.label}
            to={item.to}
            end
            data-testid={`nav-${item.label.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-")}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${
                isActive && !item.to.includes("#")
                  ? "bg-gradient-to-r from-purple-600/25 to-purple-500/10 text-purple-200 font-medium border-l-2 border-purple-500"
                  : "hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <item.icon className="w-[18px] h-[18px]" />
            <span className="flex-1">{item.label}</span>
            {item.badge && (
              <span data-testid={`badge-${item.label.toLowerCase()}`} className="min-w-[20px] h-5 px-1.5 rounded-full bg-purple-600 text-white text-[11px] font-bold flex items-center justify-center">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4">
        <div data-testid="referral-card" className="p-4 rounded-2xl bg-gradient-to-br from-purple-900/50 via-purple-950/40 to-[#120F24] border border-purple-500/20">
          <div className="w-9 h-9 rounded-lg bg-purple-500/20 flex items-center justify-center mb-3">
            <Gift className="w-4.5 h-4.5 text-purple-300" style={{ width: 18, height: 18 }} />
          </div>
          <p className="text-sm font-semibold text-white mb-1">Indique um parceiro</p>
          <p className="text-xs text-slate-400 mb-3 leading-relaxed">Conhece um espaço premium? Ganhe bónus por indicação aprovada.</p>
          <button data-testid="referral-button" onClick={() => setReferralOpen(true)} className="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press">
            Indicar agora
          </button>
        </div>
        <ReferralDialog open={referralOpen} onOpenChange={setReferralOpen} />
        <p className="text-[10px] text-slate-600 text-center mt-3 flex items-center justify-center gap-1"><Users className="w-3 h-3" /> RBAC simulado · v1 protótipo</p>
      </div>
    </div>
  );
};
