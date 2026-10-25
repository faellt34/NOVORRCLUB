import { useEffect, useState } from "react";
import { ArrowUpRight, Lightbulb, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";

function money(value, currency) {
  if (typeof value !== "number") return "Não comprovado";
  return new Intl.NumberFormat(currency === "brl" ? "pt-BR" : "pt-PT", {
    style: "currency", currency: currency.toUpperCase(),
  }).format(value);
}

export function ParceiroCopiloto() {
  const [result, setResult] = useState(null);
  const [state, setState] = useState("loading");
  const load = () => {
    setState("loading");
    api.get("/partner/insights-p5", { timeout: 20000 })
      .then(({ data }) => { setResult(data); setState("ready"); })
      .catch(() => { setResult(null); setState("error"); });
  };
  useEffect(() => { load(); }, []);

  const v = result?.valores || {};
  const currency = result?.currency || "eur";
  return (
    <section data-testid="partner-copiloto" className="card-soft p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-purple-600" /> Copiloto de crescimento
          </h2>
          <p className="text-xs text-slate-500 mt-1">Como usar a RRClub para atrair clientes e acompanhar pagamentos reais.</p>
        </div>
        <button type="button" title="Atualizar análise" onClick={load} disabled={state === "loading"}
          className="rounded-xl p-2 bg-purple-50 text-purple-700 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${state === "loading" ? "animate-spin" : ""}`} />
        </button>
      </div>
      {state === "loading" && !result && <p className="text-sm text-slate-500">A verificar os pagamentos P5...</p>}
      {state === "error" && <p role="status" className="text-sm text-amber-700">Não foi possível verificar os dados neste momento. Não apresentamos valores estimados.</p>}
      {result && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {[
              ["Pagamentos P5", result.pagamentos_p5],
              ["Compras cobradas", money(v.cobrado, currency)],
              ["Parcela do parceiro", money(v.parceiro, currency)],
              ["Ticket médio cobrado", money(result.ticket_medio_cobrado, currency)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-emerald-50/50 border border-emerald-100 p-3">
                <p className="text-[10px] text-slate-600 uppercase tracking-wider">{label}</p>
                <p className="text-lg font-bold text-slate-900 mt-1">{value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-slate-600">
            <span>Cliques registados: <b>{result.cliques_registados}</b></span>
            <span>Scans P5: <b>{result.scans_p5}</b></span>
            <span>Repasses Connect a conciliar: <b>{result.transferencias_pendentes}</b></span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex gap-2 items-center">
              <ShieldCheck className="w-4 h-4 text-emerald-600" /> Recomendações com base nos registos
            </h3>
            {result.sugestoes.length === 0 && <p className="text-xs text-slate-500">A aguardar histórico suficiente para recomendar ações específicas.</p>}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
              {result.sugestoes.map((item, i) => (
                <div key={i} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-sm font-semibold text-purple-800 flex gap-1"><ArrowUpRight className="w-4 h-4 shrink-0" />{item.titulo}</p>
                  <p className="text-xs text-slate-600 mt-1">{item.motivo}</p>
                  <p className="text-xs text-slate-800 mt-2">{item.passo}</p>
                </div>
              ))}
            </div>
          </div>
          <p className="text-[11px] text-slate-500 border-t border-slate-100 pt-3">
            Fonte: {result.fonte}. Valores em {currency.toUpperCase()}, últimos {result.periodo_dias} dias. Não representam lucro líquido nem comprovam depósito no banco.
          </p>
        </>
      )}
    </section>
  );
}
