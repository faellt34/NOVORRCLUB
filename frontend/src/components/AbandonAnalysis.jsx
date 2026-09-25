import { useCallback, useEffect, useMemo, useState } from "react";
import { MousePointerClick, Download, QrCode, CheckCircle2, Clock, X } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, downloadCsv, eur } from "../lib/api";
import { useCountUp, useFlash } from "../services/live";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const PERIODS = [["hoje", "Hoje"], ["7d", "7 dias"], ["30d", "30 dias"]];
const ESTADO = {
  Converteu: { cls: "bg-emerald-50 text-emerald-600", icon: "✅" },
  "QR sem scan": { cls: "bg-violet-50 text-violet-700", icon: "📱" },
  "Sem download": { cls: "bg-cyan-50 text-cyan-700", icon: "📥" },
  Abandonou: { cls: "bg-amber-50 text-amber-700", icon: "⏱️" },
};
const KPIS = [
  { key: "total", label: "Total cliques", icon: MousePointerClick, filter: null, emoji: "👆" },
  { key: "sem_download", label: "Sem download QR", icon: Download, filter: ["Sem download", "Abandonou"], emoji: "📥" },
  { key: "qr_sem_scan", label: "QR sem scan", icon: QrCode, filter: ["QR sem scan"], emoji: "📱" },
  { key: "convertidos", label: "Converteram", icon: CheckCircle2, filter: ["Converteu"], emoji: "✅" },
];
const fmt = (d) => (d ? new Date(d).toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—");
const stateOf = (r) => (r.converted || r.estado === "Converteu" ? "Converteu" : r.qr ? "QR sem scan" : r.estado === "Abandonou" ? "Abandonou" : "Sem download");

const FunnelKpi = ({ k, value, active, flash, onClick }) => {
  const [v, updating] = useCountUp(value);
  return (
    <button data-testid={`funnel-kpi-${k.key}`} onClick={onClick} className={`card-soft p-4 text-left stat transition-colors ${active ? "ring-2 ring-purple-500" : ""} ${flash ? "live-updated" : ""}`}>
      <div className="flex items-center justify-between mb-2"><span className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center"><k.icon className="w-4 h-4" /></span><span className="text-base">{k.emoji}</span></div>
      <p data-testid={`funnel-kpi-${k.key}-value`} className={`stat-val font-display text-2xl font-extrabold tracking-tight text-slate-900 ${updating ? "updating" : ""}`}>{Math.round(v)}</p>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mt-0.5">{k.label}</p>
    </button>
  );
};

export const AbandonAnalysis = ({ events }) => {
  const [period, setPeriod] = useState("7d");
  const [rows, setRows] = useState(null);
  const [filter, setFilter] = useState(null);
  const [detail, setDetail] = useState(null);
  const [flash, triggerFlash] = useFlash();

  const load = useCallback(() => api.get(`/admin/cliques/analysis?period=${period}`).then((r) => setRows(r.data.lista)).catch((e) => toast.error(apiError(e))), [period]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const ev = events[0];
    if (!ev) return;
    if (ev.tipo === "novo_clique" && ev.dados) {
      setRows((r) => r && (r.some((x) => x.id === ev.dados.id) ? r : [{ id: ev.dados.id, date: ev.dados.date, origem: ev.dados.origem, cliente: ev.dados.cliente, influencer: ev.dados.influencer, campanha: ev.dados.campaign, cupom: ev.dados.coupon, qr: false, estado: "Sem download", valor: null, enter: true }, ...r].slice(0, 500)));
      triggerFlash("total"); triggerFlash("sem_download");
    } else if (ev.tipo === "qr_baixado") {
      setRows((r) => r && r.map((x) => x.id === ev.claim_id ? { ...x, qr: true, qr_downloaded_at: ev.at, estado: x.estado === "Converteu" ? x.estado : "QR sem scan", enter: true } : x));
      triggerFlash("qr_sem_scan"); triggerFlash("sem_download");
    } else if (ev.tipo === "venda" && ev.claim_id) {
      setRows((r) => r && r.map((x) => x.id === ev.claim_id ? { ...x, estado: "Converteu", converted_at: ev.at, valor: ev.valor, enter: true } : x));
      triggerFlash("convertidos");
    }
  }, [events]); // eslint-disable-line react-hooks/exhaustive-deps

  const counts = useMemo(() => {
    const list = rows || [];
    const st = list.map(stateOf);
    return { total: list.length, sem_download: st.filter((s) => s === "Sem download" || s === "Abandonou").length, qr_sem_scan: st.filter((s) => s === "QR sem scan").length, convertidos: st.filter((s) => s === "Converteu").length };
  }, [rows]);
  const visible = useMemo(() => (rows || []).filter((r) => !filter || filter.includes(stateOf(r))), [rows, filter]);

  const exportCsv = () => {
    downloadCsv(`cliques-${period}${filter ? "-filtrado" : ""}.csv`, "data_hora;origem;cliente;influencer;campanha;cupom;qr;estado;valor",
      visible.map((r) => [r.date, r.origem, r.cliente, r.influencer, r.campanha, r.cupom, r.qr ? "Sim" : "Não", stateOf(r), r.valor ?? ""].join(";")));
    toast.success(`CSV exportado (${visible.length} linhas)`);
  };

  return (
    <div className="space-y-4" data-testid="abandon-analysis">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Análise de Abandono</h3>
          <p className="text-xs text-slate-500">Do clique ao restaurante — em tempo real</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-xl bg-slate-100 p-1" data-testid="abandon-period-filter">
            {PERIODS.map(([k, l]) => <button key={k} data-testid={`abandon-period-${k}`} onClick={() => setPeriod(k)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${period === k ? "bg-white text-purple-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>{l}</button>)}
          </div>
          <button data-testid="abandon-export-csv" onClick={exportCsv} disabled={!visible.length} className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 disabled:opacity-50 px-3 py-1.5 rounded-lg btn-press"><Download className="w-3.5 h-3.5" /> Export CSV</button>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {KPIS.map((k) => <FunnelKpi key={k.key} k={k} value={counts[k.key]} flash={flash[k.key]} active={filter === k.filter} onClick={() => setFilter(filter === k.filter ? null : k.filter)} />)}
      </div>

      <div data-testid="clicks-individual-card" className="card-soft p-5">
        <div className="flex items-center gap-2 mb-4">
          <h4 className="text-base font-semibold text-slate-900">Cliques Individuais</h4>
          {filter && <button data-testid="abandon-clear-filter" onClick={() => setFilter(null)} className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full">{filter.join(" / ")} <X className="w-3 h-3" /></button>}
          <span className="ml-auto text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{visible.length} linhas</span>
        </div>
        {!rows ? <p className="text-xs text-slate-400 py-6 text-center">A carregar...</p> : visible.length === 0 ? <p data-testid="abandon-empty" className="text-sm text-slate-400 py-8 text-center">Sem cliques neste período.</p> : (
          <div className="overflow-auto max-h-[440px] -mx-5 px-5">
            <table className="w-full text-sm" data-testid="clicks-individual-table">
              <thead className="sticky top-0 bg-white"><tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                {["Data/hora", "Origem", "Cliente", "Influencer", "Campanha", "QR", "Estado"].map((h) => <th key={h} className="pb-3 pr-4 font-semibold">{h}</th>)}<th className="pb-3 font-semibold text-right">Valor</th>
              </tr></thead>
              <tbody>
                {visible.slice(0, 100).map((r) => { const s = stateOf(r); return (
                  <tr key={r.id} data-testid={`abandon-row-${r.id}`} onClick={() => setDetail(r)} className={`audit-item border-b border-slate-50 last:border-0 hover:bg-purple-50/40 cursor-pointer ${r.enter ? "enter" : ""}`}>
                    <td className="py-2.5 pr-4 text-slate-600 whitespace-nowrap">{fmt(r.date)}</td>
                    <td className="py-2.5 pr-4 text-slate-700">{r.origem}</td>
                    <td className="py-2.5 pr-4 text-slate-700">{r.cliente}</td>
                    <td className="py-2.5 pr-4 text-slate-700">{r.influencer}</td>
                    <td className="py-2.5 pr-4"><span className="text-slate-900 font-medium">{r.campanha}</span> <span className="font-coupon text-[10px] text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">{r.cupom}</span></td>
                    <td className="py-2.5 pr-4" data-testid={`abandon-qr-${r.id}`}>{r.qr ? <span className="text-emerald-600 font-semibold">Sim</span> : <span className="text-slate-400">Não</span>}</td>
                    <td className="py-2.5 pr-4"><span data-testid={`abandon-state-${r.id}`} className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${ESTADO[s].cls}`}>{ESTADO[s].icon} {s}</span></td>
                    <td className="py-2.5 text-right">{r.valor != null ? <span className="amt text-sm">{eur(r.valor)}</span> : <span className="text-slate-300">—</span>}</td>
                  </tr>
                ); })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent data-testid="click-timeline-dialog" className="max-w-md">
          {detail && (() => { const s = stateOf(detail); return (
            <>
              <DialogHeader><DialogTitle>Percurso do {detail.cliente}</DialogTitle><DialogDescription>{detail.campanha} · {detail.cupom} · via {detail.influencer}</DialogDescription></DialogHeader>
              <ol className="relative border-l-2 border-purple-100 ml-3 space-y-5 py-1">
                {[
                  { ok: true, icon: MousePointerClick, title: "Cliente clicou", sub: `${fmt(detail.date)} · ${detail.origem}` },
                  { ok: detail.qr, icon: QrCode, title: detail.qr ? "Baixou o QR" : "Não baixou o QR", sub: detail.qr ? fmt(detail.qr_downloaded_at) : "sem download" },
                  { ok: s === "Converteu", icon: s === "Converteu" ? CheckCircle2 : Clock, title: s === "Converteu" ? "Pagou no restaurante" : "Não foi ao restaurante", sub: s === "Converteu" ? `${fmt(detail.converted_at)} · ${eur(detail.valor || 0)}` : s === "Abandonou" ? "abandonou (+48h)" : "ainda não" },
                ].map((st, i) => (
                  <li key={i} className="ml-5 relative" data-testid={`timeline-step-${i}`}>
                    <span className={`absolute -left-[31px] top-0 w-6 h-6 rounded-full flex items-center justify-center ${st.ok ? "bg-purple-600 text-white" : "bg-slate-100 text-slate-400"}`}><st.icon className="w-3 h-3" /></span>
                    <p className={`text-sm font-semibold ${st.ok ? "text-slate-900" : "text-slate-400"}`}>{st.title}</p>
                    <p className="text-xs text-slate-500">{st.sub}</p>
                  </li>
                ))}
              </ol>
            </>
          ); })()}
        </DialogContent>
      </Dialog>
    </div>
  );
};
