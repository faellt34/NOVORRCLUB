import React, { useMemo, useState } from "react";
import { BrandLogo } from "../components/BrandLogo";
import PreviewInsights from "../components/PreviewInsights";
import PreviewReports from "../components/PreviewReports";
import PreviewQrCard from "../components/PreviewQrCard";
import { DEMO_SOURCE, DEMO_STATUSES, deriveDemoMetrics, getPendingDemoOperation, initialDemoEvents, makeDemoEvent, toMinorUnits } from "../lib/previewData";
import { ArrowLeft, BadgeCheck, BarChart3, Building2, CheckCircle2, ClipboardList, CreditCard, LogOut, QrCode, ShieldCheck, Smartphone, Users } from "lucide-react";

const ROLES = [
  { id:"admin", name:"Administrador", alias:"Admin de teste", description:"Campanhas, indicadores, acompanhamento e auditoria" },
  { id:"influencer", name:"Influenciador", alias:"Influenciador de teste", description:"Campanhas, cliques, QR e benefícios demonstrativos" },
  { id:"partner", name:"Parceiro", alias:"Parceiro de teste", description:"Leitura QR, validação, vendas e histórico" },
  { id:"follower", name:"Seguidor", alias:"Seguidor de teste", description:"Cupom, desconto ilustrativo e meios de pagamento" },
];
const seed = initialDemoEvents();

export default function PreviewAccounts() {
  const [role,setRole] = useState(null);
  const [tab,setTab] = useState("overview");
  const [country,setCountry] = useState("PT");
  const [events,setEvents] = useState(initialDemoEvents);
  const [amount,setAmount] = useState("100");
  const [coupon,setCoupon] = useState("DEMO-INVERNO");
  const [pay,setPay] = useState("");
  const [message,setMessage] = useState("");
  const currency = country === "BR" ? "BRL" : "EUR";
  const fmt = n => new Intl.NumberFormat(country === "BR" ? "pt-BR" : "pt-PT",{style:"currency",currency}).format(Number(n)||0);
  const amountMinor = toMinorUnits(amount);
  const valid = amountMinor !== null;
  const val = valid ? amountMinor / 100 : 0;
  const discountMinor = valid ? Math.round(amountMinor * 0.05) : 0;
  const discount = discountMinor / 100;
  const counts = useMemo(() => deriveDemoMetrics(events,country),[events,country]);
  const pendingOperation = getPendingDemoOperation(events,country);
  const hasValidatedScan = Boolean(pendingOperation);
  const add = ({eventType,by,status,label,operationId,amountMinor:minor=null,discountMinor:disc=null}) => {
    const id = "demo-" + (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));
    const event = makeDemoEvent({id,operationId,eventType,role:by,label,status,country,amountMinor:minor,discountMinor:disc,currency});
    setEvents(old=>[...old,event]);
  };
  const enter = r => {setRole(r);setTab("overview");setMessage("");};
  const validate = () => {
    if (!valid || coupon.trim().toUpperCase()!=="DEMO-INVERNO") {
      setMessage("Usa o cupom DEMO-INVERNO e um valor válido maior que zero.");
      return;
    }
    add({eventType:DEMO_STATUSES.scan,by:"partner",status:"Validado",
      label:"QR DEMO-INVERNO validado: "+fmt(val)+"; desconto ilustrativo de "+fmt(discount),
      operationId:"sale-"+(crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)),amountMinor,discountMinor});
    setPay("");
    setMessage("Validação fictícia registada no monitor. Nenhuma API foi chamada.");
  };
  const checkout = () => {
    if (!hasValidatedScan) {setMessage("Primeiro valida o QR DEMO-INVERNO no painel do parceiro.");return;}
    if (!pay) {setMessage("Seleciona uma opção de pagamento fictícia.");return;}
    add({eventType:DEMO_STATUSES.checkout,by:"follower",status:"Checkout simulado",
      label:"Escolha fictícia: "+pay+"; sem transação real",operationId:pendingOperation.operationId,
      amountMinor:pendingOperation.amountMinor,discountMinor:pendingOperation.discountMinor});
    setMessage("Checkout simulado sem cobrar, guardar cartão ou contactar Stripe.");
  };
  const card = "rounded-2xl border border-[#DCE6EE] bg-white p-5 shadow-sm";
  return <main className="min-h-screen bg-[#F4F7FB] text-[#203047]" data-testid="rrclub-demo-accounts">
    <header className="bg-[#203047] text-white">
      <div className="max-w-6xl mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-3">
        <BrandLogo tagline size="sm"/>
        <span className="text-xs font-bold bg-white/10 rounded-full px-3 py-2 flex items-center gap-2"><ShieldCheck size={15}/> AMBIENTE DEMO · SEM DADOS REAIS</span>
      </div>
    </header>
    <div className="max-w-6xl mx-auto px-4 py-7">
      <a href="#/preview-v1" className="inline-flex items-center gap-2 text-sm text-[#477FAE] font-semibold mb-5"><ArrowLeft size={17}/> Centro de operações</a>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div><p className="text-xs font-bold uppercase tracking-widest text-[#477FAE]">Acessos de demonstração</p><h1 className="text-3xl font-extrabold mt-1">Painéis RRClub V1</h1>
        <p className="text-slate-600 text-sm mt-2 max-w-2xl">Escolhe um perfil de teste para explorar fluxos com dados fictícios. Estes acessos NÃO são contas de autenticação nem os dashboards operacionais oficiais.</p></div>
        <div className="flex gap-2">
          {["PT","BR"].map(x=><button type="button" key={x} aria-pressed={country===x} onClick={()=>{setCountry(x);setMessage("");}} className={"px-4 py-2 rounded-xl border text-sm font-semibold "+(country===x?"bg-[#203047] text-white":"bg-white")}>{x==="PT"?"Portugal":"Brasil"}</button>)}
        </div>
      </div>
      <div className="flex overflow-x-auto gap-2 mb-4 pb-1" role="tablist" aria-label="Áreas de gestão">
        {[["overview","Visão geral"],["qr","QR & campanhas"],["payments","Pagamentos"],["reports","Relatórios"]].map(([id,label])=><button type="button" key={id}
          role="tab" aria-selected={tab===id} onClick={()=>setTab(id)} className={"whitespace-nowrap rounded-xl border px-4 py-3 text-sm font-bold min-h-12 "+(tab===id?"bg-[#203047] text-white border-[#203047]":"bg-white text-[#203047] border-[#DCE6EE]")}>{label}</button>)}
      </div>
      {tab==="overview"&&<div className="mb-5"><PreviewInsights events={events} country={country} metrics={counts}/></div>}
      {tab==="qr"&&<div className="mb-5"><PreviewQrCard country={country}/></div>}
      {tab==="payments"&&<div className="mb-5 rounded-2xl border border-[#DCE6EE] bg-white p-5 sm:p-6 shadow-sm">
        <p className="text-[11px] uppercase tracking-widest font-bold text-[#477FAE]">Estados de pagamento · demonstração</p>
        <h2 className="text-xl font-extrabold mt-1">Acompanhamento financeiro</h2>
        <p className="text-sm text-slate-600 mt-2">O fluxo atual é visual e nunca cria cobranças. Não há montantes liquidados nem repasses reais nesta prévia.</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
          {[[ "QR validados",counts.scans ],["Aguardam checkout",Math.max(0,counts.pending)],["Checkouts simulados",counts.checkouts],["Pagamentos confirmados","Não verificado"]].map(([label,n])=>
            <div key={label} className="rounded-xl bg-[#F4F7FB] p-4 min-h-[104px]"><div className="text-xs text-slate-600">{label}</div><div className="text-2xl font-extrabold mt-3">{n}</div></div>)}
        </div>
        <div className="rounded-xl bg-amber-50 border border-amber-100 text-amber-900 text-xs p-4 mt-5">Os estados “Checkout simulado” e “QR validado” não significam pagamento recebido. Para validação P5 real será necessário um backend de homologação com Stripe Test Mode.</div>
      </div>}
      {tab==="reports"&&<div className="mb-5"><PreviewReports events={events} country={country}/></div>}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 mb-6">{ROLES.map(r=><button key={r.id} type="button" aria-pressed={role===r.id} onClick={()=>enter(r.id)}
        className={"text-left rounded-2xl border p-3 sm:p-4 min-h-[132px] transition-colors "+(role===r.id?"bg-[#203047] text-white border-[#203047]":"bg-white text-[#203047] border-[#DCE6EE] hover:border-[#477FAE]")}>
        <div className="font-bold text-lg">{r.name}</div><div className={"text-xs mt-1 "+(role===r.id?"text-blue-100":"text-slate-500")}>{r.alias}</div>
        <div className={"text-xs sm:text-sm mt-3 "+(role===r.id?"text-blue-100":"text-slate-600")}>{r.description}</div>
      </button>)}</div>
      {role===null?<div className={card}><h2 className="font-bold">Escolhe o teu perfil</h2><p className="text-sm text-slate-600 mt-2">A demonstração abre imediatamente, sem senha, e nunca utiliza contas verdadeiras. Para criar contas autenticadas será necessário um backend de homologação independente.</p></div>:
      <div className="grid lg:grid-cols-[minmax(0,1.5fr)_minmax(270px,1fr)] gap-5">
        <section className={card}>
          <div className="flex justify-between items-center gap-2 mb-5"><div><p className="text-xs text-slate-500">Área selecionada</p><h2 className="text-xl font-extrabold">{ROLES.find(r=>r.id===role).name} · Demo</h2></div><button type="button" onClick={()=>enter(null)} className="inline-flex gap-1 items-center text-sm border rounded-xl px-3 py-2"><LogOut size={16}/> Sair</button></div>
          {role==="admin"&&<div>
            <div className="grid grid-cols-2 gap-3 mb-5">
              {[["Campanhas",counts.campaignCount],["Divulgações",counts.shares],["QR validados",counts.scans],["Checkouts fictícios",counts.checkouts]].map(([k,n])=><div key={k} className="rounded-xl bg-[#F4F7FB] p-4"><p className="text-xs text-slate-500">{k}</p><p className="text-2xl font-bold mt-1">{n}</p></div>)}
            </div>
            <p className="text-sm text-slate-600 mb-4">Indicadores calculados exclusivamente a partir dos eventos desta demonstração. Receita e comissões reais não estão disponíveis.</p>
            <h3 className="font-bold">Funções existentes no dashboard oficial</h3>
            <div className="text-sm text-slate-600 mt-2 space-y-2"><p>Gestão de campanhas e parceiros · acompanhamento de cliques e origem · relatórios · auditoria · pagamentos.</p></div>
          </div>}
          {role==="influencer"&&<div>
            <div className="rounded-xl bg-[#F4F7FB] p-4 mb-4"><p className="text-xs text-slate-500">Campanha fictícia</p><h3 className="font-bold text-xl mt-1">DEMO-INVERNO</h3><p className="text-sm text-slate-600 mt-2">Exemplo de divulgação para uma campanha. Nenhum cupom real foi criado.</p></div>
            <div className="grid grid-cols-2 gap-3 mb-4"><div className="bg-white border rounded-xl p-4"><p className="text-xs text-slate-500">Cliques</p><strong>0</strong></div><div className="bg-white border rounded-xl p-4"><p className="text-xs text-slate-500">Comissões reais</p><strong>—</strong></div></div>
            <button onClick={()=>{add({eventType:DEMO_STATUSES.share,by:"influencer",status:"Demonstração",
    label:"Campanha fictícia divulgada",operationId:"share-"+(crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2))});setMessage("Partilha registada apenas no navegador.");}} className="rounded-xl bg-[#203047] text-white py-3 px-5 font-semibold">Simular divulgação do QR</button>
          </div>}
          {role==="partner"&&<div className="space-y-4">
            <div className="bg-[#F4F7FB] rounded-xl px-4 py-3 flex items-center justify-between gap-2">
              <div><p className="text-xs text-slate-500">Turno demonstrativo</p><p className="font-extrabold text-emerald-700">Pronto para validar</p></div>
              <div className="text-right"><p className="text-xs text-slate-500">QR válidos nesta sessão</p><p className="text-lg font-extrabold">{counts.scans}</p></div>
            </div>
            <p className="text-sm text-slate-600">Validação simulada do QR e do montante introduzido pelo estabelecimento. Não ativa câmara, Stripe ou API.</p>
            <label className="block text-sm font-semibold">Código QR fictício<input value={coupon} onChange={e=>setCoupon(e.target.value)} placeholder="DEMO-INVERNO" className="block w-full border rounded-xl p-3 mt-2"/></label>
            <label className="block text-sm font-semibold">Valor da venda ({currency})<input value={amount} inputMode="decimal" onChange={e=>setAmount(e.target.value)} className="block w-full border rounded-xl p-3 mt-2"/></label>
            <div className="flex flex-wrap gap-2"><button onClick={validate} className="rounded-xl bg-[#203047] text-white min-h-12 py-3 px-5 font-semibold inline-flex items-center gap-2"><QrCode size={18}/> Validar QR de demonstração</button>
              <button type="button" onClick={()=>{setCoupon("DEMO-INVERNO");setMessage("QR fictício carregado. Introduz o valor e valida.");}} className="rounded-xl border border-slate-200 min-h-12 px-4 text-sm font-bold">Carregar QR demo</button></div>
              <div className="bg-[#F4F7FB] rounded-xl p-4 text-sm"><p className="font-semibold mb-2">Resumo demonstrativo</p><div className="flex justify-between"><span>Valor</span><strong>{fmt(valid?val:0)}</strong></div><div className="flex justify-between mt-1"><span>Benefício ilustrativo</span><span>{fmt(discount)}</span></div><div className="border-t mt-2 pt-2 flex justify-between font-extrabold"><span>Total ilustrativo</span><span>{fmt(valid?val-discount:0)}</span></div><p className="text-xs text-slate-500 mt-2">Não representa os repasses financeiros reais.</p></div>
          </div>}
          {role==="follower"&&<div className="space-y-4">
            <p className="text-sm text-slate-600">Cupom fictício <strong>DEMO-INVERNO</strong>. Valores apenas ilustrativos; regras de distribuição não validadas.</p>
            <div className="bg-[#F4F7FB] rounded-xl p-4 text-sm"><div className="flex justify-between"><span>Valor</span><strong>{fmt(valid?val:0)}</strong></div><div className="flex justify-between mt-2"><span>Benefício ilustrativo (5%)</span><span>− {fmt(discount)}</span></div><div className="flex justify-between border-t mt-2 pt-2 text-lg font-bold"><span>Total demonstrativo</span><span>{fmt(valid?val-discount:0)}</span></div></div>
            <p className="text-sm font-semibold">Pagamento fictício</p><div className="grid grid-cols-2 gap-2">{(country==="BR"?["Pix","Cartão"]:["MB WAY","Cartão","Apple Pay"]).map(x=><button key={x} aria-pressed={pay===x} onClick={()=>setPay(x)} className={"border rounded-xl p-3 text-sm font-semibold "+(pay===x?"bg-blue-100 border-blue-600":"bg-white")}>{x}</button>)}</div>
            <p className="text-xs text-slate-500">{hasValidatedScan?"QR fictício validado pelo parceiro: podes simular o checkout.":"Para continuar, muda para Parceiro e valida o QR DEMO-INVERNO."}</p>
            <button type="button" onClick={checkout} className="rounded-xl bg-[#203047] text-white py-3 px-5 font-semibold">Simular checkout</button>
          </div>}
          {message&&<p role="status" className="bg-blue-50 text-[#203047] p-3 rounded-xl text-sm mt-4">{message}</p>}
        </section>
        <aside className={card}>
          <div className="flex items-center gap-2 mb-4"><ClipboardList size={19} className="text-[#477FAE]"/><h2 className="font-extrabold">Monitor de testes</h2></div>
          <p className="text-xs text-slate-500 mb-4">Os eventos são partilhados entre os quatro perfis nesta sessão, mas não saem deste navegador.</p>
          <button type="button" className="text-xs font-semibold text-[#477FAE] underline mb-4" onClick={()=>{setEvents(initialDemoEvents());setPay("");setCoupon("DEMO-INVERNO");setAmount("100");setMessage("Simulação reiniciada sem afetar nenhum utilizador.");}}>Reiniciar dados de demonstração</button>
          <ol className="space-y-4">{events.slice().reverse().map(e=><li key={e.id} className="flex items-start gap-3 text-sm"><CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-1"/><div><strong>{e.label}</strong><p className="text-xs text-slate-500 mt-1">{e.role} · {e.status}</p></div></li>)}</ol>
        </aside>
      </div>}
      <p className="mt-7 text-xs text-slate-500">Protótipo de interface e fluxo com dados simulados. Não é autenticação de produção, nem demonstra o estado real dos pagamentos.</p>
    </div>
  </main>;
}
