export const BrandMark = ({ className = "w-9 h-9", light = true }) => (
  <svg viewBox="0 0 200 200" className={className} data-testid="brand-mark" aria-label="RRclub">
    <defs>
      <linearGradient id="rr-s2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#B47BFF" /><stop offset="100%" stopColor="#6E2BFF" /></linearGradient>
      <linearGradient id="rr-bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#08040E" /><stop offset="100%" stopColor="#1A0F2E" /></linearGradient>
    </defs>
    <circle cx="100" cy="100" r="98" fill={light ? "url(#rr-bg)" : "#fff"} stroke={light ? "rgba(110,43,255,.35)" : "#E9D5FF"} strokeWidth="2" />
    <g fill="none" stroke="url(#rr-s2)" strokeWidth="10">
      <circle cx="75" cy="100" r="50" />
      <circle cx="125" cy="100" r="50" />
    </g>
    <circle cx="100" cy="100" r="8" fill="#B47BFF" />
    <circle cx="100" cy="57" r="4" fill="#B47BFF" />
    <circle cx="100" cy="143" r="4" fill="#B47BFF" />
  </svg>
);

export const BrandLogo = ({ size = "md", dark = false, tagline = false, className = "" }) => {
  const s = size === "lg" ? { mark: "w-11 h-11", text: "text-xl" } : size === "sm" ? { mark: "w-7 h-7", text: "text-sm" } : { mark: "w-9 h-9", text: "text-lg" };
  return (
    <div className={`flex items-center gap-2.5 ${className}`} data-testid="brand-logo">
      <BrandMark className={s.mark} />
      <div className="leading-tight">
        <p className={`font-display font-extrabold tracking-tight ${s.text} ${dark ? "text-slate-900" : "text-white"}`}><span className="text-[#B47BFF]">RR</span>club</p>
        {tagline && <p className={`text-[10px] uppercase tracking-widest ${dark ? "text-slate-400" : "text-purple-200/80"}`}>Luxury Experiences</p>}
      </div>
    </div>
  );
};
