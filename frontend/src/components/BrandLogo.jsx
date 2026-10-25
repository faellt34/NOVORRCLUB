/** R-Conekta: K em órbita; identidade visual da plataforma RRClub. */
export const BrandMark = ({ className = "w-9 h-9", light = true }) => (
  <svg viewBox="0 0 88 88" className={className} data-testid="brand-mark" role="img" aria-label="Símbolo R-Conekta">
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

export const BrandLogo = ({ size = "md", dark = false, tagline = false, className = "" }) => {
  const s = size === "lg" ? { mark: "w-11 h-11", text: "text-xl" } : size === "sm" ? { mark: "w-7 h-7", text: "text-sm" } : { mark: "w-9 h-9", text: "text-lg" };
  return (
    <div className={`flex items-center gap-2.5 ${className}`} data-testid="brand-logo">
      <BrandMark className={s.mark} />
      <div className="leading-tight min-w-0">
        <p
          className={`font-extrabold tracking-tight whitespace-nowrap ${s.text} ${dark ? "text-[#203047]" : "text-white"}`}
          style={{ fontFamily: 'Manrope, Inter, system-ui, sans-serif' }}
        >
          R-<span className={dark ? "text-[#477FAE]" : "text-[#A8D9F0]"}>Conekta</span>
        </p>
        {tagline && <p className={`text-[9px] uppercase tracking-[0.18em] font-semibold ${dark ? "text-[#54718B]" : "text-[#B6CBE0]"}`}>by RRClub</p>}
      </div>
    </div>
  );
};
