import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Crown, Copy, MapPin, CalendarDays, Users, CheckCircle2, XCircle, CreditCard, Smartphone } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { api, apiError, num, eur } from "../lib/api";
import { GlobeCanvas } from "../components/GlobeCanvas";

export default function PublicCoupon() {
  const { code } = useParams();
  const [c, setC] = useState(undefined);
  const [err, setErr] = useState("");
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const [amount, setAmount] = useState("");
  const [paying, setPaying] = useState(false);
  const [paid, setPaid] = useState(null);
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (!sessionId) return;
    let n = 0;
    const tick = async () => {
      try { const { data } = await api.get(`/payments/status/${sessionId}`); if (data.payment_status === "paid") { setPaid(data); return; } if (["failed", "expired"].includes(data.payment_status)) { setPaid({ failed: true }); return; } } catch {}
      if (++n < 10) setTimeout(tick, 2000); else setPaid({ pending: true });
    };
    tick();
  }, [sessionId]);

  const pay = async () => {
    const v = parseFloat(String(amount).replace(",", "."));
    if (!v || v < 1) { toast.error("Indique o valor da conta"); return; }
    setPaying(true);
    try { const { data } = await api.post("/public/pay", { code, amount: v, origin_url: window.location.origin, email: email || null }); window.location.href = data.checkout_url; }
    catch (e) { toast.error(apiError(e)); setPaying(false); }
  };
  const parsed = parseFloat(String(amount).replace(",", ".")) || 0;

  useEffect(() => {
    api.get(`/public/coupon/${encodeURIComponent(code)}`).then((r) => setC(r.data)).catch((e) => { setErr(apiError(e)); setC(null); });
  }, [code]);

  const copy = () => { navigator.clipboard?.writeText(c.cupom).catch(() => {}); toast.success("Código copiado — mostre-o no local"); };
  const active = c?.status === "Ativa";

  return (
    <div className="min-h-screen bg-[#0C0A14] text-white flex flex-col relative overflow-hidden"><div className="absolute inset-0 opacity-30"><GlobeCanvas color="167,139,250" /></div>
      <div className="px-6 pt-6 flex items-center justify-between relative">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-5 h-5" /></div>
          <div><p className="font-display font-bold leading-tight">ןןClub</p><p className="text-[10px] uppercase tracking-widest text-purple-400/80">Luxury Experiences</p></div>
        </div>
        <Link to="/login" data-testid="coupon-login-link" className="text-xs text-slate-400 hover:text-white">Área de membros</Link>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 relative">
        {c === undefined && <p className="text-slate-400 text-sm" data-testid="coupon-loading">A carregar cupom...</p>}
        {c === null && (
          <div className="text-center" data-testid="coupon-not-found">
            <XCircle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-lg font-semibold">Cupom não encontrado</p>
            <p className="text-sm text-slate-400">{err}</p>
          </div>
        )}
        {c && (
          <div className="w-full max-w-md fade-up">
            <div className="rounded-3xl bg-white text-slate-900 overflow-hidden shadow-2xl shadow-purple-900/40" data-testid="public-coupon-card">
              <div className="p-6 bg-gradient-to-br from-purple-600 to-purple-800 text-white">
                <div className="flex items-center gap-3 mb-4">
                  {c.influencer_avatar && <img src={c.influencer_avatar} alt="" className="w-11 h-11 rounded-full border-2 border-white/40 object-cover" />}
                  <div><p className="text-xs text-purple-200">Oferta exclusiva de</p><p className="font-semibold">{c.influencer} <span className="text-purple-200 font-normal">{c.influencer_handle}</span></p></div>
                </div>
                <p className="font-display text-5xl font-extrabold tracking-tight">{c.desconto}% OFF</p>
                <p className="text-sm text-purple-100 mt-1">{c.campanha}</p>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center gap-3">
                  {c.avatar && <img src={c.avatar} alt="" className="w-12 h-12 rounded-xl object-cover" />}
                  <div><p className="font-bold text-slate-900">{c.parceiro}</p><p className="text-xs text-slate-500 flex items-center gap-1"><MapPin className="w-3 h-3" /> {c.categoria} · {c.cidade}</p></div>
                </div>
                <div className={`rounded-2xl p-4 flex items-center gap-4 ${active ? "bg-purple-50" : "bg-slate-100"}`}>
                  <div className="bg-white p-2 rounded-xl border border-purple-100"><QRCodeSVG value={window.location.href} size={92} fgColor="#3B0764" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">O seu código</p>
                    <p data-testid="public-coupon-code" className="font-coupon font-bold text-lg tracking-wider text-purple-700 break-all">{c.cupom}</p>
                    <button data-testid="public-coupon-copy" onClick={copy} className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 px-3 py-1.5 rounded-lg btn-press"><Copy className="w-3.5 h-3.5" /> Copiar código</button>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="flex items-center gap-1"><CalendarDays className="w-3.5 h-3.5" /> Válido até {new Date(c.validade).toLocaleDateString("pt-PT")}</span>
                  <span data-testid="public-coupon-claims" className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {num(c.claims)} pessoas já receberam</span>
                </div>
                {active && paid?.payment_status === "paid" && (
                  <div data-testid="public-pay-success" className="rounded-2xl bg-emerald-50 border border-emerald-100 p-4 text-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-1" />
                    <p className="text-sm font-bold text-emerald-800">Pagamento confirmado · {eur(paid.amount)}</p>
                    <div data-testid="public-receipt" className="mt-2 text-left text-xs text-emerald-900 bg-white/70 rounded-xl p-3 space-y-0.5">
                      <p className="font-semibold uppercase tracking-wider text-[10px] text-emerald-700">Recibo</p>
                      <p>Conta: <b>{eur(paid.gross_amount)}</b></p>
                      <p>Desconto {c.desconto}%: <b>−{eur(paid.discount)}</b></p>
                      <p>Pago: <b>{eur(paid.amount)}</b> · Ref. {paid.redemption_id || paid.session_id.slice(-8)}</p>
                      {paid.customer_email && <p className="text-emerald-700">{paid.receipt_emailed ? `Recibo enviado para ${paid.customer_email}` : `Recibo disponível neste ecrã (${paid.customer_email})`}</p>}
                    </div>
                    <button data-testid="public-receipt-print" onClick={() => window.print()} className="mt-2 text-xs font-semibold text-emerald-700 underline">Guardar / imprimir recibo</button>
                    <p className="text-xs text-emerald-700 mt-1">Mostre este ecrã ao staff de {c.parceiro}. A redenção já ficou registada.</p>
                  </div>
                )}
                {active && paid?.failed && <p data-testid="public-pay-failed" className="text-xs text-red-600 bg-red-50 rounded-xl px-3 py-2">O pagamento não foi concluído. Pode tentar novamente.</p>}
                {active && sessionId && !paid && <p data-testid="public-pay-polling" className="text-xs text-purple-700 bg-purple-50 rounded-xl px-3 py-2 animate-pulse">A confirmar o pagamento...</p>}
                {active && paid?.payment_status !== "paid" && (
                  <div data-testid="public-pay-card" className="rounded-2xl border border-slate-200 p-4 space-y-2">
                    <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5"><CreditCard className="w-3.5 h-3.5 text-purple-600" /> Pagar já com desconto aplicado</p>
                    <div className="flex gap-2">
                      <input data-testid="public-pay-amount" value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" placeholder="Valor da conta (€)" className="flex-1 h-10 px-3 rounded-xl border border-slate-200 bg-slate-50 text-sm" />
                      <button data-testid="public-pay-button" disabled={paying || parsed < 1} onClick={pay} className="h-10 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold btn-press">{paying ? "A abrir..." : "Pagar"}</button>
                    </div>
                    <input data-testid="public-pay-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email para receber o recibo (opcional)" className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-slate-50 text-sm" />
                    {parsed >= 1 && <p data-testid="public-pay-preview" className="text-xs text-slate-600">Paga <b className="text-purple-700">{eur(+(parsed * (1 - c.desconto / 100)).toFixed(2))}</b> em vez de {eur(parsed)} · poupa {eur(+(parsed * c.desconto / 100).toFixed(2))}</p>}
                    <p className="text-[11px] text-slate-400 flex items-center gap-1"><Smartphone className="w-3 h-3" /> MB WAY · Cartão de débito/crédito · pagamento seguro via Stripe</p>
                  </div>
                )}
                {active
                  ? <p className="text-xs text-emerald-700 bg-emerald-50 rounded-xl px-3 py-2 flex items-center gap-2" data-testid="public-coupon-active"><CheckCircle2 className="w-4 h-4" /> Mostre este QR ou código ao staff de {c.parceiro} para aplicar o desconto.</p>
                  : <p className="text-xs text-red-600 bg-red-50 rounded-xl px-3 py-2" data-testid="public-coupon-inactive">Este cupom está {c.status.toLowerCase()} e não pode ser utilizado.</p>}
              </div>
            </div>
            <p className="text-center text-[11px] text-slate-500 mt-4">Guarde esta página nos favoritos ou faça uma captura de ecrã. <Link to="/privacidade" className="underline">Privacidade</Link></p>
          </div>
        )}
      </div>
    </div>
  );
}
