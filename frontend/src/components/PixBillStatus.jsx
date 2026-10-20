import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { api, moneyIn } from "../lib/api";

// Payment confirmation and internal transfers are separate states.
export function PixBillStatus({ bill, onPaid }) {
  const [payment, setPayment] = useState(bill);
  const [version, setVersion] = useState(0);
  const [message, setMessage] = useState("");
  const callback = useRef(onPaid);
  const notified = useRef(null);
  callback.current = onPaid;

  useEffect(() => {
    let stopped = false, timer;
    const controller = new AbortController();
    const started = Date.now();
    setPayment((previous) => previous.request_id === bill.request_id ? previous : bill);
    setMessage("");
    const tick = async () => {
      try {
        const { data } = await api.get(`/payments/pix/status/${encodeURIComponent(bill.request_id)}`, { signal: controller.signal });
        if (stopped) return;
        setPayment(data);
        setMessage("");
        if (data.payment_status === "paid") {
          if (notified.current !== bill.request_id) {
            notified.current = bill.request_id;
            callback.current?.();
          }
          if (["completed", "held"].includes(data.split_status)) return;
        }
        if (["expired", "failed", "refunded", "partially_refunded", "disputed"].includes(data.payment_status)) return;
      } catch {
        if (stopped) return;
        setMessage("Não foi possível atualizar. Não gere outra cobrança para a mesma compra; verifique novamente.");
      }
      if (Date.now() - started < 300000) timer = setTimeout(tick, 3000);
      else setMessage("Consulta automática pausada. Verifique o pagamento antes de gerar outra cobrança para esta compra.");
    };
    tick();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
    // A new object for the same request must not restart its polling deadline.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bill.request_id, version]);

  const paid = payment.payment_status === "paid";
  const ended = ["failed", "expired", "refunded", "partially_refunded", "disputed"].includes(payment.payment_status);
  return <div className="space-y-2" aria-live="polite" data-testid="pix-bill-status">
    <p className="font-semibold text-purple-900">Cobrança Pix · {moneyIn(payment.amount, "brl")}</p>
    {paid ? <>
      <p className="font-semibold text-emerald-700">Pagamento confirmado. Não cobre novamente.</p>
      <p className="text-xs text-slate-600">{payment.split_status === "completed" ? "Divisão concluída nos saldos Stripe. Os depósitos bancários seguem os prazos da Stripe." : payment.split_status === "held" ? "Divisão retida para revisão. O pagamento do cliente continua registado." : "Pagamento recebido; divisão em processamento. O cliente não precisa pagar outra vez."}</p>
    </> : ended ? <p className="text-sm text-slate-700">{["failed", "expired"].includes(payment.payment_status) ? "Cobrança expirada ou não concluída. Confirme o estado antes de preparar nova cobrança." : "Pagamento com reembolso ou contestação. Consulte o histórico antes de cobrar novamente."}</p> : <>
      <p className="text-xs text-slate-600">Peça ao cliente para abrir esta cobrança e pagar no checkout seguro.</p>
      <div className="bg-white p-3 rounded-xl inline-block"><QRCodeSVG value={payment.customer_url || bill.customer_url} size={160} /></div>
      <p className="text-xs text-purple-800">Aguardando pagamento. Gerar a cobrança não confirma a venda.</p>
      <a className="text-sm underline text-purple-700 block" href={payment.customer_url || bill.customer_url || bill.checkout_url} target="_blank" rel="noreferrer">Abrir cobrança do cliente</a>
    </>}
    {message && <p className="text-xs text-amber-800">{message}</p>}
    <button type="button" className="text-xs text-purple-700 underline" onClick={() => setVersion((v) => v + 1)}>Verificar pagamento</button>
  </div>;
}
