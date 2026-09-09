import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Megaphone, MessageSquare, BookOpen, QrCode, Gift, Crown, ShieldCheck, FileText, Settings, LogOut, Bell, Wallet } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../../context/AppContext";
import { slug } from "../../lib/api";
import { ReferralDialog } from "../ReferralDialog";

const MENUS = {
  influencer: [
    { to: "/influencer", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/influencer#campanhas", icon: Megaphone, label: "Campanhas" },
    { to: "/influencer/extrato", icon: FileText, label: "Extrato Mensal" },
    { to: "/mensagens", icon: MessageSquare, label: "Mensagens", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Notificações", badge: "notifications" },
    { to: "/ebooks", icon: BookOpen, label: "E-books & Guias" },
  ],
  partner: [
    { to: "/parceiro", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/parceiro#validar", icon: QrCode, label: "Validar Cupom" },
    { to: "/mensagens", icon: MessageSquare, label: "Mensagens", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Notificações", badge: "notifications" },
  ],
  admin: [
    { to: "/admin", icon: LayoutDashboard, label: "Visão Geral" },
    { to: "/admin/gestao", icon: Settings, label: "Gestão" },
    { to: "/admin/pagamentos", icon: Wallet, label: "Pagamentos" },
    { to: "/mensagens", icon: MessageSquare, label: "Mensagens", badge: "messages" },
    { to: "/notificacoes", icon: Bell, label: "Notificações", badge: "notifications" },
    { to: "/ebooks", icon: BookOpen, label: "E-books & Guias" },
  ],
};

const ROLE_LABEL = { influencer: "Influencer", partner: "Parceiro", admin: "Admin" };
const ROLE_ICONS = { influencer: Crown, partner: QrCode, admin: ShieldCheck };

export const SidebarContent = ({ onNavigate }) => {
  const { user, logout, unread } = useApp();
  const navigate = useNavigate();
  const [referralOpen, setReferralOpen] = useState(false);
  const items = MENUS[user.role];
  const RoleIcon = ROLE_ICONS[user.role];

  const handleLogout = async () => {
    await logout();
    toast.success("Sessão terminada");
    navigate("/login");
  };

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
        <div data-testid="sidebar-user-card" className="w-full p-3 rounded-xl bg-white/5 border border-white/10 flex items-center gap-3">
          <img src={user.avatar} alt={user.nome} className="w-9 h-9 rounded-full object-cover" />
          <div className="flex-1 min-w-0">
            <p data-testid="sidebar-user-name" className="text-sm font-semibold text-white truncate">{user.nome}</p>
            <p data-testid="sidebar-user-role" className="text-xs text-purple-300/80 truncate flex items-center gap-1"><RoleIcon className="w-3 h-3" /> {ROLE_LABEL[user.role]} · {user.handle || user.email}</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto" data-testid="sidebar-nav">
        {items.map((item) => {
          const count = item.badge ? unread[item.badge] : 0;
          return (
            <NavLink
              key={item.to + item.label}
              to={item.to}
              end
              onClick={() => onNavigate?.()}
              data-testid={`nav-${slug(item.label)}`}
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
              {count > 0 && (
                <span data-testid={`badge-${slug(item.label)}`} className="min-w-[20px] h-5 px-1.5 rounded-full bg-purple-600 text-white text-[11px] font-bold flex items-center justify-center">
                  {count}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 space-y-3">
        {user.role !== "admin" && (
          <div data-testid="referral-card" className="p-4 rounded-2xl bg-gradient-to-br from-purple-900/50 via-purple-950/40 to-[#120F24] border border-purple-500/20">
            <div className="w-9 h-9 rounded-lg bg-purple-500/20 flex items-center justify-center mb-3">
              <Gift className="text-purple-300" style={{ width: 18, height: 18 }} />
            </div>
            <p className="text-sm font-semibold text-white mb-1">Indique um parceiro</p>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">Conhece um espaço premium? Ganhe bónus por indicação aprovada.</p>
            <button data-testid="referral-button" onClick={() => setReferralOpen(true)} className="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press">
              Indicar agora
            </button>
          </div>
        )}
        <ReferralDialog open={referralOpen} onOpenChange={setReferralOpen} />
        <button data-testid="logout-button" onClick={handleLogout} className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 text-sm text-slate-300 hover:text-white btn-press">
          <LogOut className="w-4 h-4" /> Terminar sessão
        </button>
      </div>
    </div>
  );
};
