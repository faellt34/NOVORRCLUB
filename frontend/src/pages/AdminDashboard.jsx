import { useCallback, useEffect, useState } from "react";
import { Euro, HandCoins, Users, Store, Megaphone, ScrollText, Inbox, Check, X, KeyRound, Copy, Lightbulb, Radio, Ticket, MousePointerClick, UserX, Percent, Receipt, Target } from "lucide-react";
import { toast } from "sonner";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { api, apiError, eur } from "../lib/api";
import { useRealtime } from "../services/ws";
import { useFlash } from "../services/live";
import { AbandonAnalysis } from "../components/AbandonAnalysis";
import { TestRunDialog } from "../components/TestRunDialog";
import { AiAnalyst } from "../components/AiAnalyst";
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
  const [stats, setStats] = useState({ receita: 0, comissoes: 0, influencers: 0, parceiros: 0, campanhas: 0, usos: 0, cliques: 0 });
  const [origins, setOrigins] = useState([]);
  const [audit, setAudit] = useState([]);
  const [flash, triggerFlash] = useFlash();
  const [wsState, setWsState] = useState("a ligar");
  const [clicksKey, setClicksKey] = useState(0);
  const [testOpen, setTestOpen] = useState(false);
  const [clearAllOpen, setClearAllOpen] = useState(false);
  const [clearWord, setClearWord] = useState("");
  const [resetOpen, setResetOpen] = useState(false);
  const [resetWord, setResetWord] = useState("");
  const resetAll = async () => {
    try { const { data: r } = await api.post("/admin/reset-all", { confirm: resetWord }); toast.success(`Resultados apagados (${Object.values(r.removed).reduce((a, b) => a + b, 0)} registos) — dashboard a zero`); setResetOpen(false); setResetWord(""); load(); }
    catch (e) { toast.error(apiError(e)); }
  };
  const clearAllTests = async () => {
    try { const { data: r } = await api.post("/admin/test-run/clear-all", { confirm: clearWord }); toast.success(`Testes apagados (${Object.values(r.removed).reduce((a, b) => a + b, 0)} registos)`); setClearAllOpen(false); setClearWord(""); load(); }
    catch (e) { toast.error(apiError(e)); }
  };
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
      setStats({ receita: d.data.totals.revenue, comissoes: d.data.totals.commission, influencers: d.data.counts.influencers, parceiros: d.data.counts.partners, campanhas: d.data.counts.campaigns, usos: d.data.funnel.uses, cliques: d.data.funnel.clicks });
      setOrigins(d.data.funnel.origins);
    } catch (e) { toast.error(apiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const pushAudit = (action, detail, amount, extra = {}) =>
    setAudit((prev) => [{ id: `live-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, action, detail, amount, date: new Date().toISOString(), actor: "tempo real", enter: true, ...extra }, ...prev].slice(0, 50));

  const { status: wsStatus, eventos } = useRealtime((ev) => {
    if (ev.tipo === "ligado") { setWsState("ao vivo"); return; }
    if (ev.tipo === "desligado") { setWsState("a religar"); return; }
    if (ev.tipo === "reset_all" || ev.tipo === "teste_limpo") { load(); return; }
    if (ev.tipo === "split_executado" || (ev.tipo === "pagamento_iniciado" && ev.status === "succeeded")) {
      const v = Number(ev.valor_plataforma || 0);
      setStats((s) => ({ ...s, receita: s.receita + v, comissoes: s.comissoes + v * 0.10, usos: s.usos + 1 }));
      pushAudit("REDENÇÃO", `${ev.cupom} · ${ev.parceiro}${ev.origem === "qr" ? " · pago por QR" : ""} · ${ev.influencer || ""}`, v);
      triggerFlash("receita"); triggerFlash("comissoes"); triggerFlash("usos"); triggerFlash("conv"); triggerFlash("ticket");
      setClicksKey((k) => k + 1);
    } else if (ev.tipo === "clique_cupao") {
      setStats((s) => ({ ...s, cliques: s.cliques + 1 }));
      setOrigins((o) => { const i = o.findIndex((x) => x.origem === ev.origem); return i >= 0 ? o.map((x, j) => j === i ? { ...x, clicks: x.clicks + 1 } : x) : [...o, { origem: ev.origem, clicks: 1 }]; });
      triggerFlash("cliques"); triggerFlash("naousou");
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
      if (decision.mode === "approve") toast.success(`Parceiro "${res.partner.nome}" criado automaticamente${res.access_email ? ` · acesso: ${res.access_email}${res.password_emailed ? " (palavra-passe temporária enviada por email)" : ` / palavra-passe temporária: ${res.temp_password}`}` : ""}`);
      else toast.success("Indicação rejeitada e influencer notificado");
      setDecision(null); load(); refreshUnread();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  if (!data) return <PageSkeleton />;
  const pending = leads.filter((l) => l.status === "Novo").length;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 data-testid="admin-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Visão Geral da Plataforma</h1>
          <p className="text-sm text-slate-500 mt-1">Métricas globais do RRclub — receita, comissões e entidades ativas</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button data-testid="new-test-button" onClick={() => setTestOpen(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#5B21B6] to-[#08061A] hover:opacity-90 text-white text-xs font-semibold btn-press">🎬 Novo Teste</button>
          <button data-testid="reset-all-button" onClick={() => setResetOpen(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-red-200 hover:bg-red-50 text-red-600 text-xs font-semibold btn-press">🧨 Apagar TODOS os resultados</button>
          <span data-testid="ws-indicator" data-status={wsStatus} className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border ${wsStatus === "conectado" ? "text-emerald-700 bg-emerald-50 border-emerald-100" : wsStatus === "reconectando" ? "text-amber-700 bg-amber-50 border-amber-100" : "text-red-600 bg-red-50 border-red-100"}`}>
            <span className={`w-2 h-2 rounded-full ${wsStatus === "conectado" ? "bg-emerald-500 live-dot" : wsStatus === "reconectando" ? "bg-amber-500 live-dot" : "bg-red-500"}`} />
            WS · {wsStatus === "conectado" ? "Conectado" : wsStatus === "reconectando" ? "Reconectando" : "Offline"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-sistema" icon={Euro} label="Receita do Sistema" live={stats.receita} format={(v) => eur(Math.round(v))} flash={flash.receita} trend={data.trend.revenue} period="últimos 30d vs anteriores" />
        <KpiCard id="comissoes-agregadas" icon={HandCoins} label="Comissões Agregadas" live={stats.comissoes} format={(v) => eur(Math.round(v))} flash={flash.comissoes} trend={data.trend.commission} period="últimos 30d vs anteriores" />
        <KpiCard id="influencers-ativos" icon={Users} label="Influencers Ativos" live={stats.influencers} />
        <KpiCard id="parceiros-ativos" icon={Store} label="Parceiros Ativos" live={stats.parceiros} flash={flash.parceiros} />
        <KpiCard id="campanhas-ativas" icon={Megaphone} label="Campanhas Ativas" live={stats.campanhas} flash={flash.campanhas} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="cupons-usados" icon={Ticket} label="Pessoas que usaram cupom" live={stats.usos} flash={flash.usos} trend={data.trend.count} period="últimos 30d vs anteriores" />
        <KpiCard id="cliques-total" icon={MousePointerClick} label="Cliques no cupom" live={stats.cliques} flash={flash.cliques} />
        <KpiCard id="nao-utilizaram" icon={UserX} label="Clicaram e não usaram" live={Math.max(stats.cliques - stats.usos, 0)} flash={flash.naousou} />
        <KpiCard id="taxa-conversao" icon={Percent} label="Taxa de Conversão" live={stats.cliques ? stats.usos / stats.cliques * 100 : 0} format={(v) => `${v.toFixed(1).replace(".", ",")}%`} flash={flash.conv} />
        <KpiCard id="ticket-medio" icon={Receipt} label="Ticket Médio" live={stats.usos ? stats.receita / stats.usos : 0} format={(v) => eur(+v.toFixed(2))} flash={flash.ticket} />
      </div>

      {origins.length > 0 && (
        <div data-testid="admin-origins-card" className="card-soft p-5">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-slate-900">Origens dos cliques</h3>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{stats.cliques} cliques</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
            {origins.map((o) => (
              <div key={o.origem} data-testid={`origin-${o.origem.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                <div className="flex items-center justify-between text-xs mb-1"><span className="font-semibold text-slate-700">{o.origem}</span><span className="text-slate-500">{o.clicks} · {stats.cliques ? Math.round(o.clicks / stats.cliques * 100) : 0}%</span></div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden"><div className="h-full rounded-full bg-gradient-to-r from-[#B47BFF] to-[#6E2BFF] transition-all duration-700" style={{ width: `${stats.cliques ? o.clicks / stats.cliques * 100 : 0}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
      )}

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

      <AbandonAnalysis events={eventos} />

      <AiAnalyst refreshKey={clicksKey} />

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
                    ? `"${decision.lead.nome}" será criado automaticamente como parceiro ativo. Se indicar um email, é criada a conta de acesso (palavra-passe temporária gerada e enviada por email).`
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

      <TestRunDialog open={testOpen} onOpenChange={setTestOpen} eventos={eventos} onDone={load} />

      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent data-testid="reset-all-dialog" className="max-w-sm">
          <DialogHeader><DialogTitle>Apagar TODOS os resultados</DialogTitle><DialogDescription>Zera receita, comissões, ticket médio, vendas, cliques, audit log, notificações, indicações e pagamentos QR. Mantém utilizadores, campanhas reais, e-books e definições. Irreversível.</DialogDescription></DialogHeader>
          <Input data-testid="reset-all-input" value={resetWord} onChange={(e) => setResetWord(e.target.value)} placeholder='Escreva "RESET-ALL"' className="rounded-xl bg-slate-50" />
          <button data-testid="reset-all-confirm" disabled={resetWord !== "RESET-ALL"} onClick={resetAll} className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-semibold btn-press">Apagar tudo e zerar dashboard</button>
        </DialogContent>
      </Dialog>

      <button data-testid="clear-all-tests-button" onClick={() => setClearAllOpen(true)} className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-white border border-slate-200 shadow-lg hover:bg-red-50 hover:text-red-600 text-slate-600 text-xs font-semibold btn-press">🗑️ Limpar TODOS os testes</button>
      <Dialog open={clearAllOpen} onOpenChange={setClearAllOpen}>
        <DialogContent data-testid="clear-all-tests-dialog" className="max-w-sm">
          <DialogHeader><DialogTitle>Limpar todos os testes</DialogTitle><DialogDescription>Apaga apenas campanhas, cupões e transações marcadas como teste. Utilizadores e campanhas reais não são tocados.</DialogDescription></DialogHeader>
          <Input data-testid="clear-all-tests-input" value={clearWord} onChange={(e) => setClearWord(e.target.value)} placeholder='Escreva "LIMPAR"' className="rounded-xl bg-slate-50" />
          <button data-testid="clear-all-tests-confirm" disabled={clearWord !== "LIMPAR"} onClick={clearAllTests} className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-semibold btn-press">Apagar dados de teste</button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
