import { useEffect, useRef, useState } from "react";
import { StripeModeBanner } from "../components/StripeModeBanner";
import P5FollowerPanel from "../components/P5FollowerPanel";
import { saveQr } from "../lib/saveQr";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Copy, MapPin, CalendarDays, Users, CheckCircle2, XCircle, CreditCard, Smartphone, Download } from "lucide-react";
import { BrandLogo } from "../components/BrandLogo";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { api, apiError, num } from "../lib/api";
import { GlobeCanvas } from "../components/GlobeCanvas";

export default function PublicCoupon() {
  const { code } = useParams();
  const [c, setC] = useState(undefined);
  const [err, setErr] = useState("");
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const [amount, setAmount] = useState("");
  const [paying, setPaying] = useState(false);
  const [p5Enabled, setP5Enabled] = useState(false);
  const [p5CheckoutEnabled, setP5CheckoutEnabled] = useState(false);
  const [paid, setPaid] = useState(null);
  const [email, setEmail] = useState("");
  const [checkVersion, setCheckVersion] = useState(0);
  const payingRef = useRef(false);
  const storageKey = `rrclub_pix_${code.toUpperCase()}`;
  const readAttempt = () => {
    try { return JSON.parse(sessionStorage.getItem(storageKey) || "null"); } catch { return null; }
  };
  const [attempt, setAttempt] = useState(readAttempt);
  const saveAttempt = (value) => {
    setAttempt(value);
    try { value ? sessionStorage.setItem(storageKey, JSON.stringify(value)) : sessionStorage.removeItem(storageKey); } catch {}
  };
  const pixRequestId = params.get("pix_request_id") || attempt?.request_id;
  const currency = (c?.currency || "eur").toLowerCase();
  const money = (value, selected = currency) => new Intl.NumberFormat(selected.toLowerCase() === "brl" ? "pt-BR" : "pt-PT", { style: "currency", currency: selected.toUpperCase() }).format(Number(value) || 0);
  const receiptMoney = (value) => money(value, paid?.currency || currency);
  const terminal = ["failed", "expired"].includes(paid?.payment_status);
  const completed = ["paid", "partially_refunded", "refunded", "disputed"].includes(paid?.payment_status);
  const awaiting = Boolean((pixRequestId || sessionId) && !terminal && !completed);

  useEffect(() => {
    setC(undefined); setErr(""); setPaid(null); setAttempt(readAttempt());
    let cancelled = false;
    api.get(`/public/coupon/${encodeURIComponent(code)}`).then((r) => { if (!cancelled) setC(r.data); }).catch((e) => { if (!cancelled) { setErr(apiError(e)); setC(null); } });
    return () => { cancelled = true; };
    // Storage is scoped to the coupon, rather than a payment URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  useEffect(() => {
    if (!pixRequestId && !sessionId) return;
    let cancelled = false, timer;
    const started = Date.now();
    setPaid({ pending: true });
    const tick = async () => {
      try {
        const path = pixRequestId ? `/payments/pix/status/${encodeURIComponent(pixRequestId)}` : `/payments/status/${encodeURIComponent(sessionId)}`;
        const { data } = await api.get(path);
        if (cancelled) return;
        if (data.coupon && data.coupon.toUpperCase() !== code.toUpperCase()) {
          setPaid({ pending: true, stopped: true, blocked: true, message: "Esta referência pertence a outro cupom. Verifique o endereço da compra." }); return;
        }
        if (["paid", "partially_refunded", "refunded", "disputed", "failed", "expired"].includes(data.payment_status)) { setPaid(data); return; }
        setPaid({ ...data, pending: true });
      } catch (e) {
        if (cancelled) return;
        setPaid({ pending: true, unresolved: e.response?.status === 404, message: "Não foi possível consultar agora. Não faça outro pagamento; verifique novamente." });
      }
      if (Date.now() - started < 300000) timer = setTimeout(tick, 3000);
      else setPaid((previous) => ({ ...previous, pending: true, stopped: true }));
    };
    tick();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [pixRequestId, sessionId, code, checkVersion]);

  useEffect(() => {
    let cancelled = false;
    setP5Enabled(false);
    setP5CheckoutEnabled(false);
    if (!c || c.status !== "Ativa") return () => { cancelled = true; };
    api.get("/public/p5/config").then(({ data }) => {
      if (cancelled) return;
      const selected = (c.currency || "eur").toLowerCase();
      setP5Enabled(Boolean(c.p5_eligible && data?.currencies?.[selected]));
      setP5CheckoutEnabled(Boolean(data?.checkout_currencies?.[selected]));
    }).catch(() => {
      if (!cancelled) { setP5Enabled(false); setP5CheckoutEnabled(false); }
    });
    return () => { cancelled = true; };
  }, [c?.cupom, c?.currency, c?.status]);

  const pay = async () => {
    if (payingRef.current || awaiting || currency === "brl") return;
    const v = Number(String(amount).replace(",", "."));
    if (!Number.isFinite(v) || v < 1 || v > 10000) { toast.error("Indique um valor entre 1 e 10.000 na moeda da campanha"); return; }
    payingRef.current = true; setPaying(true);
    try {
      const { data } = await api.post("/public/pay", { code, amount: v, origin_url: window.location.origin, email: email || null });
      window.location.assign(data.checkout_url);
    } catch (e) { toast.error(apiError(e)); }
    finally { payingRef.current = false; setPaying(false); }
  };
  const retryPixCheckout = async () => {
    if (payingRef.current || !pixRequestId) return;
    payingRef.current = true; setPaying(true);
    try {
      const { data } = await api.post("/public/pix/checkout", { request_id: pixRequestId });
      saveAttempt({ request_id: pixRequestId, checkout_url: data.checkout_url });
      window.location.assign(data.checkout_url);
    } catch (e) { toast.error(apiError(e)); }
    finally { payingRef.current = false; setPaying(false); }
  };
  const parsed = Number(String(amount).replace(",", ".")) || 0;
  const newAttempt = () => {
    saveAttempt(null); setPaid(null);
    const url = new URL(window.location.href); url.searchParams.delete("pix_request_id"); url.searchParams.delete("session_id"); url.searchParams.delete("cancel");
    window.history.replaceState({}, "", url);
    // React Router reads search params on navigation; reload guarantees old references are removed.
    window.location.replace(url.toString());
  };

  const copy = () => { navigator.clipboard?.writeText(c.cupom).catch(() => {}); toast.success("Código copiado — mostre-o no local"); };
  const downloadQr = async () => {
    try {
      const svg = document.querySelector('[data-testid="public-coupon-qr"] svg');
      const result = await saveQr(svg, `qr-${c.cupom}.png`);
      if (result === "cancelled") return;
      if (c.claim_id) api.post(`/public/coupon/${encodeURIComponent(code)}/qr-downloaded`, { claim_id: c.claim_id }).catch(() => {});
      toast.info(result === "shared" ? "QR partilhado." : "Imagem do QR preparada. Se abrir numa nova janela, use Partilhar → Guardar imagem.");
    } catch (error) { toast.error(error.message); }
  };

  const active = c?.status === "Ativa";

  return (
    <div className="min-h-screen bg-[#0C0A14] text-white flex flex-col relative overflow-hidden"><div className="absolute inset-0 opacity-30"><GlobeCanvas color="167,139,250" /></div>
      <div className="px-6 pt-6 flex items-center justify-between relative">
        <BrandLogo tagline />
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
                  <div data-testid="public-coupon-qr" className="bg-white p-2 rounded-xl border border-purple-100 flex flex-col items-center gap-1.5">
                    {!p5Enabled ? <QRCodeSVG value={`${window.location.origin}/c/${encodeURIComponent(c.cupom)}`} size={92} fgColor="#3B0764" /> : <p className="text-[10px] font-bold text-purple-700 text-center w-[92px]">Use o QR P5 seguro abaixo</p>}
                    {!p5Enabled && <button data-testid="public-coupon-download-qr" onClick={downloadQr} className="text-[10px] font-semibold text-purple-700 hover:underline inline-flex items-center gap-1"><Download className="w-3 h-3" /> Guardar QR</button>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">O seu código</p>
                    <p data-testid="public-coupon-code" className="font-coupon font-bold text-lg tracking-wider text-purple-700 break-all">{c.cupom}</p>
                    <button data-testid="public-coupon-copy" onClick={copy} className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 px-3 py-1.5 rounded-lg btn-press"><Copy className="w-3.5 h-3.5" /> Copiar código</button>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="flex items-center gap-1"><CalendarDays className="w-3.5 h-3.5" /> Válido até {new Date(c.validade).toLocaleDateString("pt-PT")}</span>
                  <span data-testid="public-coupon-claims" className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {num(c.claims)} aberturas registadas</span>
                </div>
                {completed && (
                  <div data-testid="public-pay-success" className="rounded-2xl bg-emerald-50 border border-emerald-100 p-4 text-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-1" />
                    <p className="text-sm font-bold text-emerald-800">{paid.payment_status === "refunded" ? "Pagamento reembolsado" : paid.payment_status === "partially_refunded" ? "Pagamento parcialmente reembolsado" : paid.payment_status === "disputed" ? "Pagamento em análise" : "Pagamento confirmado"} · {receiptMoney(paid.amount)}</p>
                    <div data-testid="public-receipt" className="mt-2 text-left text-xs text-emerald-900 bg-white/70 rounded-xl p-3 space-y-0.5">
                      <p className="font-semibold uppercase tracking-wider text-[10px] text-emerald-700">{(paid.currency || currency).toLowerCase() === "brl" ? "Recibo Pix" : "Recibo"}{c.p5_eligible ? " · P5" : ""}</p>
                      <p>Conta: <b>{receiptMoney(paid.gross_amount)}</b></p>
                      {paid.gross_amount > 0 && paid.discount > 0 && <p data-testid="public-receipt-discount-percent">Desconto RRClub: <b>{Math.round((paid.discount / paid.gross_amount) * 100)}%</b></p>}
                      {paid.refunded_amount > 0 && <p data-testid="public-refund-amount">Reembolsado: <b>{receiptMoney(paid.refunded_amount)}</b></p>}
                      <p>Desconto aplicado: <b>−{receiptMoney(paid.discount)}</b></p>
                      <p>Pago: <b>{receiptMoney(paid.amount)}</b> · Ref. {paid.redemption_id || (paid.request_id || paid.session_id || "").slice(-8)}</p>
                      {paid.customer_email && <p className="text-emerald-700">{paid.receipt_emailed ? `Recibo enviado para ${paid.customer_email}` : `Recibo disponível neste ecrã (${paid.customer_email})`}</p>}
                    </div>
                    <button data-testid="public-receipt-print" onClick={() => window.print()} className="mt-2 text-xs font-semibold text-emerald-700 underline">Guardar / imprimir recibo</button>
                    <p className="text-xs text-emerald-700 mt-1">{paid.payment_status === "paid" ? `Mostre este ecrã ao staff de ${c.parceiro}. A redenção já ficou registada.` : "Consulte o estabelecimento para esclarecer o estado desta compra."}</p>
                  </div>
                )}
                {terminal && <div data-testid="public-pay-failed" className="text-xs text-red-600 bg-red-50 rounded-xl px-3 py-2">{paid.payment_status === "expired" ? "A cobrança expirou." : "O pagamento não foi concluído."} <button onClick={newAttempt} className="underline font-semibold">{currency === "brl" ? "Voltar ao cupom e pedir nova cobrança ao parceiro" : "Iniciar nova tentativa"}</button></div>}
                {awaiting && <div data-testid="public-pay-polling" role="status" className="text-xs text-purple-700 bg-purple-50 rounded-xl p-3 space-y-2">
                  {paid?.amount != null && <p data-testid="public-pix-confirmed-bill">Valor confirmado pelo estabelecimento: <b>{receiptMoney(paid.amount)}</b></p>}
                  <p>{paid?.stopped ? "Pagamento ainda pendente. Confirme o estado antes de tentar pagar novamente." : "A confirmar o pagamento. Não faça outro pagamento enquanto aguarda."}</p>
                  {paid?.message && <p>{paid.message}</p>}
                  <button onClick={() => setCheckVersion((v) => v + 1)} className="underline font-semibold">Verificar pagamento</button>
                  {!paid?.blocked && !paid?.checkout_url && !attempt?.checkout_url && pixRequestId && <button disabled={paying} onClick={retryPixCheckout} className="block underline font-semibold">Retomar pedido de pagamento</button>}
                  {!paid?.blocked && (paid?.checkout_url || attempt?.checkout_url) && <a href={paid?.checkout_url || attempt.checkout_url} className="block underline font-semibold">Retomar a mesma cobrança</a>}
                </div>}
                {active && !p5Enabled && currency === "brl" && !pixRequestId && !terminal && !completed && <p data-testid="public-pix-merchant-bill" className="text-sm text-purple-700 bg-purple-50 rounded-xl p-4">Apresente o cupom ao parceiro. O estabelecimento confirma o valor e gera a cobrança Pix.</p>}
                {active && p5Enabled && !awaiting && !terminal && !completed && (
                  <P5FollowerPanel code={code} currency={currency} checkoutEnabled={p5CheckoutEnabled} />
                )}
                {active && !p5Enabled && currency !== "brl" && !awaiting && !terminal && !completed && (
                  <div data-testid="public-pay-card" className="rounded-2xl border border-slate-200 p-4 space-y-2">
                    <StripeModeBanner compact />
                    <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5"><CreditCard className="w-3.5 h-3.5 text-purple-600" /> Pagar já com desconto aplicado</p>
                    <div className="flex gap-2">
                      <input data-testid="public-pay-amount" value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" placeholder={`Valor da conta (${currency === "brl" ? "R$" : "€"})`} className="flex-1 h-10 px-3 rounded-xl border border-slate-200 bg-slate-50 text-sm" />
                      <button data-testid="public-pay-button" disabled={paying || !Number.isFinite(parsed) || parsed < 1 || parsed > 10000} onClick={pay} className="h-10 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold btn-press">{paying ? "A abrir..." : "Pagar"}</button>
                    </div>
                    {currency !== "brl" && <input data-testid="public-pay-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email para receber o recibo (opcional)" className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-slate-50 text-sm" />}
                    {parsed >= 1 && <p data-testid="public-pay-preview" className="text-xs text-slate-600">Paga <b className="text-purple-700">{money(+(parsed * (1 - c.desconto / 100)).toFixed(2))}</b> em vez de {money(parsed)} · poupa {money(+(parsed * c.desconto / 100).toFixed(2))}</p>}
                    <p className="text-[11px] text-slate-400 flex items-center gap-1"><Smartphone className="w-3 h-3" /> {currency === "brl" ? "Pix · pagamento seguro via Stripe" : "MB WAY · Cartão de débito/crédito · pagamento seguro via Stripe"}</p>
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
