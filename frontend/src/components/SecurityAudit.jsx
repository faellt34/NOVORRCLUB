import { useEffect, useState } from "react";
import { ShieldCheck, Loader2, Wrench, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

const SEV = { alta: "bg-red-50 text-red-600 border-red-100", media: "bg-amber-50 text-amber-700 border-amber-100", baixa: "bg-slate-100 text-slate-600 border-slate-200" };
const fmt = (d) => new Date(d).toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export const SecurityAudit = ({ onProposed }) => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("");
  useEffect(() => { api.get("/diretor/auditoria").then((r) => setData(r.data?.id ? r.data : null)).catch(() => {}); }, []);

  const run = async () => {
    setBusy(true);
    try { const { data: d } = await api.post("/diretor/auditoria", {}, { timeout: 300000 }); setData(d); toast.success(`Auditoria concluída: ${d.achados.length} achados em ${d.ficheiros.length} ficheiros`); }
    catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const propose = async (f) => {
    try { await api.post(`/diretor/auditoria/${data.id}/propor/${f.id}`); toast.success("Correção colocada em Ações Pendentes"); setData((d) => ({ ...d, achados: d.achados.map((a) => a.id === f.id ? { ...a, acao_id: "x" } : a) })); onProposed?.(); }
    catch (e) { toast.error(apiError(e)); }
  };

  const shown = (data?.achados || []).filter((a) => !filter || a.severidade === filter);
  return (
    <div className="card-soft p-5" data-testid="security-audit-card">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-3">
        <div className="flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">Auditoria de Segurança</h3>
          {data && <span className="text-[10px] text-slate-400">{fmt(data.timestamp)} · {data.ficheiros.length} ficheiros</span>}</div>
        <div className="sm:ml-auto flex items-center gap-2">
          {data && ["alta", "media", "baixa"].map((s) => <button key={s} data-testid={`audit-filter-${s}`} onClick={() => setFilter(filter === s ? "" : s)} className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${SEV[s]} ${filter === s ? "ring-2 ring-purple-400" : ""}`}>{data.resumo[s]} {s}</button>)}
          <button data-testid="audit-run" disabled={busy} onClick={run} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-xs font-semibold btn-press">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : data ? <RefreshCw className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />} {busy ? "A auditar todas as rotas (≈1 min)..." : data ? "Repetir auditoria" : "Auditar todas as rotas"}
          </button>
        </div>
      </div>
      {!data && !busy && <p className="text-sm text-slate-400 py-6 text-center" data-testid="audit-empty">O subagente Backend revê todos os ficheiros de rotas de uma vez e lista os achados aqui.</p>}
      {data && shown.length === 0 && <p className="text-sm text-slate-400 py-6 text-center">Sem achados{filter ? ` de severidade ${filter}` : ""}.</p>}
      <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
        {shown.map((f) => (
          <details key={f.id} data-testid={`audit-finding-${f.id}`} className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
            <summary className="flex items-center gap-2 cursor-pointer list-none">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase ${SEV[f.severidade] || SEV.baixa}`}>{f.severidade}</span>
              <span className="text-sm font-semibold text-slate-900 flex-1 truncate">{f.titulo}</span>
              <span className="text-[11px] font-mono text-slate-400 truncate max-w-[180px]">{f.ficheiro}{f.funcao && f.funcao !== "-" ? ` · ${f.funcao}` : ""}</span>
            </summary>
            <p className="mt-2 text-xs text-slate-600 whitespace-pre-wrap">{f.descricao}</p>
            {f.correcao && <p className="mt-1 text-xs text-slate-800"><b>Correção:</b> {f.correcao}</p>}
            {f.diff && <pre className="mt-2 text-[11px] text-emerald-300 bg-slate-900 rounded-lg p-2 overflow-x-auto max-h-32 whitespace-pre">{f.diff}</pre>}
            <button data-testid={`audit-propose-${f.id}`} disabled={!!f.acao_id} onClick={() => propose(f)} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-purple-700 hover:underline disabled:opacity-50 disabled:no-underline"><Wrench className="w-3 h-3" /> {f.acao_id ? "Correção já proposta" : "Propor correção (ação pendente)"}</button>
          </details>
        ))}
      </div>
    </div>
  );
};
