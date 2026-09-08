import { useEffect, useState } from "react";
import { Bell, CheckCheck, Ticket, Inbox, MessageSquare, ThumbsUp, ThumbsDown } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { api, apiError } from "../lib/api";

const ICONS = { redencao: Ticket, lead: Inbox, mensagem: MessageSquare, lead_aprovada: ThumbsUp, lead_rejeitada: ThumbsDown };

export default function Notifications() {
  const { refreshUnread } = useApp();
  const [items, setItems] = useState(null);

  const load = () => api.get("/notifications").then((r) => setItems(r.data.items)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);

  const markAll = async () => {
    await api.post("/notifications/read");
    setItems((p) => p.map((i) => ({ ...i, lido: true })));
    refreshUnread();
    toast.success("Todas as notificações marcadas como lidas");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 data-testid="notifications-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Notificações</h1>
          <p className="text-sm text-slate-500 mt-1">Redenções, indicações e mensagens — geradas automaticamente pelo servidor</p>
        </div>
        {items?.some((i) => !i.lido) && (
          <button data-testid="mark-all-read-button" onClick={markAll} className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-purple-50 text-slate-700 text-xs font-semibold btn-press"><CheckCheck className="w-4 h-4" /> Marcar todas como lidas</button>
        )}
      </div>

      <div className="card-soft divide-y divide-slate-50" data-testid="notifications-list">
        {items === null && <p className="p-6 text-sm text-slate-400">A carregar...</p>}
        {items?.length === 0 && (
          <div className="p-12 text-center" data-testid="notifications-empty">
            <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-400">Sem notificações por agora.</p>
          </div>
        )}
        {items?.map((n) => {
          const Icon = ICONS[n.tipo] || Bell;
          return (
            <Link to={n.link || "#"} key={n.id} data-testid={`notification-${n.id}`} className={`flex items-start gap-3 p-4 hover:bg-purple-50/40 transition-colors ${n.lido ? "" : "bg-purple-50/60"}`}>
              <span className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${n.lido ? "bg-slate-100 text-slate-500" : "bg-purple-600 text-white"}`}><Icon className="w-4 h-4" /></span>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${n.lido ? "text-slate-700" : "font-semibold text-slate-900"}`}>{n.titulo}</p>
                <p className="text-xs text-slate-500 mt-0.5">{n.texto}</p>
                <p className="text-[11px] text-slate-400 mt-1">{new Date(n.date).toLocaleString("pt-PT")}</p>
              </div>
              {!n.lido && <span className="w-2 h-2 rounded-full bg-purple-600 mt-2" />}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
