import { useState } from "react";
import { NavLink, useNavigate, Link } from "react-router-dom";
import { LayoutDashboard, Megaphone, MessageSquare, BookOpen, QrCode, Gift, Crown, ShieldCheck, FileText, Settings, LogOut, Bell, Wallet, Lightbulb, SlidersHorizontal, Briefcase } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../../context/AppContext";
import { useT } from "../../context/I18nContext";
import { slug } from "../../lib/api";
import { ReferralDialog } from "../ReferralDialog";
import { FeedbackDialog } from "../FeedbackDialog";
import { LanguageSwitcher } from "../LanguageSwitcher";
import { InstallAppButton } from "../InstallAppButton";
import { GlobeCanvas } from "../GlobeCanvas";

const MENUS = {
  influencer: [
    { to: "/influencer", icon: LayoutDashboard, key: "dashboard", id: "dashboard" },
    { to: "/influencer#campanhas", icon: Megaphone, key: "campaigns", id: "campanhas" },
    { to: "/influencer/extrato", icon: FileText, key: "statement", id: "extrato-mensal" },
    { to: "/mensagens", icon: MessageSquare, key: "messages", id: "mensagens", badge: "messages" },
    { to: "/notificacoes", icon: Bell, key: "notifications", id: "notificacoes", badge: "notifications" },
    { to: "/ebooks", icon: BookOpen, key: "ebooks", id: "e-books-guias" },
  ],
  partner: [
    { to: "/parceiro", icon: LayoutDashboard, key: "dashboard", id: "dashboard" },
    { to: "/parceiro#validar", icon: QrCode, key: "validate", id: "validar-cupom" },
    { to: "/mensagens", icon: MessageSquare, key: "messages", id: "mensagens", badge: "messages" },
    { to: "/notificacoes", icon: Bell, key: "notifications", id: "notificacoes", badge: "notifications" },
  ],
  admin: [
    { to: "/admin", icon: LayoutDashboard, key: "overview", id: "visao-geral" },
    { to: "/admin/gestao", icon: Settings, key: "manage", id: "gestao" },
    { to: "/admin/pagamentos", icon: Wallet, key: "payouts", id: "pagamentos" },
    { to: "/admin/definicoes", icon: SlidersHorizontal, key: "settings", id: "definicoes" },
    { to: "/admin/diretor", icon: Briefcase, key: "diretor", id: "diretor" },
    { to: "/mensagens", icon: MessageSquare, key: "messages", id: "mensagens", badge: "messages" },
    { to: "/notificacoes", icon: Bell, key: "notifications", id: "notificacoes", badge: "notifications" },
    { to: "/ebooks", icon: BookOpen, key: "ebooks", id: "e-books-guias" },
  ],
};

const ROLE_LABEL = { influencer: "Influencer", partner: "Parceiro", admin: "Admin" };
import { BrandMark } from "../BrandLogo";
const ROLE_ICONS = { influencer: Crown, partner: QrCode, admin: ShieldCheck };

export const SidebarContent = ({ onNavigate }) => {
  const { user, logout, unread } = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [referralOpen, setReferralOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const items = MENUS[user.role];
  const RoleIcon = ROLE_ICONS[user.role];

  const handleLogout = async () => {
    await logout();
    toast.success("Sessão terminada");
    navigate("/login");
  };

  return (
    <div className="flex flex-col h-full bg-[#070B1F] text-slate-300 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-72 pointer-events-none" data-testid="sidebar-globe">
        <div className="absolute inset-0 opacity-70"><GlobeCanvas color="129,140,248" interactive={false} /></div>
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#070B1F]/30 to-[#070B1F]" />
      </div>
      <div className="relative px-5 pt-6 pb-4">
        <div className="flex items-center gap-2.5" data-testid="sidebar-logo">
          <BrandMark className="w-9 h-9" />
          <div>
            <p className="font-display font-extrabold text-white leading-tight"><span className="text-indigo-400">RR</span>Club</p>
            <p className="text-[10px] uppercase tracking-widest text-indigo-300/80">Luxury Experiences</p>
          </div>
        </div>
      </div>

      <div className="relative px-4 pb-4">
        <div data-testid="sidebar-user-card" className="w-full p-3 rounded-xl bg-white/[0.06] backdrop-blur-md border border-white/10 flex items-center gap-3">
          <img src={user.avatar} alt={user.nome} className="w-10 h-10 rounded-full object-cover ring-2 ring-indigo-400/40" />
          <div className="flex-1 min-w-0">
            <p data-testid="sidebar-user-name" className="text-sm font-semibold text-white truncate">{user.nome}</p>
            <p data-testid="sidebar-user-role" className="text-xs text-indigo-200/70 truncate flex items-center gap-1"><RoleIcon className="w-3 h-3" /> {ROLE_LABEL[user.role]} · {user.handle || user.email}</p>
          </div>
        </div>
      </div>

      <nav className="relative flex-1 px-3 space-y-1 overflow-y-auto" data-testid="sidebar-nav">
        {items.map((item) => {
          const count = item.badge ? unread[item.badge] : 0;
          return (
            <NavLink key={item.to + item.key} to={item.to} end onClick={() => onNavigate?.()} data-testid={`nav-${item.id}`}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${isActive && !item.to.includes("#") ? "bg-indigo-500/15 text-white font-medium border border-indigo-400/30 shadow-[inset_0_0_24px_-12px_#6366f1]" : "hover:bg-white/5 hover:text-white"}`}>
              <item.icon className="w-[18px] h-[18px]" />
              <span className="flex-1">{t(item.key)}</span>
              {count > 0 && <span data-testid={`badge-${item.id}`} className="min-w-[20px] h-5 px-1.5 rounded-full bg-indigo-500 text-white text-[11px] font-bold flex items-center justify-center">{count}</span>}
            </NavLink>
          );
        })}
        <InstallAppButton />
        <button data-testid="feedback-button" onClick={() => setFeedbackOpen(true)} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm hover:bg-white/5 hover:text-white transition-colors text-left">
          <Lightbulb className="w-[18px] h-[18px] text-amber-400" /><span className="flex-1">{t("suggest")}</span>
        </button>
      </nav>

      <div className="relative p-4 space-y-3">
        {user.role === "admin" && (
          <div data-testid="sidebar-system-status" className="p-3 rounded-xl bg-white/[0.04] border border-white/10">
            <p className="text-xs font-semibold text-white flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-400 live-dot" /> Sistema operacional</p>
            <p className="text-[10px] text-slate-400 mt-1">Audit log ativo · Dados sincronizados</p>
            <p className="text-[10px] text-slate-500">Última atualização: {new Date().toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}</p>
          </div>
        )}
        {user.role !== "admin" && (
          <div data-testid="referral-card" className="p-4 rounded-2xl bg-gradient-to-br from-purple-900/50 via-purple-950/40 to-[#120F24] border border-purple-500/20">
            <div className="w-9 h-9 rounded-lg bg-purple-500/20 flex items-center justify-center mb-3"><Gift className="text-purple-300" style={{ width: 18, height: 18 }} /></div>
            <p className="text-sm font-semibold text-white mb-1">{t("referTitle")}</p>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">{t("referText")}</p>
            <button data-testid="referral-button" onClick={() => setReferralOpen(true)} className="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press">{t("referNow")}</button>
          </div>
        )}
        <ReferralDialog open={referralOpen} onOpenChange={setReferralOpen} />
        <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
        <div className="flex items-center justify-between gap-2">
          <LanguageSwitcher dark />
          <Link to="/privacidade" data-testid="privacy-link" className="text-[11px] text-slate-500 hover:text-white">{t("privacy")}</Link>
        </div>
        <button data-testid="logout-button" onClick={handleLogout} className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 text-sm text-slate-300 hover:text-white btn-press">
          <LogOut className="w-4 h-4" /> {t("logout")}
        </button>
      </div>
    </div>
  );
};
