import { useCallback, useEffect, useRef, useState } from "react";
import { Euro, Ticket, BadgePercent, HandCoins, Receipt, ScanLine, Download, CheckCircle2, Landmark, QrCode } from "lucide-react";
import { toast } from "sonner";
import { KpiCard } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { useHashScroll } from "../lib/useHashScroll";
import { api, apiError, dashboardMoney as eur, moneyIn, reportCurrency, num, downloadCsv } from "../lib/api";
import { Input } from "../components/ui/input";
import { PageSkeleton } from "../components/PageSkeleton";
import { QrScannerDialog } from "../components/QrScannerDialog";
import { parseCustomerQr } from "../lib/p5Scan";
import { PartnerOnboarding } from "../components/PartnerOnboarding";
import { ParceiroCopiloto } from "../components/ParceiroCopiloto";
import { CouponQrDialog } from "../components/CouponQrDialog";
import { useRealtime } from "../services/ws";
import { useFlash } from "../services/live";
import { StatusBadge } from "../components/KpiCard";
import { PixBillStatus } from "../components/PixBillStatus";
import { PartnerPhotoButton } from "../components/PartnerPhotoButton";
import { CosmicHeader, HeaderStat } from "../components/CosmicHeader";

const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

export default function PartnerDashboard() {
  const { user, refreshUnread } = useApp();
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [code, setCode] = useState("");
  const [amount, setAmount] = useState("");
  const [preview, setPreview] = useState(null);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [p5Currencies, setP5Currencies] = useState({});
  const [p5ScanRef, setP5ScanRef] = useState("");
  const [p5ScanRejected, setP5ScanRejected] = useState(false);
  const [p5ScanState, setP5ScanState] = useState("idle");
  const scanSequence = useRef(0);
  const [p5Bill, setP5Bill] = useState(null);
  const [pixBill, setPixBill] = useState(null);
  const [lastReceipt, setLastReceipt] = useState(null);
  const [idemKey, setIdemKey] = useState(newKey);
  const [submitting, setSubmitting] = useState(false);
  const [iban, setIban] = useState("");
  const [ibanEdit, setIbanEdit] = useState(false);
  const [connect, setConnect] = useState(null);
  const [pixAvailable, setPixAvailable] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [qrCampaign, setQrCampaign] = useState(null);
  const [qrActivity, setQrActivity] = useState([]);
  const [qrActivityState, setQrActivityState] = useState("loading");
  const [flash, triggerFlash] = useFlash();
  const [live, setLive] = useState(false);
  useRealtime((ev) => {
    if (ev.tipo === "ligado") { setLive(true); return; }
    if (ev.tipo === "desligado") { setLive(false); return; }
    if (ev.tipo === "pagamento_atualizado") { load(); return; }
    if (ev.tipo === "novo_clique" || ev.tipo === "p5_session_aberta" || ev.tipo === "p5_qr_lido") {
      api.get("/partner/qr/activity").then(({ data }) => {
        setQrActivity(data.events || []);
        setQrActivityState("ready");
      }).catch(() => setQrActivityState("unavailable"));
      return;
    }
    if (ev.tipo === "redencao_registada" && ev.record) {
      const r = ev.record;
      setData((d) => {
        if (!d || d.redemptions.some((x) => x.id === r.id)) return d;
        const t = d.totals, count = t.count + 1, revenue = t.revenue + r.amount;
        return { ...d, totals: { ...t, count, revenue, discounts: t.discounts + r.discount, commission: t.commission + r.commission, ticket: revenue / count, online_paid: (t.online_paid || 0) + (r.paid_online ? r.amount - r.discount : 0) },
          redemptions: [{ ...r, enter: true }, ...d.redemptions].slice(0, 100) };
      });
      ["revenue", "count", "discounts", "commission", "ticket"].forEach(triggerFlash);
      if (ev.origem === "qr") toast.success(`Pagamento por QR recebido · ${r.coupon} · ${eur(r.amount - r.discount)}`);
    }
  });

  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("connect");
    if (p === "return") toast.success("Dados Stripe submetidos — a verificar o estado da ligação...");
    if (p === "refresh") toast.info("O link do Stripe expirou. Clique em 'Continuar onboarding' para retomar.");
  }, []);

  useEffect(() => {
    if (!data?.partner?.currency && !data?.partner?.id) return;
    let cancelled = false;
    const check = async () => {
      if (data?.partner?.currency === "brl") {
        const { data: availability } = await api.get("/public/pix/availability");
        if (!cancelled) setPixAvailable(!!availability.accepting_new_payments);
        if (!availability.configured) {
          if (!cancelled) setConnect({ connected: false, available: false });
          return;
        }
      }
      const response = await api.get(data?.partner?.currency === "brl" ? "/partner/pix/connect/status" : "/partner/connect/status");
      if (!cancelled) setConnect(response.data);
    };
    check().catch(() => { if (!cancelled) setConnect({ connected: false, available: false, status_verified: false, reason: "Não foi possível verificar os recebimentos. Tente novamente mais tarde." }); });
    return () => { cancelled = true; };
  }, [data?.partner?.currency, data?.partner?.id]);

  const startConnect = async () => {
    setConnecting(true);
    try {
      const { data: res } = await api.post(data?.partner?.currency === "brl" ? "/partner/pix/connect/onboard" : "/partner/connect/onboard", { origin_url: window.location.origin });
      if (res.available === false) { toast.info(res.reason, { duration: 9000 }); setConnect((c) => ({ ...(c || {}), available: false })); setConnecting(false); return; }
      window.location.href = res.url;
    } catch (err) { toast.error(apiError(err)); setConnecting(false); }
  };

  const saveIban = async (e) => {
    e.preventDefault();
    try { await api.post("/partner/iban", { iban, titular: user.nome }); toast.success("IBAN guardado — usado para receber os pagamentos online"); setIbanEdit(false); load(); }
    catch (err) { toast.error(apiError(err)); }
  };

  const load = useCallback(() => { setLoadError(""); return api.get("/dashboard/partner").then((r) => setData(r.data)).catch((e) => { setLoadError(apiError(e)); }); }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let active = true;
    const refresh = () => api.get("/partner/qr/activity")
      .then(({ data }) => {
        if (!active) return;
        setQrActivity(data.events || []);
        setQrActivityState("ready");
      })
      .catch(() => { if (active) setQrActivityState("unavailable"); });
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => { active = false; clearInterval(interval); };
  }, [data?.partner?.id, data?.partner?.currency]);

  useEffect(() => {
    const c = code.trim().toUpperCase();
    if (c.length < 4) { setPreview(null); return; }
    const t = setTimeout(() => api.get(`/coupons/preview/${encodeURIComponent(c)}`).then((r) => setPreview(r.data)).catch(() => setPreview(null)), 250);
    return () => clearTimeout(t);
  }, [code]);

  useEffect(() => {
    let active = true;
    api.get("/public/p5/config")
      .then(({ data }) => { if (active) setP5Currencies(data?.currencies || {}); })
      .catch(() => { if (active) setP5Currencies({}); });
    return () => { active = false; };
  }, []);

  const p5EligibleCampaign = preview && Number(preview.desconto) === 5 && Number(preview.comissao) === 5 && Boolean(preview.influencer_id);
  const p5Mode = Boolean(p5EligibleCampaign && p5Currencies[String(preview.currency || data?.partner?.currency || "eur").toLowerCase()]);
  const parsedAmount = parseFloat(String(amount).replace(",", ".")) || 0;

  const handleValidate = async (e) => {
    e.preventDefault();
    if (submitting) return;
    if (!code.trim()) { toast.error("Introduza o código do cupom."); return; }
    if (!parsedAmount || parsedAmount <= 0) { toast.error("Informe um valor de compra válido."); return; }
    if (p5ScanRejected || (p5ScanRef && !p5Mode)) {
      toast.error("QR P5 não validado para esta campanha. Confirme a ativação do P5 e volte a ler o QR da sessão; não registe como venda manual.");
      return;
    }
    setSubmitting(true);
    try {
      if (p5Mode) {
        if (!p5ScanRef || p5ScanRef.length < 24) {
          toast.error("Leia o QR P5 desta sessão do cliente. O QR genérico não autoriza uma cobrança.");
          return;
        }
        const { data: bill } = await api.post("/partner/p5/charges", {
          code, scan_ref: p5ScanRef, gross_amount: parsedAmount, idempotency_key: idemKey,
        });
        setP5Bill(bill);
        setIdemKey(newKey()); // Each new follower/session must have its own idempotency key.
        toast.success("Conta confirmada! O cliente verá o valor e poderá pagar quando o MB WAY estiver apto.");
        return;
      }
      if (preview?.currency === "brl") {
        if (!pixAvailable) { toast.info("Pix ainda não está liberado para cobranças nesta plataforma."); return; }
        const { data: bill } = await api.post("/partner/pix/checkout", { code, amount: parsedAmount, origin_url: window.location.origin, request_id: idemKey });
        setPixBill(bill);
        toast.success("Cobrança Pix criada. Aguarde a confirmação do pagamento.");
        return;
      }
      const { data: res } = await api.post("/redemptions", { code, amount: parsedAmount, idempotency_key: idemKey });
      if (res.duplicate) toast.warning("Pedido repetido — redenção já registada (idempotência server-side).");
      else toast.success(`Venda validada! Comissão de ${moneyIn(res.record.commission, res.record.currency || "eur")} registada (taxa travada ${(res.record.rate * 100).toFixed(0)}%).`);
      setLastReceipt(res.record);
      setCode(""); setAmount(""); setPreview(null); setIdemKey(newKey());
      load(); refreshUnread();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const onDetected = useCallback((value) => {
    const { code: coupon, scanRef, isP5Url } = parseCustomerQr(value, window.location.origin);
    const requestNo = ++scanSequence.current;
    setCode(coupon);
    setP5ScanRef("");
    setP5ScanState(scanRef ? "checking" : "idle");
    setP5ScanRejected(isP5Url && !scanRef);
    setP5Bill(null);
    setIdemKey(newKey());
    if (isP5Url && !scanRef) {
      toast.error("QR P5 inválido ou de outro endereço. Peça ao cliente para abrir a sessão RRClub neste site.");
    } else if (scanRef) {
      api.post("/partner/p5/scans", { code: coupon, scan_ref: scanRef })
        .then(() => {
          if (requestNo !== scanSequence.current) return;
          setP5ScanRef(scanRef);
          setP5ScanState("verified");
          toast.success("QR P5 confirmado pelo servidor. Pode aprovar o valor da conta.");
        })
        .catch((err) => {
          if (requestNo !== scanSequence.current) return;
          setP5ScanState("invalid");
          setP5ScanRejected(true);
          toast.error(apiError(err));
        });
    } else {
      toast.success("Cupão detetado: " + coupon);
    }
  }, []);

  const exportCsv = () => {
    downloadCsv(`redencoes-${(data.partner?.nome || "parceiro").toLowerCase().replace(/\s+/g, "-")}.csv`, "id;cupom;influencer;valor;desconto;comissao;taxa;data;staff;moeda",
      data.redemptions.map((r) => [r.id, r.coupon, r.influencer, r.amount.toFixed(2), r.discount.toFixed(2), r.commission.toFixed(2), r.rate, r.date, r.staff, r.currency || "eur"].join(";")));
    toast.success("CSV exportado com sucesso");
  };

  useHashScroll(!!data);
  if (!data && loadError) return <div role="alert" data-testid="partner-access-error" className="card-soft p-6 space-y-3"><h1 className="text-xl font-semibold">Acesso ao estabelecimento indisponível</h1><p className="text-sm text-slate-600">{loadError}</p><p className="text-sm text-slate-500">Peça ao administrador para verificar a associação da sua conta em Gestão → Parceiros → Associar conta.</p><button onClick={load} className="px-4 py-2 rounded-xl bg-purple-600 text-white">Tentar novamente</button></div>;
  if (!data) return <PageSkeleton />;
  const { totals, trend, leaderboard, redemptions, campaigns = [] } = data;

  return (
    <div className="space-y-6">
      <CosmicHeader testId="partner-header">
        <div className="flex items-center gap-4">
          <PartnerPhotoButton current={data.partner?.avatar} onSaved={load} />
          <div className="min-w-0 flex-1">
            <p className="text-[11px] uppercase tracking-[0.14em] text-white/50 font-semibold">Parceiro</p>
            <h1 data-testid="partner-greeting" className="font-display text-xl sm:text-2xl font-extrabold tracking-tight truncate">{user.nome}</h1>
          </div>
          {live && <span data-testid="partner-live-badge" className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 border border-emerald-400/20 px-3 py-1 rounded-full"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 live-dot" /> ao vivo</span>}
        </div>
        <div className="grid grid-cols-3 gap-3 mt-6">
          <HeaderStat testId="partner-stat-count" label="Validações" value={num(totals.count || 0)} sub="confirmadas" />
          <HeaderStat testId="partner-stat-revenue" label="Vendas" value={eur(Math.round(totals.revenue || 0))} sub="atribuídas" />
          <HeaderStat testId="partner-stat-share" label="Recebe" value="80%" sub={eur(Math.round((totals.revenue || 0) * 0.8))} accent />
        </div>
        <p className="text-[11px] text-white/50 mt-4">Receita atribuída, redenções e comissões devidas a influencers.</p>
      </CosmicHeader>

      <PartnerOnboarding currency={data.partner?.currency || "eur"} hasIban={!!data.partner?.iban} connect={connect} hasCampaign={campaigns.some((c) => c.status === "Ativa")} onIban={() => { setIban(data.partner?.iban || ""); setIbanEdit(true); document.getElementById("partner-iban-card")?.scrollIntoView({ behavior: "smooth" }); }} onConnect={startConnect} />

      <section data-testid="partner-qr-activity" className="card-soft p-4 space-y-3">
        <div className="flex items-center gap-2">
          <ScanLine className="w-4 h-4 text-purple-600" />
          <h2 className="text-sm font-bold text-slate-900">Atividade QR · últimas 24 horas</h2>
        </div>
        <p className="text-xs text-slate-500">Abrir um cupão ou iniciar uma sessão P5 não confirma uma venda nem um pagamento.</p>
        {qrActivityState === "unavailable" && (
          <p role="status" className="text-xs text-amber-700">Não foi possível atualizar as leituras agora. Os registos permanecem preservados.</p>
        )}
        {qrActivityState === "loading" && <p className="text-xs text-slate-500">A verificar as interações...</p>}
        {qrActivityState === "ready" && qrActivity.length === 0 && (
          <p className="text-xs text-slate-500">Nenhuma abertura ou sessão P5 registada neste período.</p>
        )}
        {qrActivity.slice(0, 5).map((entry) => (
          <div key={entry.id} className="flex items-center justify-between gap-3 border-t border-slate-100 pt-2">
            <p className="text-xs text-slate-700">
              {entry.kind === "p5_qr_scanned" ? "QR P5 lido pelo parceiro" : entry.kind === "p5_session_opened" ? "Sessão P5 iniciada" : "Cupão aberto"} · <span className="font-semibold">{entry.coupon}</span>
            </p>
            <time className="text-[11px] text-slate-500" dateTime={entry.at}>
              {new Date(entry.at).toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
            </time>
          </div>
        ))}
      </section>

      <ParceiroCopiloto />

      <details className="card-soft p-4" data-testid="partner-historico-nao-conciliado">
        <summary className="text-sm font-semibold text-slate-700 cursor-pointer">Consultar histórico de resgates — valores não conciliados, podendo incluir simulações</summary>
        <p className="text-xs text-amber-700 mt-2 mb-3">Os números abaixo representam registos históricos e não comprovam pagamentos. Utilize o Copiloto acima para valores P5 confirmados.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard id="receita-atribuida" icon={Euro} label="Receita Atribuída" live={totals.revenue} format={(v) => eur(Math.round(v))} flash={flash.revenue} trend={trend.revenue} />
        <KpiCard id="redencoes" icon={Ticket} label="Redenções" live={totals.count} format={num} flash={flash.count} trend={trend.count} />
        <KpiCard id="descontos" icon={BadgePercent} label="Descontos Concedidos" live={totals.discounts} format={(v) => eur(Math.round(v))} flash={flash.discounts} />
        <KpiCard id="comissao-devida" icon={HandCoins} label="Comissão Devida" live={totals.commission} format={(v) => eur(Math.round(v))} flash={flash.commission} trend={trend.commission} />
        <KpiCard id="ticket-medio" icon={Receipt} label="Ticket Médio" live={totals.ticket} format={(v) => eur(+v.toFixed(2))} flash={flash.ticket} />
      </div>

      </details>

      {data.partner?.currency !== "brl" && <div data-testid="partner-iban-card" id="partner-iban-card" className="card-soft p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
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
      </div>}

      <div data-testid="partner-connect-card" className="card-soft p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${(data.partner?.currency === "brl" ? connect?.receiving_ready : (connect?.charges_enabled && connect?.payouts_enabled)) ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500"}`}><CheckCircle2 className="w-5 h-5" /></span>
          <div>
            <p className="text-sm font-semibold text-slate-900">Split automático dos pagamentos por QR (Stripe Connect)</p>
            <p className="text-xs text-slate-500" data-testid="partner-connect-status">
              {connect === null ? "A verificar..." : connect.status_verified === false ? (connect.reason || "Estado Stripe por verificar; os dados guardados foram preservados.") : data.partner?.currency === "brl" && connect.available === false ? "Cadastro disponível. Os recebimentos Pix aguardam a configuração brasileira da plataforma; poderá associar a sua conta depois." : (data.partner?.currency === "brl" ? connect.receiving_ready : (connect.charges_enabled && connect.payouts_enabled)) ? <>Ativo — a sua parte é encaminhada ao saldo da conta Stripe; o depósito bancário segue os prazos da Stripe{connect.bank_last4 ? ` (••••${connect.bank_last4})` : ""}; {data.partner?.currency === "brl" ? "o influencer recebe a sua parte numa transferência separada." : "a comissão fica na plataforma."}</> : connect.connected ? "Onboarding iniciado — conclua os dados no Stripe para ativar as transferências automáticas." : "Ligue a sua conta bancária ao Stripe para receber automaticamente a sua parte de cada pagamento, sem transferências manuais."}
            </p>
          </div>
        </div>
        {(data.partner?.currency === "brl" ? !connect?.receiving_ready : !(connect?.charges_enabled && connect?.payouts_enabled)) && <button data-testid="partner-connect-button" disabled={connecting || connect === null || connect.status_verified === false || (data.partner?.currency === "brl" && connect.available === false)} onClick={startConnect} className="px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-xs font-semibold btn-press shrink-0">{connecting ? "A abrir Stripe..." : connect?.connected ? "Continuar onboarding" : "Ativar split automático"}</button>}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="coupon-validation-card" className="card-soft p-5 scroll-mt-20" id="validar">
          <h3 className="text-lg font-semibold text-slate-900 mb-1">{p5Mode ? "P5 · Aprovar conta do cliente" : "Validação de Cupom"}</h3>
          <p className="text-xs text-slate-500 mb-4">{p5Mode ? "Leia o QR P5 do telemóvel do cliente; confirme o valor original da conta. O cliente paga depois." : "Escaneie o QR do cliente ou digite o código"}</p>
          <form onSubmit={handleValidate} className="space-y-3">
            <div className="flex gap-2">
              <Input data-testid="coupon-code-input" value={code} onChange={(e) => {
                const raw = e.target.value;
                if (raw.startsWith("https://")) onDetected(raw);
                else { scanSequence.current += 1; setCode(raw); setP5ScanRef(""); setP5ScanState("idle"); setP5ScanRejected(false); setP5Bill(null); setIdemKey(newKey()); }
              }} placeholder="Ex.: ROBSON-LUXE-25" className="font-coupon uppercase rounded-xl bg-slate-50" />
              <button type="button" data-testid="open-scanner-button" onClick={() => setScannerOpen(true)} className="shrink-0 h-11 px-4 sm:w-11 sm:px-0 rounded-xl bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center gap-2 text-xs font-semibold shadow-lg shadow-violet-900/30 btn-press" title="Escanear QR"><span className="sm:hidden">Ler QR</span>
                <ScanLine className="w-[18px] h-[18px]" />
              </button>
            </div>
            {code.trim().length >= 4 && (
              <div data-testid="coupon-preview" className={`text-xs px-3 py-2 rounded-lg ${preview?.status === "Ativa" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`}>
                {!preview ? "Cupom não encontrado para este parceiro"
                  : preview.status === "Ativa" ? <>✓ {preview.nome} · {preview.influencer} · {preview.desconto}% desconto · comissão {preview.comissao}% · {(preview.currency || "eur").toUpperCase()}</>
                  : <>Cupom {preview.status.toLowerCase()} — não redimível</>}
              </div>
            )}
            {preview?.status === "Ativa" && p5EligibleCampaign && preview.currency === "eur" && !p5Currencies.eur && (
              <p data-testid="p5-pt-off" className="text-xs text-amber-700">
                Campanha P5 Portugal elegível, mas o fluxo QR ainda não está ativado nesta instalação. Ative P5_ENABLED e P5_EUR_ENABLED no backend.
              </p>
            )}
            {p5Mode && (
              <p data-testid="p5-qr-state" className={p5ScanRef ? "text-xs text-emerald-700" : "text-xs text-amber-700"}>
                {p5ScanState === "checking" ? "QR P5 lido. A confirmar o vínculo com o servidor..." :
                  p5ScanRef ? "QR P5 verificado pelo servidor. Pode aprovar a conta sem cobrar." :
                  "Aguardando QR P5: o cupão público isoladamente não identifica o cliente."}
              </p>
            )}
            {p5ScanRejected && <p role="alert" className="text-xs text-red-700">O QR desta sessão não foi reconhecido; nenhuma venda será registada.</p>}
            <Input data-testid="purchase-amount-input" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Valor da conta na moeda da campanha" inputMode="decimal" className="rounded-xl bg-slate-50" />
            {preview?.status === "Ativa" && parsedAmount > 0 && (
              <div data-testid="live-calculation" className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 rounded-lg px-3 py-2">
                  <p className="text-slate-500">Desconto ({preview.desconto}%)</p>
                  <p className="font-bold text-slate-900" data-testid="live-discount-value">{moneyIn(+(parsedAmount * preview.desconto / 100).toFixed(2), preview.currency || "eur")}</p>
                </div>
                <div className="bg-purple-50 rounded-lg px-3 py-2">
                  <p className="text-purple-500">Comissão ({preview.comissao}%)</p>
                  <p className="font-bold text-purple-700" data-testid="live-commission-value">{moneyIn(+(parsedAmount * preview.comissao / 100).toFixed(2), preview.currency || "eur")}</p>
                </div>
              </div>
            )}
            <button type="submit" disabled={submitting || (!p5Mode && preview?.currency === "brl" && !pixAvailable)} data-testid="validate-coupon-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press">
              {submitting ? "A processar..." : p5Mode ? "Aprovar conta P5 (sem cobrar)" : preview?.currency === "brl" ? pixAvailable ? "Gerar cobrança Pix" : "Pix aguarda ativação" : "Validar Venda"}
            </button>
          </form>
          {p5Bill && (
            <div data-testid="partner-p5-bill" className="mt-4 rounded-xl border border-purple-200 bg-purple-50 p-4 text-sm text-purple-900">
              <strong>Conta P5 aprovada pelo estabelecimento</strong>
              <p>Referência: {p5Bill.charge_id}</p>
              {p5Bill.net_minor != null && (
                <p>Total que o cliente verá: <b>{moneyIn(p5Bill.net_minor / 100, p5Bill.currency || preview?.currency || "eur")}</b></p>
              )}
              <p className="text-xs mt-1">
                Aguarde o pagamento do cliente. Ler o QR não regista uma venda nem distribui comissões.
              </p>
            </div>
          )}
          {pixBill && <div className="mt-4 p-4 rounded-xl bg-purple-50 border border-purple-100 text-center" data-testid="partner-pix-bill">
            <PixBillStatus bill={pixBill} onPaid={() => { load(); refreshUnread(); }} />
            <button type="button" className="text-xs text-purple-700 underline mt-3" onClick={() => { setPixBill(null); setIdemKey(newKey()); }}>Preparar outra conta</button>
          </div>}
          {lastReceipt && (
            <div data-testid="last-receipt" className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-100 flex items-start gap-2 fade-up">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
              <div className="text-xs text-emerald-800">
                <p className="font-semibold">Redenção {lastReceipt.id} registada</p>
                <p>{lastReceipt.coupon} · {moneyIn(lastReceipt.amount, lastReceipt.currency || "eur")} · comissão {moneyIn(lastReceipt.commission, lastReceipt.currency || "eur")} (taxa travada {(lastReceipt.rate * 100).toFixed(0)}%)</p>
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
              <div key={r.id} data-testid={`redemption-${r.id}`} className={`audit-item flex items-center justify-between gap-2 pb-3 border-b border-slate-50 last:border-0 ${r.enter ? "enter" : ""}`}>
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

      <QrScannerDialog open={scannerOpen} onOpenChange={setScannerOpen} onDetected={onDetected} preserveRaw />
      <CouponQrDialog campaign={qrCampaign} open={!!qrCampaign} onOpenChange={(o) => !o && setQrCampaign(null)} />

      <div data-testid="partner-campaigns-card" className="card-soft p-5">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Os seus cupões QR</h3>
        <p className="text-xs text-slate-500 mb-4">Descarregue o QR ou o cartaz A5 para colocar na mesa / balcão</p>
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm" data-testid="partner-campaigns-table">
            <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100"><th className="pb-3 pr-4 font-semibold">Campanha</th><th className="pb-3 pr-4 font-semibold">Cupom</th><th className="pb-3 pr-4 font-semibold">Influencer</th><th className="pb-3 pr-4 font-semibold">Desconto</th><th className="pb-3 pr-4 font-semibold">Status</th><th className="pb-3 font-semibold text-right">QR / Cartaz</th></tr></thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} data-testid={`partner-campaign-row-${c.id}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40">
                  <td className="py-3 pr-4 font-semibold text-slate-900">{c.nome}</td>
                  <td className="py-3 pr-4"><span className="font-coupon text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{c.cupom}</span></td>
                  <td className="py-3 pr-4 text-slate-600">{c.influencer}</td>
                  <td className="py-3 pr-4 text-slate-600">{c.desconto}%</td>
                  <td className="py-3 pr-4"><StatusBadge status={c.status} /></td>
                  <td className="py-3 text-right"><button data-testid={`partner-campaign-qr-${c.id}`} onClick={() => setQrCampaign(c)} className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 px-3 py-1.5 rounded-lg btn-press"><QrCode className="w-3.5 h-3.5" /> QR / Cartaz</button></td>
                </tr>
              ))}
              {campaigns.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-slate-400" data-testid="partner-campaigns-empty">Ainda sem cupões — o admin cria a campanha com o seu influencer.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
