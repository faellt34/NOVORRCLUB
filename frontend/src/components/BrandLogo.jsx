export const BrandMark = ({ className = "w-9 h-9", light = true }) => (
  <svg viewBox="0 0 80 80" className={className} role="img" aria-label="CONEKTA" data-testid="brand-mark">
    <rect width="80" height="80" rx="23" fill={light ? "#7137D7" : "#F0E8FF"} />
    <g fill="none" stroke={light ? "white" : "#7137D7"} strokeWidth="3.8">
      <circle cx="31" cy="40" r="20" /><circle cx="49" cy="40" r="20" />
    </g>
    <circle cx="40" cy="40" r="3.5" fill={light ? "white" : "#7137D7"} />
  </svg>
);

export const BrandLogo = ({ size = "md", dark = false, tagline = false, className = "" }) => {
  const width = size === "lg" ? 170 : size === "sm" ? 122 : 145;
  return (
    <div className={`flex items-center gap-3 ${className}`} data-testid="brand-logo">
      <BrandMark className={size === "lg" ? "w-11 h-11 shrink-0" : "w-9 h-9 shrink-0"} />
      <div className={dark ? "text-[#19132E]" : "text-white"}>
        <svg viewBox="0 0 218 34" width={width} role="img" aria-label="CONEKTA" className="max-w-full">
          <g fill="none" stroke="currentColor" strokeWidth="2.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M25 7C8-7 0 10 4 23C8 34 20 33 25 27M45 2C28 2 28 31 45 31C62 31 62 2 45 2ZM68 31V3L88 31V3M120 3H100V31H120M100 17H117M151 3V31M151 17L132 3M151 17L132 31M160 3H184M172 3V31M190 31L202 3L215 31M194 22H211" />
          </g>
        </svg>
        {tagline && <p className="text-[9px] uppercase tracking-[.22em] mt-1 opacity-60">Influência que conecta</p>}
      </div>
    </div>
  );
};
