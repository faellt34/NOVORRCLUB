import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, ArrowUpRight, BadgePercent, CheckCircle2, ChevronDown,
  CreditCard, Menu, Pause, Play, QrCode, RotateCcw, ScanLine,
  ShieldCheck, Sparkles, Store, TrendingUp, Users, X
} from "lucide-react";
import "../home.css";

const stages = [
  { eyebrow: "01 / DESCOBERTA", title: "Uma oferta chama a atenção.", description: "O criador divulga uma experiência. O cliente encontra a oferta e decide visitar o parceiro.", status: "Oferta encontrada" },
  { eyebrow: "02 / IDENTIFICAÇÃO", title: "O cliente apresenta o seu QR.", description: "No estabelecimento, o seguidor apresenta o QR Code RRClub ao parceiro para identificar a campanha.", status: "QR apresentado" },
  { eyebrow: "03 / VALIDAÇÃO", title: "O parceiro confirma a compra.", description: "O parceiro lê o código, indica o valor e confirma a oferta antes de iniciar o pagamento.", status: "Oferta validada" },
  { eyebrow: "04 / PAGAMENTO", title: "O cliente paga e aproveita.", description: "O cliente confirma o pagamento no seu telemóvel. Após a confirmação real do sistema, a venda pode ser registada.", status: "Pagamento demonstrativo" }
];

const qrCells = Array.from({ length: 121 }, (_, i) => {
  const x = i % 11, y = Math.floor(i / 11);
  const finder = (a, b) => x >= a && x < a + 3 && y >= b && y < b + 3;
  return finder(0, 0) || finder(8, 0) || finder(0, 8) || ((x * 13 + y * 7 + x * y * 3) % 9 < 4);
});

const benefits = [
  { icon: Store, label: "Para negócios", title: "Mais visitas, vendas mensuráveis.", text: "Campanhas locais, ofertas com QR e um painel para acompanhar a utilização." },
  { icon: Users, label: "Para criadores", title: "A influência tem resultado.", text: "Partilha experiências, recomenda parceiros e acompanha o impacto das campanhas." },
  { icon: BadgePercent, label: "Para clientes", title: "Descobertas com benefícios.", text: "Encontra propostas de negócios locais e usa os teus benefícios com simplicidade." }
];

function RRLogo({ small = false }) {
  return <span className={"v2-wordmark" + (small ? " v2-wordmark-small" : "")} aria-label="RR Club">
    <span>RR</span><i aria-hidden="true"></i><span>Club</span>
  </span>;
}

function QrArt() {
  return <div className="v2-qr" aria-label="Código QR ilustrativo, não utilizável">
    {qrCells.map((active, i) => <span key={i} className={active ? "on" : ""} />)}
  </div>;
}

function DemoPhone({ stage }) {
  return <div className="v2-phone" aria-label="Demonstração fictícia da experiência no telemóvel">
    <div className="v2-phone-camera"></div>
    <div className="v2-phone-content">
      <div className="v2-phone-top"><RRLogo small /><span>DEMO</span></div>
      {stage === 0 && <div className="v2-phone-panel">
        <div className="v2-photo"><span className="v2-photo-icon">✦</span><span>EXPERIÊNCIAS LOCAIS</span></div>
        <small>OFERTA DE EXEMPLO</small>
        <strong>O teu próximo favorito<br />está perto de ti.</strong>
        <p>Restaurante parceiro · Almada</p>
        <div className="v2-pill"><BadgePercent size={15}/> 5% de benefício ilustrativo</div>
        <div className="v2-phone-cta">Ver oferta <ArrowRight size={14}/></div>
      </div>}
      {stage === 1 && <div className="v2-phone-panel v2-qr-scene">
        <small>O TEU PASSE RRCLUB</small>
        <strong>Mostra ao parceiro.</strong>
        <p>Este código identifica a oferta.</p>
        <QrArt/>
        <span className="v2-qr-caption">QR ILUSTRATIVO — SEM VALIDADE</span>
      </div>}
      {stage === 2 && <div className="v2-phone-panel">
        <div className="v2-check-icon"><ScanLine size={25}/></div>
        <small>VALIDAÇÃO NO PARCEIRO</small>
        <strong>Oferta identificada.</strong>
        <p>O parceiro confirma o valor antes de pagar.</p>
        <div className="v2-receipt"><span>Valor de exemplo</span><b>20,00 €</b><span>Benefício 5%</span><b>−1,00 €</b><hr/><strong>Total ilustrativo</strong><strong>19,00 €</strong></div>
      </div>}
      {stage === 3 && <div className="v2-phone-panel v2-confirm-scene">
        <div className="v2-check-icon v2-success"><CheckCircle2 size={38}/></div>
        <small>DEMONSTRAÇÃO / SEM COBRANÇA</small>
        <strong>Pagamento concluído</strong>
        <p>Exemplo do ecrã após confirmação do pagamento.</p>
        <div className="v2-paid">19,00 € <span>SIMULADO</span></div>
        <div className="v2-phone-cta">Ver comprovativo <ArrowRight size={14}/></div>
      </div>}
    </div>
  </div>;
}

function ProcessDemo() {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);
  useEffect(() => {
    if (!playing) return undefined;
    const timer = window.setInterval(() => setStep(s => (s + 1) % stages.length), 3800);
    return () => window.clearInterval(timer);
  }, [playing]);
  const select = (n) => { setStep(n); setPlaying(false); };
  return <section className="v2-demo-section" id="demonstracao">
    <div className="v2-section-header">
      <div><span className="v2-eyebrow v2-eyebrow-dark"><span className="v2-pulse"/> DEMONSTRAÇÃO INTERATIVA</span>
      <h2>Vê a RRClub<br/><em>em movimento.</em></h2>
      <p>Quatro momentos, uma experiência clara. Carrega numa etapa para explorar.</p></div>
      <span className="v2-demo-label"><Play size={13}/> SIMULAÇÃO • NÃO PROCESSA PAGAMENTOS</span>
    </div>
    <div className="v2-demo-shell">
      <div className="v2-demo-visual"><div className="v2-demo-halo"/><div className="v2-orbit v2-orbit-a"/><div className="v2-orbit v2-orbit-b"/><DemoPhone stage={step}/><div className="v2-float-notice"><span><CheckCircle2 size={17}/></span>{stages[step].status}</div></div>
      <div className="v2-demo-info">
        <span className="v2-demo-overline">O PERCURSO RRCLUB</span>
        <span className="v2-demo-counter">0{step+1} <span>/ 04</span></span>
        <div className="v2-demo-title-wrap" key={step}><span>{stages[step].eyebrow}</span><h3>{stages[step].title}</h3><p>{stages[step].description}</p></div>
        <div className="v2-demo-progress">{stages.map((s,i)=><button type="button" key={s.eyebrow} onClick={()=>select(i)} aria-label={"Mostrar etapa "+(i+1)} aria-current={i===step?"step":undefined} className={i===step?"active":i<step?"done":""}><span>{i<step?"✓":"0"+(i+1)}</span><i/></button>)}</div>
        <div className="v2-demo-controls"><button type="button" onClick={()=>setPlaying(p=>!p)}>{playing?<Pause size={16}/>:<Play size={16}/>} {playing?"Pausar vídeo":"Reproduzir vídeo"}</button><button type="button" onClick={()=>{setStep(0);setPlaying(true)}}><RotateCcw size={16}/> Recomeçar</button></div>
        <p className="v2-demo-footnote">Animação explicativa do fluxo P5. Não é uma operação financeira real nem apresenta resultados de produção.</p>
      </div>
    </div>
  </section>;
}

function Home() {
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { document.title = "RRClub 2.0 | Conecta negócios reais"; }, []);
  return <div className="rr-v2">
    <div className="v2-notice"><span className="v2-notice-dot"/> RRCLUB 2.0 <span className="v2-notice-text">— Ambiente de apresentação. Sem alterações no site oficial.</span></div>
    <header className="v2-nav">
      <div className="v2-nav-inner"><a href="#inicio" aria-label="RRClub, início" className="v2-logo-link"><RRLogo/><span className="v2-logo-caption">CONECTA<br/>NEGÓCIOS REAIS</span></a>
      <nav className={menuOpen?"v2-links open":"v2-links"} aria-label="Navegação principal">
        <a href="#como-funciona" onClick={()=>setMenuOpen(false)}>Como funciona</a><a href="#demonstracao" onClick={()=>setMenuOpen(false)}>Ver demonstração</a><a href="#para-quem" onClick={()=>setMenuOpen(false)}>Para quem</a>
      </nav><div className="v2-header-actions"><Link to="/login" className="v2-signin">Entrar</Link><Link to="/registar" className="v2-btn v2-btn-sm">Criar conta <ArrowUpRight size={16}/></Link></div>
      <button type="button" className="v2-menu" onClick={()=>setMenuOpen(p=>!p)} aria-expanded={menuOpen} aria-label="Abrir navegação">{menuOpen?<X/>:<Menu/>}</button></div>
    </header>
    <main id="inicio">
      <section className="v2-hero">
        <div className="v2-gridback"/><div className="v2-nebula v2-nebula-1"/><div className="v2-nebula v2-nebula-2"/>
        <div className="v2-hero-main">
          <div className="v2-hero-copy"><div className="v2-hero-badge"><Sparkles size={15}/> EXPERIÊNCIAS LOCAIS, LIGAÇÕES REAIS <span>2.0</span></div>
            <h1>O próximo cliente<br/>pode estar a <em>um<br/>QR de distância.</em></h1>
            <p>Negócios, criadores e clientes no mesmo ecossistema. Uma experiência simples, do interesse à compra.</p>
            <div className="v2-hero-actions"><a href="#demonstracao" className="v2-btn v2-btn-primary"><Play size={18} fill="currentColor"/> Ver como funciona <ArrowRight size={19}/></a><a href="#para-quem" className="v2-btn v2-btn-outline">Descobrir vantagens <ArrowUpRight size={17}/></a></div>
            <div className="v2-trust"><span><ShieldCheck size={17}/> Sem instalar aplicações</span><span><QrCode size={17}/> QR no estabelecimento</span><span><CreditCard size={17}/> Pagamento após validação</span></div>
          </div>
          <div className="v2-hero-showcase" aria-label="Prévia visual ilustrativa RRClub">
            <div className="v2-hero-ring v2-hero-ring-a"/><div className="v2-hero-ring v2-hero-ring-b"/>
            <div className="v2-hero-dashboard"><div className="v2-window-head"><span/><span/><span/><b>RRCLUB / EXPERIÊNCIA</b></div><div className="v2-hero-dashboard-inner">
              <div className="v2-hero-scan"><ScanLine size={32}/></div><small>UMA LIGAÇÃO. UM BENEFÍCIO.</small><strong>Da descoberta<br/>à experiência.</strong>
              <div className="v2-mini-flow"><span>Oferta</span><ArrowRight size={14}/><span>QR</span><ArrowRight size={14}/><span>Pagamento</span></div>
            </div></div>
            <div className="v2-hero-smallcard"><span><TrendingUp size={16}/></span><div><b>Resultados que contam.</b><small>Acompanha as tuas campanhas.</small></div></div>
            <div className="v2-hero-tag">RR—CLUB / DIGITAL EXPERIENCE</div>
          </div>
        </div>
        <a href="#como-funciona" className="v2-scroll-down">EXPLORA A EXPERIÊNCIA <ChevronDown size={16}/></a>
      </section>
      <section id="como-funciona" className="v2-steps-section">
        <div className="v2-topline"><span className="v2-eyebrow v2-eyebrow-dark">COMO FUNCIONA</span><span>01 — 04 / PERCURSO SIMPLES</span></div>
        <h2>Simples para quem usa.<br/><em>Inteligente para quem cresce.</em></h2>
        <div className="v2-steps-grid">
          {[["01","Descobre","O cliente conhece uma oferta divulgada por um criador.","search"],["02","Apresenta","Mostra o seu QR Code no estabelecimento.","qr"],["03","Valida","O parceiro lê o código e confirma o valor da compra.","scan"],["04","Paga","O cliente conclui o pagamento no seu telemóvel.","pay"]].map(([n,t,d,ic])=><div className="v2-step-card" key={n}><span className="v2-step-no">{n}</span><div className="v2-step-icon">{ic==="search"?<Sparkles/>:ic==="qr"?<QrCode/>:ic==="scan"?<ScanLine/>:<CreditCard/>}</div><h3>{t}</h3><p>{d}</p></div>)}
        </div>
      </section>
      <ProcessDemo/>
      <section className="v2-audiences" id="para-quem"><div className="v2-topline"><span className="v2-eyebrow v2-eyebrow-dark">UM ECOSSISTEMA, TRÊS EXPERIÊNCIAS</span><span>CONEXÕES COM PROPÓSITO</span></div><h2>Para quem faz<br/><em>as coisas acontecerem.</em></h2><div className="v2-benefits">
      {benefits.map(({icon:Icon,label,title,text})=><article key={label}><div className="v2-benefit-icon"><Icon size={25}/></div><span>{label}</span><h3>{title}</h3><p>{text}</p><a href="#demonstracao">Conhecer o percurso <ArrowUpRight size={17}/></a></article>)}</div>
      </section>
      <section className="v2-end-cta"><div className="v2-end-glow"/><span>O FUTURO DAS EXPERIÊNCIAS LOCAIS</span><h2>As melhores conexões<br/><em>começam aqui.</em></h2><p>A RRClub aproxima quem cria, quem vende e quem descobre.</p><div><Link to="/registar?perfil=partner" className="v2-btn v2-btn-primary">Sou parceiro <ArrowRight size={17}/></Link><Link to="/registar?perfil=influencer" className="v2-btn v2-btn-outline">Sou criador <ArrowUpRight size={16}/></Link></div></section>
    </main>
    <footer className="v2-footer"><RRLogo small/><span>Apresentação RRClub 2.0 — conteúdo demonstrativo, sem transações reais.</span><Link to="/privacidade">Privacidade</Link></footer>
  </div>;
}
export default Home;
