import { useCallback, useEffect, useState } from "react";
import { Euro, Ticket, BadgePercent, HandCoins, Receipt, ScanLine, Download, CheckCircle2, Landmark } from "lucide-react";
import { toast } from "sonner";
import { KpiCard } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { api, apiError, eur, num, downloadCsv } from "../lib/api";
import { Input } from "../components/ui/input";
import { PageSkeleton } from "../components/PageSkeleton";
import { QrScannerDialog } from "../components/QrScannerDialog";

const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

export default function PartnerDashboard() {
  const { user, refreshUnread } = useApp();
  const [data, setData] = useState(null);
  const [code, setCode] = useState("");
  const [amount, setAmount] = useState("");
  const [preview, setPreview] = useState(null);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [lastReceipt, setLastReceipt] = useState(null);
  const [idemKey, setIdemKey] = useState(newKey);
  const [submitting, setSubmitting] = useState(false);
  const [iban, setIban] = useState("");
  const [ibanEdit, setIbanEdit] = useState(false);

  const saveIban = async (e) => {
    e.preventDefault();
    try { await api.post("/partner/iban", { iban, titular: user.nome }); toast.success("IBAN guardado — usado para receber os pagamentos online"); setIbanEdit(false); load(); }
    catch (err) { toast.error(apiError(err)); }
  };

  const load = useCallback(() => api.get("/dashboard/partner").then((r) => setData(r.data)).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const c = code.trim().toUpperCase();
    if (c.length < 4) { setPreview(null); return; }
    const t = setTimeout(() => api.get(`/coupons/preview/${encodeURIComponent(c)}`).then((r) => setPreview(r.data)).catch(() => setPreview(null)), 250);
    return () => clearTimeout(t);
  }, [code]);

  const parsedAmount = parseFloat(String(amount).replace(",", ".")) || 0;

  const handleValidate = async (e) => {
    e.preventDefault();
    if (submitting) return;
    if (!code.trim()) { toast.error("Introduza o código do cupom."); return; }
    if (!parsedAmount || parsedAmount <= 0) { toast.error("Informe um valor de compra válido."); return; }
    setSubmitting(true);
    try {
      const { data: res } = await api.post("/redemptions", { code, amount: parsedAmount, idempotency_key: idemKey });
      if (res.duplicate) toast.warning("Pedido repetido — redenção já registada (idempotência server-side).");
      else toast.success(`Venda validada! Comissão de ${eur(res.record.commission)} registada (taxa travada ${(res.record.rate * 100).toFixed(0)}%).`);
      setLastReceipt(res.record);
      setCode(""); setAmount(""); setPreview(null); setIdemKey(newKey());
      load(); refreshUnread();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const onDetected = useCallback((c) => { setCode(c); toast.success(`QR detetado: ${c}`); }, []);

  const exportCsv = () => {
    downloadCsv(`redencoes-${(data.partner?.nome || "parceiro").toLowerCase().replace(/\s+/g, "-")}.csv`, "id;cupom;influencer;valor_eur;desconto_eur;comissao_eur;taxa;data;staff",
      data.redemptions.map((r) => [r.id, r.coupon, r.influencer, r.amount.toFixed(2), r.discount.toFixed(2), r.commission.toFixed(2), r.rate, r.date, r.staff].join(";")));
    toast.success("CSV exportado com sucesso");
  };

  if (!data) return <PageSkeleton />;
  const { totals, trend, leaderboard, redemptions } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="partner-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{user.nome}</h1>
        <p className="text-sm text-slate-500 mt-1">Receita atribuída, redenções e comissões devidas a influencers</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-atribuida" icon={Euro} label="Receita Atribuída" value={eur(Math.round(totals.revenue))} trend={trend.revenue} />
        <KpiCard id="redencoes" icon={Ticket} label="Redenções" value={num(totals.count)} trend={trend.count} />
        <KpiCard id="descontos" icon={BadgePercent} label="Descontos Concedidos" value={eur(Math.round(totals.discounts))} />
        <KpiCard id="comissao-devida" icon={HandCoins} label="Comissão Devida" value={eur(Math.round(totals.commission))} trend={trend.commission} />
        <KpiCard id="ticket-medio" icon={Receipt} label="Ticket Médio" value={eur(+totals.ticket.toFixed(2))} />
      </div>

      <div data-testid="partner-iban-card" className="card-soft p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center"><Landmark className="w-5 h-5" /></span>
          <div>
            <p className="text-sm font-semibold text-slate-900">Conta para receber pagamentos online (QR)</p>
            <p className="text-xs text-slate-500">{data.partner?.iban ? <>IBAN <span className="font-mono" data-testid="partner-iban-value">{data.partner.iban.replace(/(.{4})/g, "$1 ").trim()}</span> · recebido online: <b className="text-emerald-600">{eur(totals.online_paid || 0)}</b></> : "Ainda sem IBAN — adicione para receber as transferências dos pagamentos por MB WAY/cartão."}</p>
          </div>
        </div>
        {ibanEdit ? (
          <form onSubmit={saveIban} className="flex gap-2">
            <Input data-testid="partner-iban-input" value={iban} onChange={(e) => setIban(e.target.value)} placeholder="PT50 0000 0000 0000 0000 0000 0" className="rounded-xl bg-slate-50 font-mono w-[280px]" />
            <button type="submit" data-testid="partner-iban-save" className="px-3 py-2 rounded-xl bg-purple-600 text-white text-xs font-semibold btn-press">Guardar</button>
          </form>
        ) : (
          <button data-testid="partner-iban-edit" onClick={() => { setIban(data.partner?.iban || ""); setIbanEdit(true); }} className="px-3 py-2 rounded-xl bg-white border border-slate-200 hover:bg-purple-50 text-slate-700 text-xs font-semibold btn-press">{data.partner?.iban ? "Alterar IBAN" : "Adicionar IBAN"}</button>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="coupon-validation-card" className="card-soft p-5" id="validar">
          <h3 className="text-lg font-semibold text-slate-900 mb-1">Validação de Cupom</h3>
          <p className="text-xs text-slate-500 mb-4">Escaneie o QR do cliente ou digite o código</p>
          <form onSubmit={handleValidate} className="space-y-3">
            <div className="flex gap-2">
              <Input data-testid="coupon-code-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ex.: ROBSON-LUXE-25" className="font-coupon uppercase rounded-xl bg-slate-50" />
              <button type="button" data-testid="open-scanner-button" onClick={() => setScannerOpen(true)} className="shrink-0 w-10 h-10 rounded-xl bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center btn-press" title="Escanear QR">
                <ScanLine className="w-[18px] h-[18px]" />
              </button>
            </div>
            {code.trim().length >= 4 && (
              <div data-testid="coupon-preview" className={`text-xs px-3 py-2 rounded-lg ${preview?.status === "Ativa" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`}>
                {!preview ? "Cupom não encontrado para este parceiro"
                  : preview.status === "Ativa" ? <>✓ {preview.nome} · {preview.influencer} · {preview.desconto}% desconto · comissão {preview.comissao}%</>
                  : <>Cupom {preview.status.toLowerCase()} — não redimível</>}
              </div>
            )}
            <Input data-testid="purchase-amount-input" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Valor da conta (€)" inputMode="decimal" className="rounded-xl bg-slate-50" />
            {preview?.status === "Ativa" && parsedAmount > 0 && (
              <div data-testid="live-calculation" className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 rounded-lg px-3 py-2">
                  <p className="text-slate-500">Desconto ({preview.desconto}%)</p>
                  <p className="font-bold text-slate-900" data-testid="live-discount-value">{eur(+(parsedAmount * preview.desconto / 100).toFixed(2))}</p>
                </div>
                <div className="bg-purple-50 rounded-lg px-3 py-2">
                  <p className="text-purple-500">Comissão ({preview.comissao}%)</p>
                  <p className="font-bold text-purple-700" data-testid="live-commission-value">{eur(+(parsedAmount * preview.comissao / 100).toFixed(2))}</p>
                </div>
              </div>
            )}
            <button type="submit" disabled={submitting} data-testid="validate-coupon-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press">
              {submitting ? "A validar..." : "Validar Venda"}
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
            {leaderboard.map((inf, i) => (
              <div key={inf.id} data-testid={`leaderboard-row-${inf.id}`} className="flex items-center gap-3">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${i === 0 ? "bg-purple-600 text-white" : "bg-slate-100 text-slate-500"}`}>{i + 1}</span>
                <img src={inf.avatar} alt={inf.nome} className="w-9 h-9 rounded-full object-cover" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{inf.nome}</p>
                  <p className="text-xs text-slate-500">{inf.handle} · {num(inf.redemptions)} redenções</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-slate-900">{eur(Math.round(inf.revenue))}</p>
                  <p className="text-xs text-purple-600 font-medium">{eur(Math.round(inf.commission))} comissão</p>
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

      <QrScannerDialog open={scannerOpen} onOpenChange={setScannerOpen} onDetected={onDetected} />
    </div>
  );
}
