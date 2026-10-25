import { useEffect, useState } from "react";
import { BarChart3, BrainCircuit, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";

const fmtMoney = (value, currency) =>
  typeof value === "number"
    ? new Intl.NumberFormat(currency === "brl" ? "pt-BR" : "pt-PT", {
        style: "currency", currency: currency.toUpperCase(),
      }).format(value)
    : "Não comprovado";

export function DiretorEstrategia({ onAsk, refreshKey }) {
  const [data, setData] = useState(null);
  const [currency, setCurrency] = useState("brl");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.get("/diretor/estrategia", { timeout: 20000 })
      .then(({ data: result }) => { if (!cancelled) { setData(result); setError(false); } })
      .catch(() => { if (!cancelled) { setError(true); setData(null); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [refreshKey]);

  const item = data?.financeiro_por_pais?.[currency];
  const f = item?.financeiro || {};
  const steps = item?.funil_observado || {};

  return (
    <section className="card-soft p-5 space-y-4" data-testid="diretor-estrategia">
      <div className="flex flex-wrap justify-between items-start gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 flex gap-2 items-center">
            <BrainCircuit className="w-5 h-5 text-purple-600" /> Diretor Executivo · Situação do negócio
          </h3>
          <p className="text-xs text-slate-500 mt-1">Consulta sem consumo de créditos IA. Só pagamentos P5 registados como pagos por webhook local.</p>
        </div>
        <div className="flex gap-2 items-center">
          {[
            ["brl", "Brasil · BRL"],
            ["eur", "Portugal · EUR"],
          ].map(([key, name]) => (
            <button key={key} data-testid={`diretor-moeda-${key}`} type="button" onClick={() => setCurrency(key)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold ${currency === key ? "bg-purple-600 text-white" : "bg-slate-100 text-slate-600"}`}>
              {name}
            </button>
          ))}
          {loading && <RefreshCw className="w-4 h-4 animate-spin text-purple-500" />}
        </div>
      </div>
      {error && <p className="text-sm text-amber-700">Não foi possível verificar os dados locais. Nenhum resultado foi estimado.</p>}
      {item && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
            {[
              ["Vendas P5 pagas", item.vendas_p5_pagas],
              ["Total cobrado", fmtMoney(f.cobrado, currency)],
              ["Parceiro (devido)", fmtMoney(f.parceiro, currency)],
              ["Influenciador (devido)", fmtMoney(f.influenciador, currency)],
              ["RRClub (bruto)", fmtMoney(f.rrclub, currency)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-slate-50 border border-slate-100 p-3">
                <p className="text-[10px] uppercase text-slate-500">{label}</p>
                <p className="text-base font-bold text-slate-900 mt-1">{value}</p>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-purple-100 bg-purple-50/50 p-3">
            <h4 className="text-xs font-semibold text-purple-800 flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Funil P5 — eventos observados</h4>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-2 text-center">
              {[
                ["Cupom aberto", steps.aberturas_cupom],
                ["Sessões", steps.sessoes_p5],
                ["Scans", steps.scans_p5],
                ["Checkout", steps.checkouts_p5],
                ["Pagamento", steps.pagamentos_p5],
                ["Connect", steps.repasses_connect],
              ].map(([label, n]) => <div key={label}><p className="text-lg font-bold text-slate-900">{n ?? "—"}</p><p className="text-[10px] text-slate-500">{label}</p></div>)}
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-[11px] text-slate-600">
            <span>Repasses pendentes: <b>{item.pagos_com_repasses_pendentes}</b></span>
            <span>Pagamentos antigos fora do P5: <b>{item.pagamentos_legados_ou_nao_p5}</b></span>
            <span>Crédito em conta bancária: <b>não comprovado</b></span>
            <span>Tarifas Stripe / IVA: <b>não estimados</b></span>
          </div>
        </>
      )}
      {data && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 border-t border-slate-100 pt-4">
          <div>
            <h4 className="text-sm font-semibold text-slate-900 mb-2 flex gap-2 items-center"><ShieldCheck className="w-4 h-4 text-emerald-600" /> Decisões prioritárias</h4>
            <div className="space-y-2">
              {data.decisoes_prioritarias.map((p, idx) => (
                <div key={idx} className="rounded-xl border border-slate-100 bg-white p-3">
                  <p className="text-xs font-semibold text-slate-900">{p.titulo}</p>
                  <p className="text-[11px] text-slate-600 mt-1">{p.evidencia}</p>
                  <button type="button" className="text-xs font-semibold text-purple-700 mt-2"
                    onClick={() => onAsk(`Analisa esta prioridade com evidências. ${p.titulo}. ${p.acao}. Não executa ações sem autorização.`)}>
                    Pedir plano ao Diretor
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-900 mb-2">Equipa de especialidades</h4>
            <div className="flex flex-wrap gap-1.5">
              {data.equipa.map((p) => (
                <span key={p.id} title={p.funcao} className="rounded-full px-2.5 py-1.5 border border-purple-100 bg-purple-50 text-purple-800 text-[11px]">
                  {p.nome}
                </span>
              ))}
            </div>
            <p className="text-[11px] text-slate-500 mt-3">Leituras financeira e operacional automáticas; análises de marketing, pesquisa externa e engenharia requerem pedido e verificação de fontes. Nenhum especialista movimenta dinheiro.</p>
          </div>
        </div>
      )}
      {data && <p className="text-[10px] text-slate-400">Atualizado em {new Date(data.gerado_em).toLocaleString("pt-PT")} · fonte: base local RRClub. EUR e BRL nunca são somados.</p>}
    </section>
  );
}
