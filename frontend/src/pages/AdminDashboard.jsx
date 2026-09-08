import { useCallback, useEffect, useState } from "react";
import { Euro, HandCoins, Users, Store, Megaphone, ScrollText, Inbox, Check, X } from "lucide-react";
import { toast } from "sonner";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { api, apiError, eur } from "../lib/api";
import { PageSkeleton } from "../components/PageSkeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

const LEAD_STYLE = { Novo: "bg-purple-50 text-purple-700", Aprovada: "bg-emerald-50 text-emerald-600", Rejeitada: "bg-red-50 text-red-500" };

export default function AdminDashboard() {
  const { refreshUnread } = useApp();
  const [data, setData] = useState(null);
  const [audit, setAudit] = useState([]);
  const [leads, setLeads] = useState([]);
  const [decision, setDecision] = useState(null);
  const [note, setNote] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, a, l] = await Promise.all([api.get("/dashboard/admin"), api.get("/audit"), api.get("/leads")]);
      setData(d.data); setAudit(a.data); setLeads(l.data);
    } catch (e) { toast.error(apiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openDecision = (lead, mode) => {
    setDecision({ lead, mode }); setNote("");
    setEmail(/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(lead.contacto) ? lead.contacto : "");
  };

  const confirm = async () => {
    setBusy(true);
    try {
      const { data: res } = await api.post(`/leads/${decision.lead.id}/${decision.mode}`, { note, email: email || null });
      if (decision.mode === "approve") toast.success(`Parceiro "${res.partner.nome}" criado automaticamente${res.access_email ? ` · acesso: ${res.access_email} / parceiro123` : ""}`);
      else toast.success("Indicação rejeitada e influencer notificado");
      setDecision(null); load(); refreshUnread();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  if (!data) return <PageSkeleton />;
  const pending = leads.filter((l) => l.status === "Novo").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="admin-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Visão Geral da Plataforma</h1>
        <p className="text-sm text-slate-500 mt-1">Métricas globais do Robson Club — receita, comissões e entidades ativas</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-sistema" icon={Euro} label="Receita do Sistema" value={eur(Math.round(data.totals.revenue))} trend={data.trend.revenue} period="últimos 30d vs anteriores" />
        <KpiCard id="comissoes-agregadas" icon={HandCoins} label="Comissões Agregadas" value={eur(Math.round(data.totals.commission))} trend={data.trend.commission} period="últimos 30d vs anteriores" />
        <KpiCard id="influencers-ativos" icon={Users} label="Influencers Ativos" value={String(data.counts.influencers)} />
        <KpiCard id="parceiros-ativos" icon={Store} label="Parceiros Ativos" value={String(data.counts.partners)} />
        <KpiCard id="campanhas-ativas" icon={Megaphone} label="Campanhas Ativas" value={String(data.counts.campaigns)} />
      </div>

      <div data-testid="admin-leads-card" className="card-soft p-5">
        <div className="flex items-center gap-2 mb-4">
          <Inbox className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-slate-900">Indicações de Parceiros</h3>
          {pending > 0 && <span data-testid="leads-count-badge" className="min-w-[20px] h-5 px-1.5 rounded-full bg-purple-600 text-white text-[11px] font-bold flex items-center justify-center">{pending}</span>}
        </div>
        {leads.length === 0 ? (
          <p data-testid="leads-empty-state" className="text-sm text-slate-400 py-6 text-center">Sem indicações. Influencers e parceiros podem indicar espaços via "Indicar agora".</p>
        ) : (
          <div className="space-y-3">
            {leads.map((l) => (
              <div key={l.id} data-testid={`lead-${l.id}`} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-50 last:border-0 fade-up">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{l.nome}</p>
                  <p className="text-xs text-slate-500">{l.categoria} · {l.cidade} · {l.contacto} · por {l.referrer}{l.nota ? ` — "${l.nota}"` : ""}</p>
                  {l.decision_note && <p className="text-xs text-slate-400 italic mt-0.5">Nota: {l.decision_note}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span data-testid={`lead-status-${l.id}`} className={`text-xs font-medium px-2.5 py-1 rounded-full ${LEAD_STYLE[l.status]}`}>{l.status}</span>
                  {l.status === "Novo" && (
                    <>
                      <button data-testid={`approve-lead-${l.id}`} onClick={() => openDecision(l, "approve")} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold btn-press"><Check className="w-3.5 h-3.5" /> Aprovar</button>
                      <button data-testid={`reject-lead-${l.id}`} onClick={() => openDecision(l, "reject")} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-red-50 hover:text-red-600 text-slate-600 text-xs font-semibold btn-press"><X className="w-3.5 h-3.5" /> Rejeitar</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div data-testid="admin-campaigns-card" className="card-soft p-5">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Campanhas Recentes</h3>
          <div className="space-y-3">
            {data.campaigns.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-3 pb-3 border-b border-slate-50 last:border-0">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{c.nome}</p>
                  <p className="text-xs text-slate-500">{c.parceiro} · {c.cidade} · {c.influencer} · comissão {c.comissao}%</p>
                </div>
                <StatusBadge status={c.status} />
              </div>
            ))}
          </div>
        </div>

        <div data-testid="audit-log-card" className="card-soft p-5">
          <div className="flex items-center gap-2 mb-4">
            <ScrollText className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-slate-900">Audit Log</h3>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">append-only · servidor</span>
          </div>
          {audit.length === 0 ? (
            <p data-testid="audit-log-empty" className="text-sm text-slate-400 py-8 text-center">Sem entradas.</p>
          ) : (
            <div className="space-y-3 max-h-[380px] overflow-y-auto">
              {audit.map((a) => (
                <div key={a.id} data-testid={`audit-entry-${a.id}`} className="flex items-start gap-3 pb-3 border-b border-slate-50 last:border-0">
                  <span className="text-[10px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md shrink-0">{a.action}</span>
                  <div className="min-w-0">
                    <p className="text-sm text-slate-700">{a.detail}</p>
                    <p className="text-xs text-slate-400">{new Date(a.date).toLocaleString("pt-PT")} · {a.actor}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={!!decision} onOpenChange={() => setDecision(null)}>
        <DialogContent data-testid="lead-decision-dialog" className="max-w-md">
          {decision && (
            <>
              <DialogHeader>
                <DialogTitle>{decision.mode === "approve" ? "Aprovar indicação" : "Rejeitar indicação"}</DialogTitle>
                <DialogDescription>
                  {decision.mode === "approve"
                    ? `"${decision.lead.nome}" será criado automaticamente como parceiro ativo. Se indicar um email, é criada a conta de acesso (palavra-passe inicial: parceiro123).`
                    : `O influencer ${decision.lead.referrer} será notificado da decisão.`}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                {decision.mode === "approve" && (
                  <div>
                    <label className="text-xs font-semibold text-slate-600 mb-1 block">Email de acesso do parceiro (opcional)</label>
                    <Input data-testid="lead-access-email-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="gerencia@espaco.pt" className="rounded-xl bg-slate-50" />
                  </div>
                )}
                <div>
                  <label className="text-xs font-semibold text-slate-600 mb-1 block">Nota {decision.mode === "reject" ? "(motivo)" : "(opcional)"}</label>
                  <Textarea data-testid="lead-decision-note" value={note} onChange={(e) => setNote(e.target.value)} className="rounded-xl bg-slate-50 min-h-[70px]" />
                </div>
                <button data-testid="lead-decision-confirm" disabled={busy} onClick={confirm} className={`w-full py-2.5 rounded-xl text-white text-sm font-semibold btn-press disabled:opacity-60 ${decision.mode === "approve" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-red-600 hover:bg-red-500"}`}>
                  {busy ? "A processar..." : decision.mode === "approve" ? "Confirmar aprovação e criar parceiro" : "Confirmar rejeição"}
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
