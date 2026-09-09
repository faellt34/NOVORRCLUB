import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Clock, XCircle, BookOpen } from "lucide-react";
import { api } from "../lib/api";

export default function PaymentResult({ cancelled = false }) {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const [state, setState] = useState(cancelled ? "cancelled" : "polling");
  const [lookup, setLookup] = useState("");

  useEffect(() => {
    if (cancelled || !sessionId) return;
    let attempts = 0;
    const tick = async () => {
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        setLookup(data.lookup_key || "");
        if (data.payment_status === "paid") { setState("paid"); return; }
        if (["failed", "expired"].includes(data.payment_status)) { setState("failed"); return; }
      } catch {}
      if (++attempts < 10) setTimeout(tick, 2000); else setState("timeout");
    };
    tick();
  }, [sessionId, cancelled]);

  const views = {
    polling: { icon: Clock, color: "text-purple-600 bg-purple-50", title: "A confirmar pagamento...", text: "Aguarde alguns segundos enquanto confirmamos com o Stripe." },
    paid: { icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50", title: lookup === "club_monthly" ? "Subscrição Premium ativa!" : "Compra confirmada!", text: lookup === "club_monthly" ? "Todos os guias premium estão desbloqueados na sua área de E-books." : "O seu guia já está disponível para leitura na área de E-books." },
    failed: { icon: XCircle, color: "text-red-600 bg-red-50", title: "Pagamento não concluído", text: "O pagamento falhou ou expirou. Pode tentar novamente." },
    timeout: { icon: Clock, color: "text-amber-600 bg-amber-50", title: "Confirmação pendente", text: "Ainda não recebemos a confirmação. Verifique os E-books dentro de instantes." },
    cancelled: { icon: XCircle, color: "text-slate-600 bg-slate-100", title: "Pagamento cancelado", text: "Nenhum valor foi cobrado. Pode voltar aos guias quando quiser." },
  };
  const v = views[state];

  return (
    <div className="max-w-md mx-auto py-16 text-center" data-testid={`payment-${state}`}>
      <div className={`w-16 h-16 rounded-2xl mx-auto flex items-center justify-center mb-5 ${v.color}`}><v.icon className={`w-8 h-8 ${state === "polling" ? "animate-pulse" : ""}`} /></div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">{v.title}</h1>
      <p className="text-sm text-slate-500 mb-8">{v.text}</p>
      <Link to="/ebooks" data-testid="back-to-ebooks" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold btn-press"><BookOpen className="w-4 h-4" /> Ir para os E-books</Link>
    </div>
  );
}
