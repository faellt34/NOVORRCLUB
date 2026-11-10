import React, { useState } from "react";
import { ArrowRight, CheckCircle2, Circle, RotateCcw, ShieldCheck } from "lucide-react";

const steps = [
  { role: "Influenciador", title: "Campanha partilhada", detail: "Link e QR disponibilizados ao seguidor" },
  { role: "Seguidor", title: "Cupom aberto", detail: "Seguidor consulta a campanha no telefone" },
  { role: "Parceiro", title: "QR validado", detail: "Parceiro valida o QR e introduz um valor de teste" },
  { role: "Seguidor", title: "Checkout apresentado", detail: "Prévia das opções de pagamento, sem cobrança" },
  { role: "Administração", title: "Operação acompanhada", detail: "Estado da campanha visível no monitor" },
];

const destinations = [
  { title: "Site e entrada", path: "/", detail: "Rota existente da aplicação" },
  { title: "Entrar", path: "/login", detail: "Autenticação existente" },
  { title: "Registar", path: "/registar", detail: "Registo existente" },
  { title: "Parceiro", path: "/parceiro", detail: "Painel existente, exige acesso autorizado" },
  { title: "Influenciador", path: "/influencer", detail: "Painel existente, exige acesso autorizado" },
  { title: "Administrador", path: "/admin", detail: "Painel existente, exige acesso autorizado" },
];

export default function PreviewV1() {
  const [index, setIndex] = useState(0);
  const [events, setEvents] = useState([]);
  const complete = index === steps.length;
  const advance = () => {
    if (complete) return;
    const step = steps[index];
    setEvents(current => [...current, { ...step, stamp: new Date().toLocaleTimeString("pt-PT") }]);
    setIndex(current => current + 1);
  };
  const restart = () => { setIndex(0); setEvents([]); };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900" data-testid="rrclub-preview-v1">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div><div className="font-bold text-xl tracking-tight text-blue-800">R-Conekta <span className="text-slate-500 font-medium">| RRClub</span></div><div className="text-xs text-slate-500">Ambiente V1 · homologação isolada</div></div>
          <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 rounded-full px-3 py-2"><ShieldCheck size={14}/> Sem pagamentos reais</div>
        </div>
      </header>
      <section className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-7">
          <p className="text-xs uppercase tracking-widest font-semibold text-blue-700 mb-2">Centro de operações / Preview V1</p>
          <h1 className="text-2xl md:text-4xl font-bold leading-tight">Simular a jornada completa da RRClub</h1>
          <p className="text-slate-600 mt-3 max-w-3xl">Esta área demonstra eventos no navegador, sem acesso a Stripe, dados de clientes ou produção. As páginas reais do projeto continuam disponíveis nas rotas existentes; as permissões de cada perfil são mantidas.</p>
        </div>
        <div className="grid lg:grid-cols-5 gap-5">
          <div className="lg:col-span-3 rounded-2xl border bg-white p-5 md:p-7 shadow-sm">
            <div className="flex justify-between text-sm text-slate-500 mb-4"><span>Simulação de ponta a ponta</span><span>{index} de {steps.length}</span></div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden mb-8"><div className="bg-blue-700 h-full transition-all" style={{ width: `${index / steps.length * 100}%` }} /></div>
            {complete ? <div className="py-8 text-center"><CheckCircle2 className="text-emerald-600 mx-auto mb-3" size={44}/><h2 className="text-xl font-bold">Ciclo de demonstração concluído</h2><p className="text-slate-600 mt-2">Nenhuma cobrança ou alteração de produção foi realizada.</p></div> :
              <div className="py-5"><p className="text-sm text-blue-700 font-semibold">{steps[index].role}</p><h2 className="text-2xl font-bold mt-2">{steps[index].title}</h2><p className="text-slate-600 mt-3">{steps[index].detail}</p><p className="text-xs text-slate-500 mt-5">Dados fictícios e eventos locais, apenas para testar a navegação do fluxo.</p></div>}
            <div className="flex gap-3 pt-4 border-t border-slate-100">
              <button type="button" onClick={advance} disabled={complete} className="flex-1 inline-flex justify-center items-center gap-2 rounded-xl bg-blue-700 text-white px-4 py-3 font-semibold disabled:opacity-40">Avançar teste <ArrowRight size={18}/></button>
              <button type="button" onClick={restart} aria-label="Reiniciar simulação" className="inline-flex items-center gap-2 rounded-xl border px-4 py-3"><RotateCcw size={17}/> Reiniciar</button>
            </div>
          </div>
          <div className="lg:col-span-2 rounded-2xl border bg-white p-5 md:p-6 shadow-sm">
            <h2 className="font-bold text-lg mb-4">Monitor de eventos</h2>
            {events.length === 0 ? <p className="text-slate-500 text-sm">Nenhum evento simulado. Avança no fluxo para acompanhar as etapas aqui.</p> :
              <ol className="space-y-4">{events.map((event, i) => <li key={i} className="flex gap-3 text-sm"><CheckCircle2 size={18} className="shrink-0 text-emerald-600 mt-1"/><div><div className="font-semibold">{event.title}</div><div className="text-slate-500">{event.role} · {event.stamp}</div></div></li>)}</ol>}
            {!complete && <div className="flex items-center gap-2 text-xs text-slate-500 mt-6"><Circle size={12}/> Aguardando próxima etapa</div>}
          </div>
        </div>
        <div className="mt-7"><h2 className="text-xl font-bold mb-3">Aceder aos módulos existentes</h2><div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">{destinations.map(item => <a key={item.path} href={item.path} className="block rounded-xl bg-white border border-slate-200 hover:border-blue-400 p-4"><div className="font-semibold">{item.title}</div><p className="text-sm text-slate-500 mt-1">{item.detail}</p><p className="text-xs text-blue-700 mt-3">{item.path}</p></a>)}</div></div>
      </section>
    </main>
  );
}
