import React, { useState } from "react";
import { BrandLogo } from "../components/BrandLogo";
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
  const [country, setCountry] = useState("PT");
  const [amount, setAmount] = useState("100");
  const [method, setMethod] = useState("");
  const [warning, setWarning] = useState("");
  const value = Number(String(amount).replace(",", "."));
  const valid = Number.isFinite(value) && value > 0 && value <= 100000;
  const currency = country === "BR" ? "BRL" : "EUR";
  const cash = n => new Intl.NumberFormat(country === "BR" ? "pt-BR" : "pt-PT", { style: "currency", currency }).format(n || 0);
  const methods = country === "BR" ? ["Pix", "Cartão"] : ["MB WAY", "Cartão", "Apple Pay"];
  const benefit = valid ? Math.round(value * 5) / 100 : 0;
  const [events, setEvents] = useState([]);
  const complete = index === steps.length;
  const advance = () => {
    if (complete) return;
    if (index === 2 && !valid) { setWarning("Introduz um valor válido superior a zero."); return; }
    if (index === 3 && !method) { setWarning("Seleciona uma opção fictícia de pagamento."); return; }
    setWarning("");
    const step = steps[index];
    const detail = index === 2 ? ("Valor " + cash(value) + "; benefício ilustrativo " + cash(benefit)) : index === 3 ? (method + " simulado, sem cobrança") : step.detail;
    setEvents(current => [...current, { ...step, detail, stamp: new Date().toLocaleTimeString("pt-PT") }]);
    setIndex(current => current + 1);
  };
  const restart = () => { setIndex(0); setEvents([]); setMethod(""); setWarning(""); setAmount("100"); };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900" data-testid="rrclub-preview-v1">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div><BrandLogo dark size="sm" tagline /><div className="text-xs text-slate-500">Ambiente V1 · homologação isolada</div></div>
          <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 rounded-full px-3 py-2"><ShieldCheck size={14}/> Sem pagamentos reais</div>
        </div>
      </header>
      <section className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-5 flex gap-2 flex-wrap" aria-label="Selecionar país">
          {["PT", "BR"].map(item => <button key={item} type="button" aria-pressed={item === country}
            onClick={() => { restart(); setCountry(item); }}
            className={"px-4 py-2 rounded-xl font-semibold border " + (country === item ? "bg-[#203047] text-white" : "bg-white")}>
            {item === "PT" ? "Portugal · EUR" : "Brasil · BRL"}
          </button>)}
        </div>
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
              <div className="py-5"><p className="text-sm text-blue-700 font-semibold">{steps[index].role}</p><h2 className="text-2xl font-bold mt-2">{steps[index].title}</h2><p className="text-slate-600 mt-3">{steps[index].detail}</p>
                {index === 0 && <div className="mt-5 bg-slate-50 rounded-xl p-4 font-mono font-bold">DEMO-RRCLUB-V1 <p className="text-xs font-sans font-normal text-slate-500">Código fictício; não válido no site oficial</p></div>}
                {index === 2 && <label className="block mt-5 text-sm font-semibold">Valor de demonstração ({currency})
                  <input className="mt-2 w-full rounded-xl border px-4 py-3 text-lg" inputMode="decimal"
                    value={amount} onChange={e => { setAmount(e.target.value); setWarning(""); }} />
                </label>}
                {index === 3 && <div className="mt-5">
                  <div className="rounded-xl bg-slate-50 p-4 text-sm">
                    <div className="flex justify-between"><span>Valor</span><b>{cash(value)}</b></div>
                    <div className="flex justify-between mt-1"><span>Benefício ilustrativo (5%)</span><span>-{cash(benefit)}</span></div>
                    <div className="flex justify-between mt-2 border-t pt-2 text-base font-bold"><span>Total ilustrativo</span><span>{cash(value - benefit)}</span></div>
                  </div>
                  <p className="text-xs text-slate-500 my-3">Simulação visual. Não define o split real, não cria pagamento.</p>
                  <div className="grid grid-cols-2 gap-2">{methods.map(m => <button key={m} type="button"
                    aria-pressed={method === m} onClick={() => { setMethod(m); setWarning(""); }}
                    className={"rounded-xl border min-h-12 font-semibold " + (method === m ? "bg-blue-100 border-blue-600" : "bg-white")}>{m}</button>)}</div>
                </div>}<p className="text-xs text-slate-500 mt-5">Dados fictícios e eventos locais, apenas para testar a navegação do fluxo.</p></div>}
            {warning && <p role="alert" className="text-sm text-red-700 mt-4">{warning}</p>}
            <div className="flex gap-3 pt-4 border-t border-slate-100">
              <button type="button" onClick={advance} disabled={complete} className="flex-1 inline-flex justify-center items-center gap-2 rounded-xl bg-blue-700 text-white px-4 py-3 font-semibold disabled:opacity-40">Avançar teste <ArrowRight size={18}/></button>
              <button type="button" onClick={restart} aria-label="Reiniciar simulação" className="inline-flex items-center gap-2 rounded-xl border px-4 py-3"><RotateCcw size={17}/> Reiniciar</button>
            </div>
          </div>
          <div className="lg:col-span-2 rounded-2xl border bg-white p-5 md:p-6 shadow-sm">
            <h2 className="font-bold text-lg mb-4">Monitor de eventos</h2>
            {events.length === 0 ? <p className="text-slate-500 text-sm">Nenhum evento simulado. Avança no fluxo para acompanhar as etapas aqui.</p> :
              <ol className="space-y-4">{events.map((event, i) => <li key={i} className="flex gap-3 text-sm"><CheckCircle2 size={18} className="shrink-0 text-emerald-600 mt-1"/><div><div className="font-semibold">{event.title}</div><div className="text-slate-500">{event.role} · {event.stamp}</div><div className="text-slate-600 mt-1">{event.detail}</div></div></li>)}</ol>}
            {!complete && <div className="flex items-center gap-2 text-xs text-slate-500 mt-6"><Circle size={12}/> Aguardando próxima etapa</div>}
          </div>
        </div>
        <div className="mt-7"><h2 className="text-xl font-bold mb-3">Aceder aos módulos existentes</h2><div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">{destinations.map(item => <a key={item.path} href={item.path} className="block rounded-xl bg-white border border-slate-200 hover:border-blue-400 p-4"><div className="font-semibold">{item.title}</div><p className="text-sm text-slate-500 mt-1">{item.detail}</p><p className="text-xs text-blue-700 mt-3">{item.path}</p></a>)}</div></div>
      </section>
    </main>
  );
}
