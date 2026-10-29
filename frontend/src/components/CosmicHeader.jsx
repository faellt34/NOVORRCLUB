/** Cabeçalho "universo" premium: gradiente azul-profundo, brilho roxo, grão de estrelas. */
export const CosmicHeader = ({ children, className = "", testId = "cosmic-header" }) => (
  <header data-testid={testId} className={`cosmic-header relative overflow-hidden text-white rounded-b-[32px] lg:rounded-3xl -mx-4 sm:-mx-6 lg:mx-0 -mt-6 lg:mt-0 px-5 sm:px-7 pt-6 pb-7 lg:py-7 fade-up ${className}`}>
    <div className="relative z-10">{children}</div>
  </header>
);

export const HeaderStat = ({ label, value, sub, accent, testId }) => (
  <div data-testid={testId} className="min-w-0">
    <p className="text-[10px] uppercase tracking-[0.14em] text-white/50 font-semibold">{label}</p>
    <p className={`font-display text-2xl font-extrabold tabular-nums leading-tight truncate ${accent ? "text-violet-300" : ""}`}>{value}</p>
    {sub && <p className="text-[11px] text-white/60 truncate">{sub}</p>}
  </div>
);
