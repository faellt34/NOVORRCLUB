import { useEffect, useState } from "react";
import { Download, Euro, Ticket, HandCoins, CheckCircle2, Clock, FileDown } from "lucide-react";
import { toast } from "sonner";
import { KpiCard } from "../components/KpiCard";
import { api, apiError, eur, num, downloadCsv } from "../lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { PageSkeleton } from "../components/PageSkeleton";

const monthLabel = (id) => {
  const [y, m] = id.split("-");
  const s = new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("pt-PT", { month: "long", year: "numeric" });
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export default function Statement() {
  const [months, setMonths] = useState(null);
  const [monthId, setMonthId] = useState(null);
  const [pdfBusy, setPdfBusy] = useState(false);

  useEffect(() => {
    api.get("/statements").then((r) => { setMonths(r.data); setMonthId(r.data[0]?.id || null); }).catch((e) => toast.error(apiError(e)));
  }, []);

  if (!months) return <PageSkeleton />;
  const month = months.find((m) => m.id === monthId);
  if (!month) return <p className="text-slate-400 py-12 text-center" data-testid="statement-empty">Ainda não há redenções para gerar extratos.</p>;

  const totals = month.lines.reduce((acc, l) => ({ uses: acc.uses + l.uses, revenue: acc.revenue + l.revenue, commission: acc.commission + l.commission }), { uses: 0, revenue: 0, commission: 0 });
  const label = monthLabel(month.id);

  const downloadPdf = async () => {
    setPdfBusy(true);
    try {
      const r = await api.get(`/statements/${month.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = url; a.download = `extrato-robson-club-${month.id}.pdf`; a.click(); URL.revokeObjectURL(url);
      toast.success(`PDF do extrato de ${label} descarregado`);
    } catch (e) { toast.error(apiError(e)); } finally { setPdfBusy(false); }
  };

  const exportCsv = () => {
    downloadCsv(`extrato-${month.id}.csv`, "campanha;parceiro;utilizacoes;receita_eur;taxa;comissao_eur",
      [...month.lines.map((l) => [l.campaign, l.partner, l.uses, l.revenue.toFixed(2), l.rate, l.commission.toFixed(2)].join(";")), `TOTAL;;${totals.uses};${totals.revenue.toFixed(2)};;${totals.commission.toFixed(2)}`]);
    toast.success(`Extrato de ${label} exportado`);
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
            <SelectTrigger data-testid="statement-month-selector" className="w-[180px] bg-white rounded-xl"><SelectValue /></SelectTrigger>
            <SelectContent>{months.map((m) => <SelectItem key={m.id} value={m.id}>{monthLabel(m.id)}</SelectItem>)}</SelectContent>
          </Select>
          <button data-testid="statement-pdf-button" disabled={pdfBusy} onClick={downloadPdf} className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-60 text-white text-xs font-semibold btn-press"><FileDown className="w-4 h-4" /> {pdfBusy ? "A gerar..." : "PDF"}</button>
          <button data-testid="statement-export-button" onClick={exportCsv} className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press"><Download className="w-4 h-4" /> Exportar CSV</button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard id="extrato-comissao" icon={HandCoins} label={`Comissão · ${label}`} value={eur(+totals.commission.toFixed(2))} />
        <KpiCard id="extrato-receita" icon={Euro} label="Receita Gerada" value={eur(Math.round(totals.revenue))} />
        <KpiCard id="extrato-redencoes" icon={Ticket} label="Redenções" value={num(totals.uses)} />
      </div>

      <div data-testid="statement-card" className="card-soft p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Detalhe por Campanha — {label}</h3>
          {month.status === "Pago" ? (
            <span data-testid="statement-status-pago" className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full"><CheckCircle2 className="w-3.5 h-3.5" /> Pago em {new Date(month.paidAt).toLocaleDateString("pt-PT")}</span>
          ) : (
            <span data-testid="statement-status-pendente" className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-600 bg-amber-50 px-3 py-1.5 rounded-full"><Clock className="w-3.5 h-3.5" /> Pendente · payout offline</span>
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
                  <td className="py-3 pr-4"><p className="font-semibold text-slate-900">{l.campaign}</p><p className="text-xs text-slate-500">{l.partner}</p></td>
                  <td className="py-3 pr-4 text-slate-700">{num(l.uses)}</td>
                  <td className="py-3 pr-4 text-slate-700">{eur(l.revenue)}</td>
                  <td className="py-3 pr-4"><span className="text-xs font-semibold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{(l.rate * 100).toFixed(0)}%</span></td>
                  <td className="py-3 text-right font-bold text-slate-900">{eur(l.commission)}</td>
                </tr>
              ))}
              <tr className="bg-slate-50/70">
                <td className="py-3 pr-4 font-bold text-slate-900">Total</td>
                <td className="py-3 pr-4 font-bold text-slate-900">{num(totals.uses)}</td>
                <td className="py-3 pr-4 font-bold text-slate-900">{eur(+totals.revenue.toFixed(2))}</td>
                <td className="py-3 pr-4" />
                <td data-testid="statement-total-commission" className="py-3 text-right font-extrabold text-purple-700">{eur(+totals.commission.toFixed(2))}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-slate-400 mt-4">A taxa de comissão é travada no servidor em cada redenção — alterações futuras na campanha não afetam extratos passados.</p>
      </div>
    </div>
  );
}
