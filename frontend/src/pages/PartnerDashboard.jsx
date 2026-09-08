import { useMemo, useState } from "react";
import { Euro, Ticket, BadgePercent, HandCoins, Receipt, ScanLine, Download, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { KpiCard } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { INFLUENCER_LEADERBOARD, eur, num } from "../lib/mockData";
import { Input } from "../components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

export default function PartnerDashboard() {
  const { redemptions, validateCoupon, previewCoupon } = useApp();
  const [code, setCode] = useState("");
  const [amount, setAmount] = useState("");
  const [scannerOpen, setScannerOpen] = useState(false);
  const [lastReceipt, setLastReceipt] = useState(null);

  const totals = useMemo(() => {
    const revenue = redemptions.reduce((s, r) => s + r.amount, 0);
    const discounts = redemptions.reduce((s, r) => s + r.discount, 0);
    const commission = redemptions.reduce((s, r) => s + r.commission, 0);
    return { revenue, discounts, commission, count: redemptions.length, ticket: revenue / (redemptions.length || 1) };
  }, [redemptions]);

  const preview = previewCoupon(code);
  const parsedAmount = parseFloat(String(amount).replace(",", ".")) || 0;

  const handleValidate = (e) => {
    e.preventDefault();
    const result = validateCoupon(code, amount);
    if (!result.ok) {
      toast.error(result.error);
      return;
    }
    setLastReceipt(result.record);
    toast.success(`Venda validada! Comissão de ${eur(result.record.commission)} registada (taxa travada ${(result.record.rate * 100).toFixed(0)}%).`);
    setCode("");
    setAmount("");
  };

  const simulateScan = () => {
    setScannerOpen(true);
    setTimeout(() => {
      setCode("ROBSON-LUXE-25");
      setScannerOpen(false);
      toast.success("QR detetado: ROBSON-LUXE-25");
    }, 2200);
  };

  const exportCsv = () => {
    const header = "id;cupom;influencer;valor_eur;desconto_eur;comissao_eur;taxa;data;staff";
    const rows = redemptions.map((r) =>
      [r.id, r.coupon, r.influencer, r.amount.toFixed(2), r.discount.toFixed(2), r.commission.toFixed(2), r.rate, r.date, r.staff].join(";")
    );
    const blob = new Blob([header + "\n" + rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "redencoes-tivoli-sky-bar.csv";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("CSV exportado com sucesso");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="partner-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Tivoli Sky Bar Lisboa</h1>
        <p className="text-sm text-slate-500 mt-1">Receita atribuída, redenções e comissões devidas a influencers</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-atribuida" icon={Euro} label="Receita Atribuída" value={eur(Math.round(totals.revenue))} trend="+16,2%" />
        <KpiCard id="redencoes" icon={Ticket} label="Redenções" value={num(totals.count)} trend="+9,5%" />
        <KpiCard id="descontos" icon={BadgePercent} label="Descontos Concedidos" value={eur(Math.round(totals.discounts))} trend="-2,1%" />
        <KpiCard id="comissao-devida" icon={HandCoins} label="Comissão Devida" value={eur(Math.round(totals.commission))} trend="+16,2%" />
        <KpiCard id="ticket-medio" icon={Receipt} label="Ticket Médio" value={eur(+totals.ticket.toFixed(2))} trend="+6,8%" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="coupon-validation-card" className="card-soft p-5" id="validar">
          <h3 className="text-lg font-semibold text-slate-900 mb-1">Validação de Cupom</h3>
          <p className="text-xs text-slate-500 mb-4">Escaneie o QR do cliente ou digite o código</p>
          <form onSubmit={handleValidate} className="space-y-3">
            <div className="flex gap-2">
              <Input data-testid="coupon-code-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ex.: ROBSON-LUXE-25" className="font-coupon uppercase rounded-xl bg-slate-50" />
              <button type="button" data-testid="open-scanner-button" onClick={simulateScan} className="shrink-0 w-10 h-10 rounded-xl bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center btn-press" title="Escanear QR">
                <ScanLine className="w-[18px] h-[18px]" />
              </button>
            </div>
            {preview && (
              <div data-testid="coupon-preview" className={`text-xs px-3 py-2 rounded-lg ${preview.status === "Ativa" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`}>
                {preview.status === "Ativa"
                  ? <>✓ {preview.campaign} · {preview.influencer} · {preview.discountPct}% desconto · comissão {(preview.commissionRate * 100).toFixed(0)}%</>
                  : <>Cupom {preview.status.toLowerCase()} — não redimível</>}
              </div>
            )}
            <Input data-testid="purchase-amount-input" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Valor da conta (€)" inputMode="decimal" className="rounded-xl bg-slate-50" />
            {preview?.status === "Ativa" && parsedAmount > 0 && (
              <div data-testid="live-calculation" className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 rounded-lg px-3 py-2">
                  <p className="text-slate-500">Desconto ({preview.discountPct}%)</p>
                  <p className="font-bold text-slate-900" data-testid="live-discount-value">{eur(+(parsedAmount * preview.discountPct / 100).toFixed(2))}</p>
                </div>
                <div className="bg-purple-50 rounded-lg px-3 py-2">
                  <p className="text-purple-500">Comissão ({(preview.commissionRate * 100).toFixed(0)}%)</p>
                  <p className="font-bold text-purple-700" data-testid="live-commission-value">{eur(+(parsedAmount * preview.commissionRate).toFixed(2))}</p>
                </div>
              </div>
            )}
            <button type="submit" data-testid="validate-coupon-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold btn-press">
              Validar Venda
            </button>
          </form>
          {lastReceipt && (
            <div data-testid="last-receipt" className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-100 flex items-start gap-2 fade-up">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
              <div className="text-xs text-emerald-800">
                <p className="font-semibold">Redenção {lastReceipt.id} registada</p>
                <p>{lastReceipt.coupon} · {eur(lastReceipt.amount)} · comissão {eur(lastReceipt.commission)} (taxa travada {(lastReceipt.rate * 100).toFixed(0)}%)</p>
              </div>
            </div>
          )}
        </div>

        <div data-testid="influencer-leaderboard-card" className="card-soft p-5">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Top Influencers</h3>
          <div className="space-y-4">
            {INFLUENCER_LEADERBOARD.map((inf, i) => (
              <div key={inf.id} data-testid={`leaderboard-row-${inf.id}`} className="flex items-center gap-3">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${i === 0 ? "bg-purple-600 text-white" : "bg-slate-100 text-slate-500"}`}>{i + 1}</span>
                <img src={inf.avatar} alt={inf.name} className="w-9 h-9 rounded-full object-cover" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{inf.name}</p>
                  <p className="text-xs text-slate-500">{inf.handle} · {num(inf.redemptions)} redenções</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-slate-900">{eur(inf.revenue)}</p>
                  <p className="text-xs text-purple-600 font-medium">{eur(inf.commission)} comissão</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div data-testid="redemption-history-card" className="card-soft p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Histórico</h3>
            <button data-testid="export-csv-button" onClick={exportCsv} className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 px-3 py-1.5 rounded-lg btn-press">
              <Download className="w-3.5 h-3.5" /> Exportar CSV
            </button>
          </div>
          <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
            {redemptions.map((r) => (
              <div key={r.id} data-testid={`redemption-${r.id}`} className="flex items-center justify-between gap-2 pb-3 border-b border-slate-50 last:border-0">
                <div className="min-w-0">
                  <p className="font-coupon text-[11px] font-bold text-purple-700 truncate">{r.coupon}</p>
                  <p className="text-xs text-slate-500">{new Date(r.date).toLocaleString("pt-PT", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })} · {r.staff}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-bold text-slate-900">{eur(r.amount)}</p>
                  <p className="text-xs text-emerald-600">+{eur(r.commission)} com.</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Dialog open={scannerOpen} onOpenChange={setScannerOpen}>
        <DialogContent data-testid="scanner-modal" className="max-w-sm">
          <DialogHeader><DialogTitle>A escanear QR Code...</DialogTitle></DialogHeader>
          <div className="relative aspect-square rounded-2xl bg-slate-950 overflow-hidden flex items-center justify-center">
            <div className="w-2/3 aspect-square border-2 border-purple-400/60 rounded-2xl" />
            <div className="scanner-line absolute left-[10%] right-[10%] h-0.5 bg-purple-400 shadow-[0_0_12px_rgba(167,139,250,0.9)]" />
            <p className="absolute bottom-4 text-xs text-slate-400">Câmera simulada · a detetar cupom</p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
