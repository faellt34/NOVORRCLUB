import React, { useMemo } from "react";
import { Activity, ArrowDownToLine, BarChart3, CheckCheck, CircleDollarSign, MousePointerClick, QrCode, Smartphone, Users } from "lucide-react";

const csvCell = (s) => '"' + String(s ?? "").replace(/"/g, '""').replace(/^[=+@-]/, "'$&") + '"';

export default function PreviewInsights({ events, country = "PT" }) {
  const metrics = useMemo(() => {
    const shares = events.filter(e => e.role === "influencer" && e.label.includes("divulgada")).length;
    const scans = events.filter(e => e.role === "partner" && e.status === "Validado").length;
    const checkouts = events.filter(e => e.status === "Checkout simulado").length;
    const campaignCount = 1;
    return { shares, scans, checkouts, campaignCount, pending: Math.max(0, scans - checkouts) };
  }, [events]);
  const numbers = [
    { label: "Campanhas demo", value: metrics.campaignCount, Icon: BarChart3 },
    { label: "Divulgações", value: metrics.shares, Icon: MousePointerClick },
    { label: "QR validados", value: metrics.scans, Icon: QrCode },
    { label: "Checkout simulado", value: metrics.checkouts, Icon: Smartphone },
    { label: "Aguardam checkout", value: metrics.pending, Icon: Activity },
  ];
  const ratio = metrics.scans > 0 ? Math.min(100, Math.round(metrics.checkouts / metrics.scans * 100)) : 0;

  const exportCsv = () => {
    // Gerado somente a partir dos eventos locais e fictícios, sem comunicar com servidores.
    const rows = [["ID", "Perfil", "Descrição", "Estado", "Mercado"], ...events.map(e => [e.id,e.role,e.label,e.status,country])]
      .map(row => row.map(csvCell).join(";"));
    const blob = new Blob(["\uFEFF" + rows.join("\r\n")], { type:"text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rrclub-preview-eventos-demo.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return <section className="rounded-2xl border border-[#DCE6EE] bg-white p-4 sm:p-6 shadow-sm" aria-label="Indicadores de operação fictícia">
    <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
      <div><p className="text-[11px] font-bold uppercase tracking-widest text-[#477FAE]">Operação simulada · {country}</p>
      <h2 className="font-extrabold text-xl text-[#203047] mt-1">Visão operacional</h2>
      <p className="text-xs text-slate-500 mt-1">Estatísticas apenas desta sessão, não dados reais.</p></div>
      <button type="button" onClick={exportCsv} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-[#203047] hover:bg-slate-50">
        <ArrowDownToLine size={17}/> Exportar eventos CSV
      </button>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
      {numbers.map(({label,value,Icon}) => <div key={label} className="rounded-xl bg-[#F4F7FB] p-3 sm:p-4 min-h-[104px]">
        <Icon size={18} className="text-[#477FAE] mb-2" aria-hidden="true"/>
        <div className="text-2xl font-extrabold tabular-nums text-[#203047]">{value}</div>
        <div className="text-[11px] leading-snug text-slate-600 mt-1">{label}</div>
      </div>)}
    </div>
    <div className="mt-5 pt-4 border-t border-slate-100">
      <div className="flex justify-between text-xs font-semibold text-slate-600 mb-2"><span>QR validados → checkout simulado</span><span>{ratio}%</span></div>
      <div role="progressbar" aria-valuenow={ratio} aria-valuemin={0} aria-valuemax={100} aria-label="Conversão simulada" className="h-2.5 bg-[#E8EFF6] rounded-full overflow-hidden">
        <div style={{width: ratio + "%"}} className="h-full rounded-full bg-[#477FAE] transition-all duration-300"/>
      </div>
      <p className="text-[11px] text-slate-500 mt-2">Uma validação fictícia pode produzir apenas um checkout fictício. Sem dinheiro, conta Stripe, nem receções reais.</p>
    </div>
  </section>;
}
