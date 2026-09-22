import { CheckCircle2, Circle, Landmark, CreditCard, Ticket, ArrowRight } from "lucide-react";

export const PartnerOnboarding = ({ hasIban, connect, hasCampaign, onIban, onConnect }) => {
  const connectDone = !!connect?.charges_enabled;
  const connectUnavailable = connect?.available === false;
  const steps = [
    { id: "iban", icon: Landmark, done: hasIban, title: "1. IBAN de recebimento", desc: hasIban ? "Conta bancária definida" : "Indique a conta onde recebe os pagamentos por QR", cta: hasIban ? "Alterar" : "Adicionar IBAN", onClick: onIban },
    { id: "connect", icon: CreditCard, done: connectDone, optional: connectUnavailable, title: "2. Ligar Stripe (split automático)", desc: connectDone ? "Ativo — a sua parte cai direto na sua conta" : connectUnavailable ? "Indisponível por agora — a plataforma transfere para o seu IBAN manualmente" : connect?.connected ? "Onboarding iniciado — conclua os dados no Stripe" : "Receba automaticamente a sua parte de cada pagamento", cta: connectDone ? null : connect?.connected ? "Continuar" : "Ativar", onClick: onConnect, disabled: connectUnavailable },
    { id: "campaign", icon: Ticket, done: hasCampaign, title: "3. Primeiro cupão QR", desc: hasCampaign ? "Cupão ativo — imprima o cartaz A5 e coloque na mesa/balcão" : "O admin cria a campanha com o seu influencer; peça em Mensagens", cta: null },
  ];
  const done = steps.filter((s) => s.done).length;
  if (done === 3) return null;
  return (
    <div data-testid="partner-onboarding" className="card-soft p-5 border-l-4 border-purple-500">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Comece a receber em 3 passos</h3>
          <p className="text-xs text-slate-500">Configuração inicial do parceiro</p>
        </div>
        <span data-testid="partner-onboarding-progress" className="text-xs font-bold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-full">{done}/3</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {steps.map((s) => (
          <div key={s.id} data-testid={`onboarding-step-${s.id}`} className={`rounded-2xl p-4 border ${s.done ? "bg-emerald-50/60 border-emerald-100" : "bg-slate-50 border-slate-100"}`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`w-9 h-9 rounded-xl flex items-center justify-center ${s.done ? "bg-emerald-100 text-emerald-600" : "bg-white text-purple-600"}`}><s.icon className="w-4 h-4" /></span>
              {s.done ? <CheckCircle2 className="w-5 h-5 text-emerald-500" data-testid={`onboarding-step-${s.id}-done`} /> : <Circle className="w-5 h-5 text-slate-300" />}
            </div>
            <p className="text-sm font-semibold text-slate-900">{s.title}</p>
            <p className="text-xs text-slate-500 mt-0.5 min-h-[32px]">{s.desc}</p>
            {s.cta && !s.done && (
              <button data-testid={`onboarding-step-${s.id}-cta`} disabled={s.disabled} onClick={s.onClick} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-purple-700 hover:underline disabled:opacity-50 disabled:no-underline">{s.cta} <ArrowRight className="w-3 h-3" /></button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
