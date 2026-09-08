import { Euro, HandCoins, Users, Store, Megaphone, ScrollText } from "lucide-react";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { CAMPAIGNS, eur } from "../lib/mockData";

export default function AdminDashboard() {
  const { auditLog } = useApp();

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="admin-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Visão Geral da Plataforma</h1>
        <p className="text-sm text-slate-500 mt-1">Métricas globais do Robson Club — receita, comissões e entidades ativas</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-sistema" icon={Euro} label="Receita do Sistema" value={eur(129000)} trend="+21,3%" />
        <KpiCard id="comissoes-agregadas" icon={HandCoins} label="Comissões Agregadas" value={eur(12900)} trend="+21,3%" />
        <KpiCard id="influencers-ativos" icon={Users} label="Influencers Ativos" value="24" trend="+4,2%" />
        <KpiCard id="parceiros-ativos" icon={Store} label="Parceiros Ativos" value="18" trend="+12,5%" />
        <KpiCard id="campanhas-ativas" icon={Megaphone} label="Campanhas Ativas" value="31" trend="+8,0%" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div data-testid="admin-campaigns-card" className="card-soft p-5">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Campanhas Recentes</h3>
          <div className="space-y-3">
            {CAMPAIGNS.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-3 pb-3 border-b border-slate-50 last:border-0">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{c.name}</p>
                  <p className="text-xs text-slate-500">{c.partner} · {c.city} · comissão {(c.commissionRate * 100).toFixed(0)}%</p>
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
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">somente leitura</span>
          </div>
          {auditLog.length === 0 ? (
            <p data-testid="audit-log-empty" className="text-sm text-slate-400 py-8 text-center">
              Sem entradas nesta sessão. Valide um cupom como Parceiro para gerar registos imutáveis.
            </p>
          ) : (
            <div className="space-y-3 max-h-[340px] overflow-y-auto">
              {auditLog.map((a) => (
                <div key={a.id} data-testid={`audit-entry-${a.id}`} className="flex items-start gap-3 pb-3 border-b border-slate-50 last:border-0">
                  <span className="text-[10px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md shrink-0">{a.action}</span>
                  <div className="min-w-0">
                    <p className="text-sm text-slate-700">{a.detail}</p>
                    <p className="text-xs text-slate-400">{new Date(a.date).toLocaleString("pt-PT")}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
