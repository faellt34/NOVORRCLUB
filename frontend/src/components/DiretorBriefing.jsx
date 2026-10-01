import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Info, RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "../lib/api";

const ICON = { error: ShieldAlert, warn: AlertTriangle, info: Info };
const TONE = { error: "border-red-200 bg-red-50 text-red-800", warn: "border-amber-200 bg-amber-50 text-amber-800", info: "border-sky-200 bg-sky-50 text-sky-800" };

export const DiretorBriefing = ({ onAsk, refreshKey }) => {
  const [b, setB] = useState(null);
  const [loading, setLoading] = useState(false);
  const load = () => { setLoading(true); api.get("/diretor/briefing").then((r) => setB(r.data)).catch(() => setB(null)).finally(() => setLoading(false)); };
  useEffect(load, [refreshKey]);
  if (!b) return null;
  const s = b.saude, f = b.funil_30d;
  return (
    <div className="card-soft p-5" data-testid="diretor-briefing">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">Briefing proativo</h3>
        <span data-testid="briefing-alert-count" className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${b.alertas.length ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-700"}`}>{b.alertas.length ? `${b.alertas.length} alerta(s)` : "tudo normal"}</span>
        <button data-testid="briefing-refresh" onClick={load} disabled={loading} className="ml-auto p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 btn-press"><RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /></button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        {[["Pedidos 24h", s.pedidos_api], ["Erros 500", s.erros_500, s.erros_500 > 0], ["Lentos >1,5s", s.pedidos_lentos_1500ms], ["Cliques→QR→Vendas 30d", `${f.cliques}→${f.qr_baixados}→${f.vendas}`]].map(([l, v, bad]) => (
          <div key={l} data-testid={`briefing-kpi-${l}`} className={`rounded-xl border p-2.5 ${bad ? "border-red-200 bg-red-50" : "border-slate-100 bg-slate-50"}`}>
            <p className="text-[10px] uppercase tracking-wider text-slate-400">{l}</p><p className={`text-base font-bold ${bad ? "text-red-700" : "text-slate-900"}`}>{v}</p>
          </div>
        ))}
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {b.alertas.length === 0 && <p data-testid="briefing-empty" className="text-sm text-slate-400 py-3 text-center">Sem anomalias detetadas. O Diretor continua a vigiar logs, Stripe e campanhas.</p>}
        {b.alertas.map((a, i) => { const I = ICON[a.nivel] || Info; return (
          <div key={i} data-testid={`briefing-alerta-${i}`} className={`rounded-xl border p-2.5 flex gap-2 ${TONE[a.nivel]}`}>
            <I className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1"><p className="text-sm font-semibold leading-tight">{a.titulo}</p>{a.detalhe && <p className="text-xs opacity-80 mt-0.5 truncate">{a.detalhe}</p>}</div>
            {a.acao && <button data-testid={`briefing-acao-${i}`} onClick={() => onAsk(a.acao)} className="self-center text-[11px] font-semibold px-2 py-1 rounded-lg bg-white/70 hover:bg-white btn-press whitespace-nowrap">Investigar</button>}
          </div>); })}
      </div>
    </div>
  );
};
