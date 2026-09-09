import { useEffect, useState } from "react";
import { Download, Smartphone } from "lucide-react";
import { toast } from "sonner";
import { useT } from "../context/I18nContext";

export const InstallAppButton = () => {
  const { t } = useT();
  const [prompt, setPrompt] = useState(null);
  const [installed, setInstalled] = useState(window.matchMedia?.("(display-mode: standalone)").matches);

  useEffect(() => {
    const onPrompt = (e) => { e.preventDefault(); setPrompt(e); };
    const onInstalled = () => { setInstalled(true); setPrompt(null); toast.success("ןןClub instalada no seu dispositivo"); };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => { window.removeEventListener("beforeinstallprompt", onPrompt); window.removeEventListener("appinstalled", onInstalled); };
  }, []);

  if (installed) return null;

  const install = async () => {
    if (prompt) { prompt.prompt(); await prompt.userChoice; setPrompt(null); return; }
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    toast.info(ios ? "No Safari: toque em Partilhar → 'Adicionar ao ecrã principal'." : "No menu do navegador escolha 'Instalar aplicação' / 'Adicionar ao ecrã inicial'.", { duration: 6000 });
  };

  return (
    <button data-testid="install-app-button" onClick={install} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm hover:bg-white/5 hover:text-white transition-colors text-left">
      {prompt ? <Download className="w-[18px] h-[18px] text-emerald-400" /> : <Smartphone className="w-[18px] h-[18px] text-purple-300" />}
      <span className="flex-1">{t("installApp")}</span>
    </button>
  );
};
