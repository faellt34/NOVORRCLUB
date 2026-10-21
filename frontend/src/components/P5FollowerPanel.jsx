import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { api, apiError, moneyIn } from "../lib/api";

/**
 * P5 follow-up: the QR contains only the scan reference, never the
 * follower's private session token. The follower does not choose the bill.
 */
export default function P5FollowerPanel({ code, currency, onPaymentStart }) {
  const storageKey = "rrclub_p5_session_" + String(code || "").toUpperCase();
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [pollVersion, setPollVersion] = useState(0);
  const [sessionVersion, setSessionVersion] = useState(0);
  const busyRef = useRef(false);
  const checkCurrency = currency === "brl" ? "brl" : "eur";

  useEffect(() => {
    let cancelled = false;
    setSession(null);
    setStatus(null);
    setError("");
    try {
      const old = JSON.parse(sessionStorage.getItem(storageKey) || "null");
      if (old?.session_token && old?.scan_ref && Date.parse(old.expires_at) > Date.now()) {
        setSession(old);
        return () => { cancelled = true; };
      }
    } catch { /* start a fresh private session */ }
    api.post("/public/p5/sessions", { code })
      .then(({ data }) => {
        if (cancelled) return;
        setSession(data);
        try { sessionStorage.setItem(storageKey, JSON.stringify(data)); } catch {}
      })
      .catch((e) => { if (!cancelled) setError(apiError(e)); });
    return () => { cancelled = true; };
  }, [code, storageKey, sessionVersion]);

  useEffect(() => {
    if (!session?.session_token) return;
    let cancelled = false;
    let timer;
    const started = Date.now();
    async function check() {
      try {
        const { data } = await api.get(
          "/public/p5/charges/current",
          { params: { code }, headers: { "X-P5-Session": session.session_token } },
        );
        if (cancelled) return;
        setStatus(data);
        setError("");
        if (["paid", "refunded", "disputed", "failed", "expired"].includes(data?.status)) return;
      } catch (e) {
        if (cancelled) return;
        setError(apiError(e));
      }
      if (!cancelled && Date.now() - started < 300000) {
        timer = setTimeout(check, 2500);
      }
    }
    check();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [session?.session_token, code, pollVersion]);

  const checkout = async () => {
    if (busyRef.current || !session?.session_token || !status?.charge_id) return;
    busyRef.current = true;
    setBusy(true);
    try {
      const { data } = await api.post(
        "/public/p5/charges/checkout",
        {
          charge_id: status.charge_id,
          origin_url: window.location.origin,
          email: email.trim() || null,
        },
        { headers: { "X-P5-Session": session.session_token } }
      );
      if (!data.checkout_url) throw new Error("Checkout indisponível");
      onPaymentStart?.(data);
      window.location.assign(data.checkout_url);
    } catch (e) {
      toast.error(apiError(e));
      setPollVersion((value) => value + 1);
    } finally {
      setBusy(false);
      busyRef.current = false;
    }
  };

  const renewSession = () => {
    try { sessionStorage.removeItem(storageKey); } catch {}
    setSession(null);
    setStatus(null);
    setPollVersion(0);
    setSessionVersion((n) => n + 1);
  };

  const qrUrl = session?.scan_ref
    ? window.location.origin + "/c/" + encodeURIComponent(code) +
      "?p5_ref=" + encodeURIComponent(session.scan_ref)
    : null;
  const state = status?.status || "none";
  const ready = state === "pending" && status?.charge_id;
  const due = Number(status?.net_minor || 0) / 100;

  return (
    <section
      data-testid="p5-follower-panel"
      className="rounded-2xl border border-purple-200 bg-purple-50 p-4 space-y-3 text-slate-800"
    >
      <p className="text-sm font-bold text-purple-800">
        P5 · Conta confirmada pelo estabelecimento
      </p>
      {!session && <p className="text-xs text-slate-600">A preparar o QR seguro...</p>}
      {qrUrl && state === "none" && (
        <>
          <p className="text-xs text-slate-600">
            Mostre este QR P5 ao parceiro. Só o estabelecimento pode definir o valor da conta.
          </p>
          <div className="flex justify-center bg-white rounded-xl p-3">
            <QRCodeSVG value={qrUrl} size={156} fgColor="#3B0764" />
          </div>
          <p className="text-xs text-center text-purple-700">
            À espera que o parceiro leia o QR e confirme a conta.
          </p>
        </>
      )}
      {status?.charge_id && (
        <div className="bg-white border border-purple-100 rounded-xl p-3 space-y-2">
          <p className="text-xs text-slate-500">Cobrança validada pelo estabelecimento</p>
          <div className="flex justify-between text-sm">
            <span>Valor da conta</span>
            <strong>{moneyIn((status.gross_minor || 0) / 100, checkCurrency)}</strong>
          </div>
          <div className="flex justify-between text-sm">
            <span>Desconto</span>
            <strong>-{moneyIn((status.discount_minor || 0) / 100, checkCurrency)}</strong>
          </div>
          <div className="flex justify-between text-base font-bold text-purple-800">
            <span>Total a pagar</span>
            <strong>{moneyIn(due, checkCurrency)}</strong>
          </div>
          {ready && (
            <>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Email do recibo (opcional)"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs"
              />
              <button
                type="button"
                onClick={checkout}
                disabled={busy}
                className="w-full rounded-xl bg-purple-700 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
                data-testid="p5-pay-button"
              >
                {busy ? "A abrir pagamento..." :
                  checkCurrency === "brl" ? "Pagar com Pix" : "Pagar com MB WAY / cartão"}
              </button>
            </>
          )}
          {state === "creating" && <p className="text-xs text-purple-700">A preparar a cobrança. Aguarde.</p>}
          {state === "checkout" && (
            <div className="space-y-2">
              <p className="text-xs text-amber-700">
                Pagamento iniciado. Aguarde a confirmação; não efetue outra cobrança.
              </p>
              {status.checkout_url && (
                <a
                  href={status.checkout_url}
                  className="block text-xs font-semibold text-purple-700 underline"
                >Retomar esta mesma cobrança</a>
              )}
            </div>
          )}
          {state === "paid" && (
            <p className="text-sm font-semibold text-emerald-700" role="status">
              Pagamento confirmado pelo sistema do banco/Stripe.
            </p>
          )}
          {["expired", "failed"].includes(state) && (
            <div className="space-y-2">
              <p className="text-xs text-red-700">
                Cobrança não concluída. Peça ao parceiro que confirme um novo QR P5.
              </p>
              <button
                type="button"
                onClick={renewSession}
                className="text-xs font-semibold text-purple-700 underline"
              >Criar novo QR P5</button>
            </div>
          )}
        </div>
      )}
      {!!error && <p className="text-xs text-red-700" role="alert">{error}</p>}
      {!!session && <button
        type="button"
        onClick={() => setPollVersion((v) => v + 1)}
        className="text-xs font-semibold text-purple-700 underline"
      >Verificar estado</button>}
      <p className="text-[11px] text-slate-500">
        O QR do cupão identifica a campanha; apenas o QR P5 associa a conta a esta sessão.
        Ler o QR não é pagar.
      </p>
    </section>
  );
}
