import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, TrendingUp, AlertTriangle, ShieldAlert, Info, ArrowRight } from "lucide-react";
import { api } from "../lib/api";

const ICON = { error: ShieldAlert, warn: AlertTriangle, info: Info, ok: TrendingUp };
const TONE = { error: "bg-red-50 text-red-600", warn: "bg-amber-50 text-amber-600", info: "bg-indigo-50 text-indigo-600", ok: "bg-emerald-50 text-emerald-600" };

export const Recommendations = ({ refreshKey }) => {
  const [b, setB] = useState(null);
  const navigate = useNavigate();
  useEffect(() => { api.get("/diretor/briefing").then((r) => setB(r.data)).catch(() => setB(null)); }, [refreshKey]);
  if (!b) return null;
  const items = b.alertas.slice(0, 4).map((a) => ({ ...a, tipo: a.nivel }));
  if (items.length < 4) b.top_campanhas.slice(0, 4 - items.length).forEach((c) => items.push({ tipo: "ok", titulo: `${c.nome}: € ${c.receita} em ${c.vendas} venda(s)`, detalhe: `Conversão ${c.conversao_pct}% nos últimos 30 dias`, acao: `analisa a campanha ${c.nome} e diz como escalar` }));
  if (!items.length) items.push({ tipo: "ok", titulo: "Sem anomalias detetadas", detalhe: "O Diretor continua a vigiar logs, Stripe e campanhas.", acao: null });
  return (
    <div className="card-soft p-5" data-testid="recommendations-card">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-5 h-5 text-indigo-600" /><h3 className="text-lg font-semibold text-slate-900">Recomendações</h3>
        <span data-testid="recommendations-count" className="ml-auto text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full">{b.alertas.length}</span>
      </div>
      <div className="divide-y divide-slate-100">
        {items.map((it, i) => { const I = ICON[it.tipo] || Info; return (
          <div key={i} data-testid={`recommendation-${i}`} className="py-3 flex gap-3">
            <span className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center ${TONE[it.tipo]}`}><I className="w-4 h-4" /></span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900 leading-tight">{it.titulo}</p>
              {it.detalhe && <p className="text-xs text-slate-500 mt-0.5">{it.detalhe}</p>}
              {it.acao && <button data-testid={`recommendation-action-${i}`} onClick={() => navigate("/admin/diretor", { state: { pergunta: it.acao } })} className="mt-1 text-xs font-semibold text-indigo-600 hover:text-indigo-500 inline-flex items-center gap-1">Ver com o Diretor <ArrowRight className="w-3 h-3" /></button>}
            </div>
          </div>); })}
      </div>
    </div>
  );
};
