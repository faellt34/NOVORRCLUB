import { useState } from "react";
import { Download, Euro, Ticket, HandCoins, CheckCircle2, Clock } from "lucide-react";
import { toast } from "sonner";
import { KpiCard } from "../components/KpiCard";
import { STATEMENT_MONTHS, eur, num } from "../lib/mockData";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

export default function Statement() {
  const [monthId, setMonthId] = useState(STATEMENT_MONTHS[0].id);
  const month = STATEMENT_MONTHS.find((m) => m.id === monthId);

  const totals = month.lines.reduce(
    (acc, l) => ({ uses: acc.uses + l.uses, revenue: acc.revenue + l.revenue, commission: acc.commission + l.revenue * l.rate }),
    { uses: 0, revenue: 0, commission: 0 }
  );

  const exportCsv = () => {
    const header = "campanha;parceiro;utilizacoes;receita_eur;taxa;comissao_eur";
    const rows = month.lines.map((l) => [l.campaign, l.partner, l.uses, l.revenue.toFixed(2), l.rate, (l.revenue * l.rate).toFixed(2)].join(";"));
    const blob = new Blob([header + "\n" + rows.join("\n") + `\nTOTAL;;${totals.uses};${totals.revenue.toFixed(2)};;${totals.commission.toFixed(2)}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `extrato-robson-${month.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Extrato de ${month.label} exportado`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h1 data-testid="statement-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Extrato Mensal</h1>
          <p className="text-sm text-slate-500 mt-1">Comissões consolidadas por mês — taxa travada por redenção, pronto para payout offline</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={monthId} onValueChange={setMonthId}>
            <SelectTrigger data-testid="statement-month-selector" className="w-[160px] bg-white rounded-xl"><SelectValue /></SelectTrigger>
            <SelectContent>
              {STATEMENT_MONTHS.map((m) => <SelectItem key={m.id} value={m.id}>{m.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <button data-testid="statement-export-button" onClick={exportCsv} className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press">
            <Download className="w-4 h-4" /> Exportar CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard id="extrato-comissao" icon={HandCoins} label={`Comissão · ${month.label}`} value={eur(+totals.commission.toFixed(2))} />
        <KpiCard id="extrato-receita" icon={Euro} label="Receita Gerada" value={eur(totals.revenue)} />
        <KpiCard id="extrato-redencoes" icon={Ticket} label="Redenções" value={num(totals.uses)} />
      </div>

      <div data-testid="statement-card" className="card-soft p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Detalhe por Campanha — {month.label}</h3>
          {month.status === "Pago" ? (
            <span data-testid="statement-status-pago" className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" /> Pago em {new Date(month.paidAt).toLocaleDateString("pt-PT")}
            </span>
          ) : (
            <span data-testid="statement-status-pendente" className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-600 bg-amber-50 px-3 py-1.5 rounded-full">
              <Clock className="w-3.5 h-3.5" /> Pendente · payout offline
            </span>
          )}
        </div>
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm" data-testid="statement-table">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                <th className="pb-3 pr-4 font-semibold">Campanha / Parceiro</th>
                <th className="pb-3 pr-4 font-semibold">Utilizações</th>
                <th className="pb-3 pr-4 font-semibold">Receita</th>
                <th className="pb-3 pr-4 font-semibold">Taxa Travada</th>
                <th className="pb-3 font-semibold text-right">Comissão</th>
              </tr>
            </thead>
            <tbody>
              {month.lines.map((l, i) => (
                <tr key={i} data-testid={`statement-line-${i}`} className="border-b border-slate-50 hover:bg-purple-50/40 transition-colors">
                  <td className="py-3 pr-4">
                    <p className="font-semibold text-slate-900">{l.campaign}</p>
                    <p className="text-xs text-slate-500">{l.partner}</p>
                  </td>
                  <td className="py-3 pr-4 text-slate-700">{num(l.uses)}</td>
                  <td className="py-3 pr-4 text-slate-700">{eur(l.revenue)}</td>
                  <td className="py-3 pr-4"><span className="text-xs font-semibold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{(l.rate * 100).toFixed(0)}%</span></td>
                  <td className="py-3 text-right font-bold text-slate-900">{eur(+(l.revenue * l.rate).toFixed(2))}</td>
                </tr>
              ))}
              <tr className="bg-slate-50/70">
                <td className="py-3 pr-4 font-bold text-slate-900">Total</td>
                <td className="py-3 pr-4 font-bold text-slate-900">{num(totals.uses)}</td>
                <td className="py-3 pr-4 font-bold text-slate-900">{eur(totals.revenue)}</td>
                <td className="py-3 pr-4" />
                <td data-testid="statement-total-commission" className="py-3 text-right font-extrabold text-purple-700">{eur(+totals.commission.toFixed(2))}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-slate-400 mt-4">A taxa de comissão é travada historicamente em cada redenção — alterações futuras na campanha não afetam extratos passados.</p>
      </div>
    </div>
  );
}
