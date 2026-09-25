import { useCallback, useEffect, useState } from "react";
import { Euro, HandCoins, Users, Store, Megaphone, ScrollText, Inbox, Check, X, KeyRound, Copy, Lightbulb, Radio } from "lucide-react";
import { toast } from "sonner";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { api, apiError, eur } from "../lib/api";
import { useRealtime } from "../services/ws";
import { useFlash } from "../services/live";
import { RecentClicks } from "../components/RecentClicks";
import { PageSkeleton } from "../components/PageSkeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

const LEAD_STYLE = { Novo: "bg-purple-50 text-purple-700", Aprovada: "bg-emerald-50 text-emerald-600", Rejeitada: "bg-red-50 text-red-500" };
const TAG_STYLE = { ERRO: "text-red-600 bg-red-50", REDENÇÃO: "text-emerald-700 bg-emerald-50", INDICAÇÃO: "text-purple-700 bg-purple-50", CUPONS: "text-amber-700 bg-amber-50" };
const AUDIT_LIMIT = 8;

export default function AdminDashboard() {
  const { refreshUnread } = useApp();
  const [data, setData] = useState(null);
  const [stats, setStats] = useState({ receita: 0, comissoes: 0, influencers: 0, parceiros: 0, campanhas: 0 });
  const [audit, setAudit] = useState([]);
  const [flash, triggerFlash] = useFlash();
  const [wsState, setWsState] = useState("a ligar");
  const [clicksKey, setClicksKey] = useState(0);
  const [leads, setLeads] = useState([]);
  const [resets, setResets] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [decision, setDecision] = useState(null);
  const [note, setNote] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, a, l, r, f] = await Promise.all([api.get("/dashboard/admin"), api.get("/audit"), api.get("/leads"), api.get("/admin/reset-requests"), api.get("/admin/feedback")]);
      setData(d.data); setAudit(a.data); setLeads(l.data); setResets(r.data); setFeedback(f.data);
      setStats({ receita: d.data.totals.revenue, comissoes: d.data.totals.commission, influencers: d.data.counts.influencers, parceiros: d.data.counts.partners, campanhas: d.data.counts.campaigns });
    } catch (e) { toast.error(apiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const pushAudit = (action, detail, amount, extra = {}) =>
    setAudit((prev) => [{ id: `live-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, action, detail, amount, date: new Date().toISOString(), actor: "tempo real", enter: true, ...extra }, ...prev].slice(0, 50));

  useRealtime((ev) => {
    if (ev.tipo === "ligado") { setWsState("ao vivo"); return; }
    if (ev.tipo === "desligado") { setWsState("a religar"); return; }
    if (ev.tipo === "split_executado" || (ev.tipo === "pagamento_iniciado" && ev.status === "succeeded")) {
      const v = Number(ev.valor_plataforma || 0);
      setStats((s) => ({ ...s, receita: s.receita + v, comissoes: s.comissoes + v * 0.10 }));
      pushAudit("REDENÇÃO", `${ev.cupom} · ${ev.parceiro}${ev.origem === "qr" ? " · pago por QR" : ""} · ${ev.influencer || ""}`, v);
      triggerFlash("receita"); triggerFlash("comissoes");
      setClicksKey((k) => k + 1);
    } else if (ev.tipo === "clique_cupao") {
      setClicksKey((k) => k + 1);
    } else if (ev.tipo === "indicacao_criada") {
      setStats((s) => ({ ...s, parceiros: s.parceiros + 1 }));
      pushAudit("INDICAÇÃO", `${ev.nome} · ${ev.categoria} · ${ev.cidade} · por ${ev.por}`);
      triggerFlash("parceiros");
    } else if (ev.tipo === "cupons_gerados") {
      setStats((s) => ({ ...s, campanhas: s.campanhas + Number(ev.quantidade || 1) }));
      pushAudit("CUPONS", `${ev.quantidade || 1} cupão · ${ev.cupom} · ${ev.campanha}${ev.parceiro ? ` · ${ev.parceiro}` : ""}`);
      triggerFlash("campanhas");
    } else if (ev.tipo === "erro_transferencia") {
      pushAudit("ERRO", ev.detalhe || "Falha na transferência", undefined, { erro: true });
    }
  });

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
        <p className="text-sm text-slate-500 mt-1">Métricas globais do RRclub — receita, comissões e entidades ativas</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-sistema" icon={Euro} label="Receita do Sistema" live={stats.receita} format={(v) => eur(Math.round(v))} flash={flash.receita} trend={data.trend.revenue} period="últimos 30d vs anteriores" />
        <KpiCard id="comissoes-agregadas" icon={HandCoins} label="Comissões Agregadas" live={stats.comissoes} format={(v) => eur(Math.round(v))} flash={flash.comissoes} trend={data.trend.commission} period="últimos 30d vs anteriores" />
        <KpiCard id="influencers-ativos" icon={Users} label="Influencers Ativos" live={stats.influencers} />
        <KpiCard id="parceiros-ativos" icon={Store} label="Parceiros Ativos" live={stats.parceiros} flash={flash.parceiros} />
        <KpiCard id="campanhas-ativas" icon={Megaphone} label="Campanhas Ativas" live={stats.campanhas} flash={flash.campanhas} />
      </div>

      {resets.length > 0 && (
        <div data-testid="admin-reset-requests-card" className="card-soft p-5 border-l-4 border-amber-400">
          <div className="flex items-center gap-2 mb-3">
            <KeyRound className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-semibold text-slate-900">Pedidos de recuperação de acesso</h3>
            <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-amber-500 text-white text-[11px] font-bold flex items-center justify-center">{resets.length}</span>
          </div>
          <p className="text-xs text-slate-500 mb-3">Copie o link e envie-o ao utilizador (WhatsApp/email). Cada link é válido 24h e só pode ser usado uma vez.</p>
          <div className="space-y-2">
            {resets.map((r) => {
              const link = `${window.location.origin}/redefinir-password?token=${r.token}`;
              return (
                <div key={r.id} data-testid={`reset-request-${r.id}`} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-amber-50/50">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{r.nome} <span className="font-normal text-slate-500">· {r.email}</span></p>
                    <p className="text-[11px] text-slate-400">Pedido em {new Date(r.created_at).toLocaleString("pt-PT")}</p>
                  </div>
                  <button data-testid={`copy-reset-link-${r.id}`} onClick={() => { navigator.clipboard?.writeText(link).catch(() => {}); toast.success("Link de recuperação copiado"); }} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold btn-press shrink-0"><Copy className="w-3.5 h-3.5" /> Copiar link</button>
                </div>
              );
            })}
          </div>
        </div>
      )}

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

      <RecentClicks refreshKey={clicksKey} />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div data-testid="admin-feedback-card" className="card-soft p-5">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-semibold text-slate-900">Sugestões de Melhoria</h3>
            {feedback.filter((f) => f.status === "Novo").length > 0 && <span data-testid="feedback-count-badge" className="min-w-[20px] h-5 px-1.5 rounded-full bg-amber-500 text-white text-[11px] font-bold flex items-center justify-center">{feedback.filter((f) => f.status === "Novo").length}</span>}
          </div>
          {feedback.length === 0 ? <p data-testid="feedback-empty" className="text-sm text-slate-400 py-6 text-center">Ainda sem sugestões. Os utilizadores podem enviar via "Sugerir melhoria" na sidebar.</p> : (
            <div className="space-y-3 max-h-[380px] overflow-y-auto">
              {feedback.map((f) => (
                <div key={f.id} data-testid={`feedback-${f.id}`} className="pb-3 border-b border-slate-50 last:border-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <p className="text-xs text-slate-500"><span className="font-semibold text-slate-800">{f.nome}</span> · {f.role} · {f.tipo} · {new Date(f.date).toLocaleDateString("pt-PT")}</p>
                    <select data-testid={`feedback-status-${f.id}`} value={f.status} onChange={async (e) => { await api.post(`/admin/feedback/${f.id}/status`, { status: e.target.value }); load(); }} className="text-[11px] font-semibold rounded-lg border border-slate-200 px-2 py-1 bg-white">
                      {["Novo", "Em análise", "Implementado", "Rejeitado"].map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <p className="text-sm text-slate-700">{f.mensagem}</p>
                  {f.pagina && <p className="text-[11px] text-slate-400">Página: {f.pagina}</p>}
                </div>
              ))}
            </div>
          )}
        </div>

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
            <span data-testid="ws-status" className={`ml-auto inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${wsState === "ao vivo" ? "text-emerald-700 bg-emerald-50" : "text-slate-500 bg-slate-100"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${wsState === "ao vivo" ? "bg-emerald-500 live-dot" : "bg-slate-400"}`} /><Radio className="w-3 h-3" /> {wsState}
            </span>
          </div>
          {audit.length === 0 ? (
            <p data-testid="audit-log-empty" className="text-sm text-slate-400 py-8 text-center">Sem entradas.</p>
          ) : (
            <div className="space-y-3 max-h-[380px] overflow-y-auto">
              {audit.slice(0, AUDIT_LIMIT).map((a) => (
                <div key={a.id} data-testid={`audit-entry-${a.id}`} className={`audit-item flex items-start gap-3 pb-3 border-b border-slate-50 last:border-0 ${a.enter ? "enter" : ""}`}>
                  <span className={`text-[10px] font-bold px-2 py-1 rounded-md shrink-0 ${TAG_STYLE[a.action] || "text-purple-700 bg-purple-50"}`}>{a.action}</span>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm ${a.erro ? "text-red-600" : "text-slate-700"}`}>{a.detail}</p>
                    <p className="text-xs text-slate-400">{new Date(a.date).toLocaleString("pt-PT")} · {a.actor}</p>
                  </div>
                  {a.amount != null && <span className="amt text-sm" data-testid={`audit-amount-${a.id}`}>+{eur(a.amount)}</span>}
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
