const NODES = [[50, 8], [86, 30], [86, 70], [50, 92], [14, 70], [14, 30], [50, 50], [68, 42], [36, 60]];
const LINKS = [[0, 6], [1, 6], [2, 6], [3, 6], [4, 6], [5, 6], [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [7, 1], [7, 2], [8, 4], [8, 3], [7, 8]];

export const BrandMark = ({ className = "w-9 h-9", light = true }) => (
  <svg viewBox="0 0 100 100" className={className} data-testid="brand-mark" aria-label="RRclub">
    <defs>
      <linearGradient id="rr-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#A855F7" /><stop offset="1" stopColor="#5B21B6" /></linearGradient>
    </defs>
    <circle cx="50" cy="50" r="48" fill={light ? "url(#rr-g)" : "#fff"} />
    <circle cx="50" cy="50" r="42" fill="none" stroke={light ? "rgba(255,255,255,.35)" : "#7C3AED"} strokeWidth="1.5" strokeDasharray="3 4" />
    <g stroke={light ? "rgba(255,255,255,.75)" : "#7C3AED"} strokeWidth="1.6">
      {LINKS.map(([a, b]) => <line key={`${a}-${b}`} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} />)}
    </g>
    <g fill={light ? "#fff" : "#5B21B6"}>
      {NODES.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i === 6 ? 7 : i > 6 ? 3.5 : 5} />)}
      <circle cx="50" cy="50" r="3.2" fill={light ? "#5B21B6" : "#fff"} />
    </g>
  </svg>
);

export const BrandLogo = ({ size = "md", dark = false, tagline = false, className = "" }) => {
  const s = size === "lg" ? { mark: "w-11 h-11", text: "text-xl" } : size === "sm" ? { mark: "w-7 h-7", text: "text-sm" } : { mark: "w-9 h-9", text: "text-lg" };
  return (
    <div className={`flex items-center gap-2.5 ${className}`} data-testid="brand-logo">
      <BrandMark className={s.mark} />
      <div className="leading-tight">
        <p className={`font-display font-extrabold tracking-tight ${s.text} ${dark ? "text-slate-900" : "text-white"}`}><span className="text-purple-400">RR</span>club</p>
        {tagline && <p className={`text-[10px] uppercase tracking-widest ${dark ? "text-slate-400" : "text-purple-200/80"}`}>Luxury Experiences</p>}
      </div>
    </div>
  );
};
