import { useCallback, useEffect, useState } from "react";
import { MousePointerClick, Download } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, downloadCsv } from "../lib/api";

const PERIODS = [["today", "Hoje"], ["7", "7 dias"], ["30", "30 dias"]];

export const RecentClicks = ({ refreshKey }) => {
  const [period, setPeriod] = useState("7");
  const [data, setData] = useState(null);
  const load = useCallback(() => api.get(`/admin/clicks?period=${period}`).then((r) => setData(r.data)).catch((e) => toast.error(apiError(e))), [period]);
  useEffect(() => { load(); }, [load, refreshKey]);

  const exportCsv = () => {
    downloadCsv(`cliques-${period}.csv`, "data_hora;origem;influencer;campanha;cupom;status",
      (data?.items || []).map((i) => [i.date, i.origem, i.influencer, i.campanha, i.cupom, i.status].join(";")));
    toast.success("CSV exportado");
  };

  return (
    <div data-testid="recent-clicks-card" className="card-soft p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <MousePointerClick className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-slate-900">Cliques Recentes</h3>
          {data && <span data-testid="clicks-summary" className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{data.total} cliques · {data.converted} converteram</span>}
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-xl bg-slate-100 p-1" data-testid="clicks-period-filter">
            {PERIODS.map(([k, l]) => (
              <button key={k} data-testid={`clicks-period-${k}`} onClick={() => setPeriod(k)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${period === k ? "bg-white text-purple-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>{l}</button>
            ))}
          </div>
          <button data-testid="clicks-export-csv" onClick={exportCsv} disabled={!data?.items?.length} className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 disabled:opacity-50 px-3 py-1.5 rounded-lg btn-press"><Download className="w-3.5 h-3.5" /> Export CSV</button>
        </div>
      </div>
      {!data ? <p className="text-xs text-slate-400 py-6 text-center">A carregar...</p> : data.items.length === 0 ? (
        <p data-testid="clicks-empty" className="text-sm text-slate-400 py-8 text-center">Sem cliques neste período.</p>
      ) : (
        <div className="overflow-auto max-h-[420px] -mx-5 px-5">
          <table className="w-full text-sm" data-testid="clicks-table">
            <thead className="sticky top-0 bg-white">
              <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                <th className="pb-3 pr-4 font-semibold">Data/hora</th><th className="pb-3 pr-4 font-semibold">Origem</th><th className="pb-3 pr-4 font-semibold">Influencer</th><th className="pb-3 pr-4 font-semibold">Campanha</th><th className="pb-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((i) => (
                <tr key={i.id} data-testid={`click-row-${i.id}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40">
                  <td className="py-2.5 pr-4 text-slate-600 whitespace-nowrap">{new Date(i.date).toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</td>
                  <td className="py-2.5 pr-4 text-slate-700">{i.origem}</td>
                  <td className="py-2.5 pr-4 text-slate-700">{i.influencer}</td>
                  <td className="py-2.5 pr-4"><span className="text-slate-900 font-medium">{i.campanha}</span> <span className="font-coupon text-[10px] text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">{i.cupom}</span></td>
                  <td className="py-2.5"><span data-testid={`click-status-${i.id}`} className={`text-xs font-medium px-2.5 py-1 rounded-full ${i.status === "Converteu" ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500"}`}>{i.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
