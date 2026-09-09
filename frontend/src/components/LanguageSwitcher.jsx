import { Globe } from "lucide-react";
import { useT, LANGS } from "../context/I18nContext";

export const LanguageSwitcher = ({ dark = false }) => {
  const { lang, setLang } = useT();
  return (
    <div data-testid="language-switcher" className={`inline-flex items-center gap-1 rounded-xl p-1 ${dark ? "bg-white/5 border border-white/10" : "bg-white border border-slate-200"}`}>
      <Globe className={`w-3.5 h-3.5 ml-1.5 ${dark ? "text-slate-400" : "text-slate-400"}`} />
      {Object.keys(LANGS).map((l) => (
        <button key={l} data-testid={`lang-${l}`} onClick={() => setLang(l)} title={LANGS[l]}
          className={`px-2 py-1 rounded-lg text-[11px] font-bold uppercase btn-press ${lang === l ? "bg-purple-600 text-white" : dark ? "text-slate-400 hover:text-white" : "text-slate-500 hover:bg-purple-50"}`}>
          {l}
        </button>
      ))}
    </div>
  );
};
