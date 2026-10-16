import { useEffect, useState } from "react";
import { Globe2, MapPin, RefreshCw, ArrowUpRight } from "lucide-react";
import { api, dashboardMoney, num } from "../lib/api";

// Simplified geographic outlines, equirectangular projection. No customer geolocation.
const LAND = [
  [[-168,70],[-140,70],[-128,54],[-123,48],[-124,40],[-115,30],[-105,23],[-96,17],[-87,15],[-82,9],[-77,8],[-81,23],[-81,31],[-70,43],[-59,48],[-62,58],[-79,64],[-97,74],[-120,72],[-145,72]],
  [[-74,60],[-48,60],[-20,75],[-37,83],[-63,80]],
  [[-81,12],[-68,10],[-51,4],[-35,-6],[-39,-17],[-50,-27],[-58,-39],[-68,-55],[-74,-48],[-75,-30],[-81,-8]],
  [[-11,36],[-9,43],[-2,49],[9,55],[5,62],[21,71],[31,70],[42,60],[60,68],[100,76],[150,70],[179,65],[165,55],[145,50],[140,35],[122,25],[109,17],[106,7],[100,4],[94,17],[80,8],[70,25],[53,28],[43,12],[35,30],[26,40],[10,44],[4,36]],
  [[-17,32],[-5,36],[10,37],[25,32],[35,30],[43,12],[50,12],[40,-12],[32,-25],[19,-35],[12,-28],[8,-5],[-5,5],[-15,10]],
  [[113,-22],[122,-14],[137,-12],[145,-17],[153,-28],[147,-39],[132,-35],[115,-35]],
  [[47,-13],[50,-18],[47,-26],[44,-24]],
  [[166,-35],[178,-38],[173,-45],[166,-47]],
];
const project = ([lon, lat]) => [((lon + 180) / 360) * 800, ((83 - lat) / 145) * 330];
const path = (coords) => coords.map((p, i) => `${i ? "L" : "M"}${project(p).join(",")}`).join(" ") + "Z";

export function NetworkMap({ refreshKey, connected }) {
  const [state, setState] = useState(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api.get("/dashboard/admin/geography", { signal: controller.signal })
        .then(({ data }) => { setState(data); setError(false); })
        .catch((e) => { if (!controller.signal.aborted) setError(true); });
    }, 150);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [refreshKey, version]);
  const cities = state?.cities || [];
  const mapped = cities.filter(c => Number.isFinite(c.lat) && Number.isFinite(c.lon));
  const focus = cities.find(c => c.name === selected) || cities[0];
  return <section className="rr-network" data-testid="network-map">
    <div className="rr-network-heading">
      <div><span className="rr-eyebrow">A SUA REDE, SEM FRONTEIRAS</span><h2>Onde a influência acontece<span>.</span></h2></div>
      <span className={`rr-live-pill ${connected ? "is-live" : ""}`}><i />{connected ? "Ligado ao vivo" : "Sem ligação ao vivo"}</span>
    </div>
    <div className="rr-network-body">
      <div className="rr-world">
        <svg viewBox="0 0 800 355" role="img" aria-label="Mapa de atividade agregada por cidade dos parceiros">
          <defs><pattern id="rr-map-dots" width="8" height="8" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#698dce" opacity=".55" /></pattern><radialGradient id="rr-ocean"><stop stopColor="#174a95" stopOpacity=".5"/><stop offset="1" stopColor="#081a3a" stopOpacity="0"/></radialGradient></defs>
          <ellipse cx="420" cy="160" rx="350" ry="165" fill="url(#rr-ocean)" />
          {[70,140,210,280].map(y => <path key={y} d={`M20 ${y} H780`} stroke="#426ba9" strokeWidth=".5" opacity=".15"/>)}
          {LAND.map((land,i) => <path key={i} d={path(land)} fill="url(#rr-map-dots)" stroke="#527cae" strokeWidth=".65" strokeOpacity=".4" />)}
          {mapped.map(c => {
            const [x,y] = project([c.lon,c.lat]);
            const active = c.name === focus?.name;
            return <g key={c.name} className={`rr-map-pin ${active ? "selected" : ""}`} onClick={() => setSelected(c.name)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(c.name); } }} tabIndex="0" role="button" aria-label={`${c.name}, ${c.sales} vendas, ${c.clicks} cliques`}>
              <circle cx={x} cy={y} r={active ? 19 : 10} fill="#4c9cff" opacity=".14" />
              <circle cx={x} cy={y} r={active ? 10 : 5} fill="none" stroke="#6caeff" opacity=".45" className={active ? "rr-map-pulse" : ""}/>
              <circle cx={x} cy={y} r={active ? 4 : 3} fill={active ? "#fff" : "#70b9ff"}/>
              <title>{c.name} · {c.partners} parceiros · {c.clicks} cliques</title>
            </g>;
          })}
        </svg>
        <div className="rr-map-legend"><span><i />Rede de parceiros</span><span>Localização agregada por cidade</span></div>
        {error && <p className="rr-map-state">Não foi possível atualizar o mapa. <button onClick={() => setVersion(v => v + 1)}>Tentar novamente</button></p>}
        {!state && !error && <p className="rr-map-state">A carregar a rede…</p>}
        {state && !cities.length && <p className="rr-map-state">Ainda não há parceiros nesta moeda.</p>}
      </div>
      <div className="rr-map-details">
        <div className="rr-network-counter"><span><Globe2 size={15} />Presença da rede</span><strong>{num(cities.length)}<small>cidades</small></strong></div>
        <div className="rr-city-list" aria-label="Cidades da rede">{cities.slice(0, 5).map(c => <button key={c.name} onClick={() => setSelected(c.name)} className={c.name === focus?.name ? "selected" : ""}><span><i />{c.name}</span><b>{num(c.clicks)}<small>cliques</small></b></button>)}</div>
        {focus && <div className="rr-city-focus"><span><MapPin size={13}/>{focus.name}</span><strong>{dashboardMoney(focus.revenue)}</strong><small>{num(focus.sales)} vendas · {num(focus.partners)} parceiros</small></div>}
        <button className="rr-map-refresh" onClick={() => setVersion(v => v + 1)}><RefreshCw size={12}/>Atualizar mapa<ArrowUpRight size={13}/></button>
      </div>
    </div>
    <div className="rr-network-footer"><span>Dados da plataforma · {state?.currency?.toUpperCase() || "—"}</span><span>{state?.updated_at ? `Atualizado às ${new Date(state.updated_at).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}` : "A aguardar dados"}</span></div>
  </section>;
}
