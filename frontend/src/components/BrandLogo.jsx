/** RRClub — marca principal; R-Conekta identidade complementar. */
export const BrandMark = ({ className = "w-9 h-9", light = true }) => (
  <svg viewBox="0 0 88 88" className={className} data-testid="brand-mark" role="img" aria-label="Símbolo RRClub">
    <rect width="88" height="88" rx="22" fill={light ? "#203047" : "#F2F7FB"} />
    <path
      d="M67 17 C46 3 17 18 13 43 C7 69 29 80 48 78 C58 77 65 72 70 66"
      fill="none" stroke="#477FAE" strokeWidth="7.5" strokeLinecap="round"
    />
    <path
      d="M33 27 V61 M33 44 L54 26 M33 44 L54 62"
      fill="none" stroke="#8BC7E8" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round"
    />
    <circle cx="72" cy="13" r="4" fill="#477FAE" />
  </svg>
);

export const BrandLogo = ({ size = "md", dark = false, tagline = true, className = "" }) => {
  const s = size === "lg" ? { mark: "w-12 h-12", text: "text-2xl" } : size === "sm" ? { mark: "w-7 h-7", text: "text-sm" } : { mark: "w-9 h-9", text: "text-lg" };
  return (
    <div className={`flex items-center gap-2.5 ${className}`} data-testid="brand-logo">
      <BrandMark className={s.mark} />
      <div className="leading-tight min-w-0">
        <p className={`font-display font-extrabold tracking-tight whitespace-nowrap ${s.text} ${dark ? "text-[#0B1220]" : "text-white"}`} data-testid="brand-name">
          RR<span className={dark ? "text-[#7C3AED]" : "text-[#A78BFA]"}>Club</span>
        </p>
        {tagline && <p className={`text-[9px] uppercase tracking-[0.18em] font-semibold ${dark ? "text-[#54718B]" : "text-white/55"}`} data-testid="brand-tagline">by R-Conekta</p>}
      </div>
    </div>
  );
};
