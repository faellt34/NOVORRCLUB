import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Megaphone, QrCode, MessageSquare, FileText, Bell } from "lucide-react";
import { useApp } from "../../context/AppContext";
const tabs = {
  influencer: [["/influencer", "Início", LayoutDashboard], ["/influencer#campanhas", "Campanhas", Megaphone], ["/influencer/extrato", "Extrato", FileText], ["/mensagens", "Mensagens", MessageSquare]],
  partner: [["/parceiro", "Início", LayoutDashboard], ["/parceiro#validar", "Validar QR", QrCode], ["/mensagens", "Mensagens", MessageSquare], ["/notificacoes", "Avisos", Bell]],
};
export default function MobileNavigation() {
  const { role, unread } = useApp();
  const { pathname, hash } = useLocation();
  if (!tabs[role]) return null;
  return <nav aria-label="Navegação rápida" className="ck-bottom-nav lg:hidden">{tabs[role].map(([to, label, Icon]) => {
    const selected = pathname + hash === to;
    const count = to === "/mensagens" ? unread.messages : to === "/notificacoes" ? unread.notifications : 0;
    return <Link key={to} to={to} aria-current={selected ? "page" : undefined}><span className="relative"><Icon size={20}/>{count > 0 && <span className="ck-mobile-badge">{count > 99 ? "99+" : count}</span>}</span><span>{label}</span></Link>;
  })}</nav>;
}
